"""Single source of truth for every PMHM Parquet table.

Each column records: Arrow type, nullability, unit, origin and description.
``origin`` is one of
  - ``source:<column>``   verbatim value of column <column> in the raw file (unchanged numerically)
  - ``source_path``       parsed from the raw file/folder name
  - ``cube_meta:<key>``   per-frame metadata stored inside the raw .b2nd cube
  - ``derived``           computed by PMHM from other columns (formula in description)
  - ``joined``            looked up from another raw source (join key in description)
  - ``provenance``        bookkeeping that links a row back to its raw source
These descriptors are embedded in each Parquet file's field metadata, so the
files are self-describing, and are exported to docs/DATA_DICTIONARY.md.
"""
from __future__ import annotations

from dataclasses import dataclass

import pyarrow as pa


@dataclass(frozen=True)
class Col:
    name: str
    type: pa.DataType
    nullable: bool
    unit: str
    origin: str
    description: str


@dataclass(frozen=True)
class TableSpec:
    name: str
    grain: str
    description: str
    primary_key: tuple[str, ...]
    columns: tuple[Col, ...]

    def schema(self, extra_meta: dict[str, str] | None = None) -> pa.Schema:
        fields = [
            pa.field(c.name, c.type, nullable=c.nullable,
                     metadata={"unit": c.unit, "origin": c.origin, "description": c.description})
            for c in self.columns
        ]
        meta = {
            "pmhm.table": self.name,
            "pmhm.grain": self.grain,
            "pmhm.description": self.description,
            "pmhm.primary_key": ",".join(self.primary_key),
        }
        meta.update(extra_meta or {})
        return pa.schema(fields, metadata=meta)

    @property
    def names(self) -> list[str]:
        return [c.name for c in self.columns]


S, I8, I16, I32, I64 = pa.string(), pa.int8(), pa.int16(), pa.int32(), pa.int64()
F32, F64, B = pa.float32(), pa.float64(), pa.bool_()

# --- shared column definitions -------------------------------------------------
SUBJECT = Col("subject_id", S, False, "", "source_path",
              "Canonical subject identifier 'subject_NN' (matches cube file and ROI folder names).")
STAGE = Col("stage", S, False, "", "source:stage",
            "Experimental stage label as written in the raw data (before_clamping | during_clamping_<P>mmHg).")
PRESSURE = Col("pressure_mmhg", I16, False, "mmHg", "derived",
               "Upper-arm cuff pressure parsed from stage label; 0 for baseline and rest periods.")
PHASE = Col("phase", S, False, "", "derived",
            "baseline = before_clamping; clamping = cuff pressure > 0; rest = during_clamping_0mmHg "
            "(no-pressure recovery period recorded between clamping stages).")
BLOCK = Col("stage_block_index", I16, False, "", "derived",
            "0-based index of the contiguous stage segment in the session timeline (0 = baseline, "
            "1 = 20 mmHg, 2 = rest, 3 = 40 mmHg, ...). Distinguishes the eight separate rest periods.")
PREV_P = Col("preceding_pressure_mmhg", I16, True, "mmHg", "derived",
             "For rest blocks: pressure of the clamping block immediately before (reperfusion context). "
             "Null for baseline and clamping blocks.")
T_IN_BLOCK = Col("time_in_block_s", F64, False, "s", "derived",
                 "time_delta_s minus time_delta_s of the first row of the same stage block.")
IMAGE_FILE = Col("image_file", S, False, "", "provenance",
                 "Dataset-relative path of the hyperspectral cube (.b2nd) that holds the frame.")
SRC_FILE = Col("source_file", S, False, "", "provenance", "Dataset-relative path of the raw source file.")


def src_row(dtype=I32):
    return Col("source_row_index", dtype, False, "", "provenance",
               "0-based data-row position in the raw source file (header excluded).")


# --- tables ------------------------------------------------------------------
MASTER_ROIS = TableSpec(
    name="master_rois",
    grain="one row per (subject, ROI, tracked time point)",
    description="Tracked palm ROI bounding boxes for all subjects/ROIs available locally, linked to cube frames.",
    primary_key=("subject_id", "roi_id", "source_row_index"),
    columns=(
        SUBJECT,
        Col("roi_id", I8, False, "", "source_path", "ROI number N from file name roi_N.(csv|feather)."),
        src_row(),
        Col("frame_index", I32, True, "", "joined",
            "Index along axis 0 of the subject cube, matched exactly on (stage, time_delta). Null when the "
            "tracked time point has no cube frame (tracking continues ~20 s past the 1100 s cube end) or the "
            "cube is not available locally."),
        STAGE,
        Col("time_delta_s", F64, False, "s", "source:time_delta", "Time since start of recording."),
        Col("y1", I64, False, "px", "source:y1", "Top row of the ROI box (cube row coordinate)."),
        Col("x1", I64, False, "px", "source:x1", "Left column of the ROI box."),
        Col("y2", I64, False, "px", "source:y2", "Bottom row (exclusive slice end) of the ROI box."),
        Col("x2", I64, False, "px", "source:x2", "Right column (exclusive slice end) of the ROI box."),
        Col("bbox_width_px", I32, False, "px", "derived", "x2 - x1."),
        Col("bbox_height_px", I32, False, "px", "derived", "y2 - y1."),
        Col("center_x_px", F32, False, "px", "derived", "(x1 + x2) / 2."),
        Col("center_y_px", F32, False, "px", "derived", "(y1 + y2) / 2."),
        Col("displacement_px", F32, True, "px", "derived",
            "Euclidean displacement of the ROI centre from the previous row of the same ROI (motion / "
            "tracking-consistency indicator). Null for the first row."),
        Col("bbox_in_image_bounds", B, False, "", "derived",
            "True when 0 <= x1 < x2 <= image width and 0 <= y1 < y2 <= image height (272 x 512)."),
        PRESSURE, PHASE, BLOCK, PREV_P, T_IN_BLOCK,
        Col("exposure_ms", I16, True, "ms", "joined", "Camera exposure of the matched frame (cube metadata)."),
        Col("has_image_frame", B, False, "", "joined", "True when frame_index is not null."),
        IMAGE_FILE,
        Col("image_locally_available", B, False, "", "joined",
            "True when the complete cube file for this subject exists locally."),
        SRC_FILE,
        Col("source_format", S, False, "", "provenance",
            "csv or feather: which raw copy was read (CSV preferred; feather used when no CSV exists)."),
    ),
)

MASTER_FRAMES = TableSpec(
    name="master_frames",
    grain="one row per (subject, cube frame)",
    description="Frame index of each locally complete hyperspectral cube, from the per-frame metadata stored "
                "inside the .b2nd file. Backbone for synchronising images, ROIs and stages.",
    primary_key=("subject_id", "frame_index"),
    columns=(
        SUBJECT,
        Col("frame_index", I32, False, "", "provenance", "Index along axis 0 of the cube."),
        Col("stage", S, False, "", "cube_meta:stage", "Stage label stored per frame in the cube."),
        Col("time_delta_s", F64, False, "s", "cube_meta:time_delta", "Time since start of recording."),
        Col("exposure_ms", I16, False, "ms", "cube_meta:exposure", "Camera exposure time."),
        Col("frame_interval_s", F64, True, "s", "derived", "time_delta_s minus previous frame's time_delta_s."),
        PRESSURE, PHASE, BLOCK, PREV_P, T_IN_BLOCK,
        Col("n_rois_tracked", I8, False, "", "joined",
            "Number of locally available ROI tracks that have a row matched to this frame."),
        IMAGE_FILE,
    ),
)

MASTER_SPECTROMETER = TableSpec(
    name="master_spectrometer",
    grain="one row per (subject, stage, ROI, replicate spectrum, wavelength)",
    description="HR2000+ diffuse reflectance reference spectra (long format) for all 10 subjects, 4 ROIs, "
                "baseline and 160 mmHg. One Parquet row group per (subject, stage, ROI).",
    primary_key=("subject_id", "stage", "roi_id", "spectrum_index", "wavelength_index"),
    columns=(
        Col("subject_id", S, False, "", "derived", "'subject N' -> 'subject_NN' (zero-padded) to match cube names."),
        Col("subject_label_original", S, False, "", "source:subject", "Subject label exactly as in the raw file."),
        Col("stage_original", S, False, "", "source:stage", "Stage label exactly as in the raw file."),
        Col("stage", S, False, "", "derived",
            "Harmonised cube stage label: 'baseline (0 mmHg)' -> before_clamping, "
            "'160 mmHg' -> during_clamping_160mmHg (README mapping)."),
        PRESSURE, PHASE,
        Col("roi_id", I8, False, "", "source:ROI", "ROI number (1-4), same numbering as ROI track files."),
        Col("spectrum_index", I16, False, "", "derived",
            "0-based replicate spectrum number within (subject, stage, ROI): occurrence count of the "
            "wavelength within the group in file order. The file is wavelength-major; replicate order was "
            "verified (adjacent-wavelength correlation 0.996 aligned vs 0.14 shuffled)."),
        Col("wavelength_index", I16, False, "", "derived", "0-based index into the 550 sorted spectrometer wavelengths."),
        Col("wavelength_nm", F64, False, "nm", "source:wavelength [nm]", "Spectrometer wavelength."),
        Col("reflectance_au", F64, False, "a.u.", "source:reflectance [a.u.]",
            "Diffuse reflectance as provided (arbitrary units, unmodified)."),
        Col("flag_negative_reflectance", B, False, "", "derived", "reflectance_au < 0 (noise floor indicator)."),
        src_row(I64), SRC_FILE,
    ),
)

OPTICS_FILTERS = TableSpec(
    name="optics_ximea_filters",
    grain="one row per (filter, wavelength sample)",
    description="Spectral response of the 16 XIMEA mosaic filters (400-1000 nm, 1 nm).",
    primary_key=("filter_id", "wavelength_sample_index"),
    columns=(
        Col("wavelength_nm", I64, False, "nm", "source:Wavelength [nm]",
            "Wavelength as provided. NOTE: integer-rounded in the raw file — per filter 601 samples map to 581 "
            "unique integers (20 duplicated, 20 skipped), so (filter, wavelength) is not unique."),
        Col("filter_id", I64, False, "", "source:filter", "Filter number 1-16."),
        Col("wavelength_sample_index", I16, False, "", "derived",
            "0-based sample position within the filter's curve in file order (0-600); unique key with filter_id."),
        Col("filter_response_au", F64, False, "a.u.", "source:Filter response [a.u.]", "Filter response."),
        Col("channel_index", I8, False, "", "derived",
            "filter_id - 1 = position on the cube channel axis (verified: filter peaks match README channel "
            "wavelengths within 2 nm)."),
        Col("channel_nominal_wavelength_nm", I16, False, "nm", "derived", "README nominal wavelength of that channel."),
        src_row(), SRC_FILE,
    ),
)

OPTICS_XENON = TableSpec(
    name="optics_xenon_light_source",
    grain="one row per wavelength",
    description="Relative irradiance of the xenon light source used during acquisition.",
    primary_key=("source_row_index",),
    columns=(
        Col("wavelength_nm", F64, False, "nm", "source:wavelength [nm]", "Wavelength."),
        Col("relative_irradiance_au", F64, False, "a.u.", "source:relative_irradiance [a.u.]",
            "Relative irradiance as provided (negative values present in the raw file, kept unmodified)."),
        Col("flag_negative_irradiance", B, False, "", "derived", "relative_irradiance_au < 0."),
        src_row(), SRC_FILE,
    ),
)

COLOR_CHECKER_SPEC = TableSpec(
    name="color_checker_spectrometer_adapted",
    grain="one row per raw-file row (colour patch x camera band x replicate)",
    description="Colour-checker reference spectra adapted to the 16 camera bands (as provided).",
    primary_key=("source_row_index",),
    columns=(
        Col("reflectance", F64, False, "a.u.", "source:reflectance",
            "Band-adapted reflectance as provided (values sum to ~1 over 16 bands; not interpreted further)."),
        Col("wavelength_nm", I64, False, "nm", "source:wavelength", "Nominal camera band wavelength."),
        Col("color_name", S, False, "", "source:color_name", "Colour-checker patch name."),
        Col("color_hex", S, False, "", "source:color", "Display colour of the patch."),
        Col("band", I64, False, "", "source:band", "Camera band index (= cube channel index)."),
        Col("color_index", I64, False, "", "source:ind", "Colour-checker patch number."),
        src_row(), SRC_FILE,
    ),
)

COLOR_CHECKER_FRAMES = TableSpec(
    name="color_checker_frames",
    grain="one row per (colour-checker cube, frame)",
    description="Per-frame metadata of the colour-checker XIMEA cubes (raw and normalised).",
    primary_key=("cube", "frame_index"),
    columns=(
        Col("cube", S, False, "", "source_path", "ximea_raw or ximea_norm."),
        Col("frame_index", I32, False, "", "provenance", "Index along axis 0 of the cube."),
        Col("color_name", S, False, "", "cube_meta:color", "Patch imaged in the frame."),
        Col("time_delta_s", F64, False, "s", "cube_meta:time_delta", "Time since start of recording."),
        Col("exposure_ms", I16, False, "ms", "cube_meta:exposure", "Camera exposure time."),
        IMAGE_FILE,
    ),
)

REF_CHANNELS = TableSpec(
    name="ref_channels",
    grain="one row per camera channel",
    description="Camera channel parameters: nominal wavelength, measured filter characteristics, dark-reference statistics.",
    primary_key=("channel_index",),
    columns=(
        Col("channel_index", I8, False, "", "derived", "Position on the cube channel (last) axis."),
        Col("filter_id", I8, False, "", "derived", "channel_index + 1 (filter number in ximea_filters)."),
        Col("nominal_wavelength_nm", I16, False, "nm", "source:README.md", "Channel wavelength listed in the dataset README."),
        Col("peak_wavelength_nm", I16, False, "nm", "derived", "Argmax of the filter response curve."),
        Col("peak_response_au", F64, False, "a.u.", "derived", "Maximum filter response."),
        Col("centroid_wavelength_nm", F64, False, "nm", "derived", "Response-weighted mean wavelength over 400-1000 nm "
            "(includes NIR side lobes of the mosaic filters)."),
        Col("fwhm_nm", F64, False, "nm", "derived", "Width of the contiguous region around the peak above half maximum."),
        Col("secondary_peak_ratio", F64, False, "", "derived",
            "Highest response outside the main FWHM lobe (+/-10 nm) divided by the peak (spectral cross-talk indicator)."),
        Col("dark_mean", F64, False, "counts", "derived", "Mean of dark reference for this channel."),
        Col("dark_std", F64, False, "counts", "derived", "Std of dark reference for this channel."),
        Col("dark_min", F64, False, "counts", "derived", "Min of dark reference."),
        Col("dark_max", F64, False, "counts", "derived", "Max of dark reference."),
        Col("colorchecker_band_wavelength_nm", I16, True, "nm", "joined",
            "Wavelength assigned to this band in color_checker/spectrometer_adapted (consistency check)."),
    ),
)

REF_STAGES = TableSpec(
    name="ref_stages",
    grain="one row per stage label",
    description="Stage dictionary from data/metadata.json with pressure, phase and spectrometer label mapping.",
    primary_key=("stage",),
    columns=(
        Col("stage_order", I8, False, "", "source:metadata.json", "Order in metadata.json 'stages'."),
        STAGE, PRESSURE, PHASE,
        Col("spectrometer_stage_label", S, True, "", "derived", "Matching label in spectrometer.csv, if any."),
        Col("blocks_per_session", I8, True, "", "derived",
            "Number of contiguous blocks of this stage in a complete session (from local cubes; null if unseen)."),
    ),
)

REF_SUBJECTS = TableSpec(
    name="ref_subjects",
    grain="one row per subject",
    description="Subject coverage matrix: which modalities are available locally and their key acquisition parameters.",
    primary_key=("subject_id",),
    columns=(
        SUBJECT,
        Col("cube_status", S, False, "", "derived", "complete | partial_download | missing (local file system)."),
        Col("cube_file", S, True, "", "provenance", "Dataset-relative path of cube or partial-download stub."),
        Col("cube_bytes", I64, True, "bytes", "provenance", "Size on disk."),
        Col("n_frames", I32, True, "", "cube_meta", "Frames in the cube (complete cubes only)."),
        Col("exposure_ms", I16, True, "ms", "cube_meta", "Exposure (unique per subject)."),
        Col("frame_rate_hz", F64, True, "Hz", "derived", "1 / median frame interval."),
        Col("duration_s", F64, True, "s", "cube_meta", "Last frame time_delta."),
        Col("n_stage_blocks", I16, True, "", "derived", "Contiguous stage blocks in the cube timeline."),
        Col("roi_ids_available", S, False, "", "source_path", "Comma-separated ROI numbers with local track files."),
        Col("n_roi_rows", I32, False, "", "derived", "ROI rows in master_rois for the subject."),
        Col("n_spectra_baseline", I16, False, "", "derived", "Replicate spectra at baseline (all ROIs)."),
        Col("n_spectra_160mmHg", I16, False, "", "derived", "Replicate spectra at 160 mmHg (all ROIs)."),
        Col("usable_roi_image_analysis", B, False, "", "derived",
            "True when complete cube AND at least one ROI track exist (ROI-level spectral-temporal extraction possible)."),
    ),
)

ALL_TABLES: dict[str, TableSpec] = {t.name: t for t in (
    MASTER_ROIS, MASTER_FRAMES, MASTER_SPECTROMETER, OPTICS_FILTERS, OPTICS_XENON,
    COLOR_CHECKER_SPEC, COLOR_CHECKER_FRAMES, REF_CHANNELS, REF_STAGES, REF_SUBJECTS,
)}


# ----------------------------------------------------------------------------- standalone single-file dataset
RECORD_TYPES: dict[str, str] = {
    "roi_frame": "One tracked palm ROI in one video frame: ROI box + per-channel mean/std of the raw camera counts "
                 "inside the box (extracted from the hyperspectral cube). Rows tracked after the cube end have "
                 "null spectral values (has_image_frame = false).",
    "frame": "One video frame of a locally complete cube: stage, time, exposure (no pixel data).",
    "spectrometer": "One wavelength sample of one HR2000+ reference spectrum (value = diffuse reflectance, a.u.).",
    "camera_filter": "One wavelength sample of one camera filter response curve (value = response, a.u.).",
    "light_source": "One wavelength sample of the xenon light-source spectrum (value = relative irradiance, a.u.).",
    "color_checker": "One colour-checker patch reference value for one camera band (value = band-adapted reflectance).",
    "channel": "One camera channel: nominal/peak wavelength, FWHM, cross-talk, dark-reference statistics.",
    "stage": "One protocol stage: cuff pressure, phase, spectrometer label, blocks per session.",
    "subject": "One participant: data availability and acquisition parameters.",
}


def _rt(*types: str) -> str:
    return "[" + ",".join(types) + "] "


def standalone_spec(channel_wavelengths: list[int]) -> TableSpec:
    """Union schema of the single-file dataset. Column descriptions start with the record types they apply to."""
    ALL = tuple(RECORD_TYPES)
    cols = [
        Col("record_type", S, False, "", "derived", _rt(*ALL) + "Row kind; filter on it first. "
            "Values: " + ", ".join(RECORD_TYPES)),
        Col("subject_id", S, True, "", "source_path", _rt("roi_frame", "frame", "spectrometer", "subject") +
            "Participant 'subject_NN'."),
        Col("roi_id", I8, True, "", "source_path", _rt("roi_frame", "spectrometer") + "Palm ROI number 1-4."),
        Col("frame_index", I32, True, "", "provenance", _rt("roi_frame", "frame") +
            "Frame number in the original cube (axis 0). Null for ROI rows tracked after the cube end."),
        Col("time_delta_s", F64, True, "s", "cube_meta:time_delta", _rt("roi_frame", "frame") +
            "Time since start of recording."),
        Col("stage", S, True, "", "source:stage", _rt("roi_frame", "frame", "spectrometer", "stage") +
            "Protocol stage label (before_clamping | during_clamping_<P>mmHg)."),
        Col("pressure_mmhg", I16, True, "mmHg", "derived", _rt("roi_frame", "frame", "spectrometer", "stage") +
            "Upper-arm cuff pressure; 0 at baseline and rest."),
        Col("phase", S, True, "", "derived", _rt("roi_frame", "frame", "spectrometer", "stage") +
            "baseline | clamping | rest (no-pressure recovery between clamping stages)."),
        Col("stage_block_index", I16, True, "", "derived", _rt("roi_frame", "frame") +
            "Contiguous stage segment 0-16 in the session timeline (distinguishes the 8 rest periods)."),
        Col("preceding_pressure_mmhg", I16, True, "mmHg", "derived", _rt("roi_frame", "frame") +
            "For rest rows: pressure of the clamping block just before (reperfusion context)."),
        Col("time_in_block_s", F64, True, "s", "derived", _rt("roi_frame", "frame") + "Time since block start."),
        Col("exposure_ms", I16, True, "ms", "cube_meta:exposure", _rt("roi_frame", "frame", "subject") +
            "Camera exposure time."),
        Col("has_image_frame", B, True, "", "joined", _rt("roi_frame") +
            "True when spectral values were extracted (a cube frame exists for this time point)."),
        Col("y1", I16, True, "px", "source:y1", _rt("roi_frame") + "ROI box top row."),
        Col("x1", I16, True, "px", "source:x1", _rt("roi_frame") + "ROI box left column."),
        Col("y2", I16, True, "px", "source:y2", _rt("roi_frame") + "ROI box bottom row (exclusive)."),
        Col("x2", I16, True, "px", "source:x2", _rt("roi_frame") + "ROI box right column (exclusive)."),
        Col("displacement_px", F32, True, "px", "derived", _rt("roi_frame") +
            "ROI centre motion since the previous frame (tracking/motion indicator)."),
    ]
    for ch, wl in enumerate(channel_wavelengths):
        cols.append(Col(f"ch{ch:02d}_{wl}nm_mean", F32, True, "counts", "derived", _rt("roi_frame") +
                        f"Mean raw camera value of channel {ch} ({wl} nm nominal) over the ROI pixels "
                        "(no dark/white correction)."))
    for ch, wl in enumerate(channel_wavelengths):
        cols.append(Col(f"ch{ch:02d}_{wl}nm_std", F32, True, "counts", "derived", _rt("roi_frame") +
                        f"Standard deviation over the ROI pixels of channel {ch} ({wl} nm)."))
    cols += [
        Col("roi_patch_min", F32, True, "counts", "derived", _rt("roi_frame") + "Minimum value in the ROI patch (all channels)."),
        Col("roi_patch_max", F32, True, "counts", "derived", _rt("roi_frame") + "Maximum value in the ROI patch (all channels)."),
        Col("frame_interval_s", F64, True, "s", "derived", _rt("frame") + "Time since previous frame."),
        Col("n_rois_tracked", I8, True, "", "joined", _rt("frame") + "ROI tracks available for this frame."),
        Col("wavelength_nm", F64, True, "nm", "source", _rt("spectrometer", "camera_filter", "light_source",
            "color_checker", "channel") + "Wavelength of the sample (channel rows: nominal wavelength)."),
        Col("wavelength_index", I16, True, "", "derived", _rt("spectrometer", "camera_filter") +
            "Sample position on the instrument's wavelength grid."),
        Col("value", F64, True, "a.u.", "source", _rt("spectrometer", "camera_filter", "light_source", "color_checker") +
            "Measured value, unmodified; meaning given by value_quantity."),
        Col("value_quantity", S, True, "", "derived", _rt("spectrometer", "camera_filter", "light_source", "color_checker") +
            "diffuse_reflectance | filter_response | relative_irradiance | band_adapted_reflectance."),
        Col("flag_negative_value", B, True, "", "derived", _rt("spectrometer", "light_source") + "value < 0 (noise floor)."),
        Col("spectrum_index", I16, True, "", "derived", _rt("spectrometer") +
            "Replicate spectrum number within (subject, stage, ROI)."),
        Col("channel_index", I8, True, "", "derived", _rt("camera_filter", "color_checker", "channel") +
            "Camera channel = position in the cube's channel axis (ch00..ch15 columns)."),
        Col("color_name", S, True, "", "source:color_name", _rt("color_checker") + "Colour-checker patch name."),
        Col("color_index", I16, True, "", "source:ind", _rt("color_checker") + "Colour-checker patch number."),
        Col("color_hex", S, True, "", "source:color", _rt("color_checker") + "Display colour of the patch."),
        Col("peak_wavelength_nm", I16, True, "nm", "derived", _rt("channel") + "Filter response peak."),
        Col("fwhm_nm", F64, True, "nm", "derived", _rt("channel") + "Filter full width at half maximum."),
        Col("secondary_peak_ratio", F64, True, "", "derived", _rt("channel") + "Out-of-band lobe / peak (cross-talk)."),
        Col("dark_mean", F64, True, "counts", "derived", _rt("channel") + "Dark-reference mean for the channel."),
        Col("dark_std", F64, True, "counts", "derived", _rt("channel") + "Dark-reference standard deviation."),
        Col("stage_order", I8, True, "", "source:metadata.json", _rt("stage") + "Order of the stage in the protocol list."),
        Col("spectrometer_stage_label", S, True, "", "derived", _rt("stage") + "Label used in the spectrometer file."),
        Col("blocks_per_session", I8, True, "", "derived", _rt("stage") + "Times the stage occurs per session."),
        Col("cube_status", S, True, "", "derived", _rt("subject") + "complete | partial_download | missing in the source download."),
        Col("n_frames", I32, True, "", "cube_meta", _rt("subject") + "Video frames recorded."),
        Col("frame_rate_hz", F64, True, "Hz", "derived", _rt("subject") + "Video frame rate."),
        Col("duration_s", F64, True, "s", "cube_meta", _rt("subject") + "Recording duration."),
        Col("roi_ids_available", S, True, "", "source_path", _rt("subject") + "ROIs with tracking data."),
        Col("n_spectra_baseline", I16, True, "", "derived", _rt("subject") + "Spectrometer spectra at baseline."),
        Col("n_spectra_160mmHg", I16, True, "", "derived", _rt("subject") + "Spectrometer spectra at 160 mmHg."),
        Col("source_file", S, True, "", "provenance", _rt(*ALL) + "Raw file of the original download the row came from."),
        Col("source_row_index", I64, True, "", "provenance", _rt("roi_frame", "spectrometer", "camera_filter",
            "light_source", "color_checker") + "Row position in that raw file."),
    ]
    return TableSpec(
        name="spectralpaca_pmhm_dataset",
        grain="one row per record; kind given by record_type (see pmhm.record_types)",
        description="Standalone single-file SPECTRALPACA dataset for PMHM: ROI spectral time series extracted from "
                    "the hyperspectral video, plus spectrometer references, optics/calibration, protocol and "
                    "participant tables. Usable without the original download.",
        primary_key=("record_type", "subject_id", "roi_id", "frame_index", "stage", "spectrum_index",
                     "channel_index", "color_index", "source_row_index"),
        columns=tuple(cols),
    )
