# PMHM Data Dictionary

_Generated from the field metadata embedded in each Parquet file (`data/processed/parquet`). Regenerate with `scripts/pmhm_build_dataset.py card`._

**Origin codes** — `source:<col>` verbatim raw value · `source_path` parsed from raw file/folder name · `cube_meta:<key>` per-frame metadata inside the .b2nd cube · `derived` computed by PMHM (formula given) · `joined` looked up from another raw source · `provenance` link back to the raw row/file.

## `master_rois`

Tracked palm ROI bounding boxes for all subjects/ROIs available locally, linked to cube frames.

- **Grain:** one row per (subject, ROI, tracked time point)
- **Primary key:** `subject_id, roi_id, source_row_index`
- **Rows:** 125,323 · **Row groups:** 1 · **Size:** 1.48 MB
- **Raw sources:** `intermediates/rois/subject_01/roi_1.csv`, `intermediates/rois/subject_01/roi_2.feather`, `intermediates/rois/subject_01/roi_3.csv`, `intermediates/rois/subject_01/roi_4.feather`, `intermediates/rois/subject_02/roi_1.csv`, `intermediates/rois/subject_02/roi_2.csv`, `intermediates/rois/subject_02/roi_3.csv`, `intermediates/rois/subject_01/roi_3.feather`, `intermediates/rois/subject_02/roi_1.feather`, `intermediates/rois/subject_02/roi_2.feather`, `intermediates/rois/subject_02/roi_3.feather`

| column | type | nullable | unit | origin | description |
|---|---|---|---|---|---|
| subject_id | string | False |  | source_path | Canonical subject identifier 'subject_NN' (matches cube file and ROI folder names). |
| roi_id | int8 | False |  | source_path | ROI number N from file name roi_N.(csv|feather). |
| source_row_index | int32 | False |  | provenance | 0-based data-row position in the raw source file (header excluded). |
| frame_index | int32 | True |  | joined | Index along axis 0 of the subject cube, matched exactly on (stage, time_delta). Null when the tracked time point has no cube frame (tracking continues ~20 s past the 1100 s cube end) or the cube is not available locally. |
| stage | string | False |  | source:stage | Experimental stage label as written in the raw data (before_clamping | during_clamping_<P>mmHg). |
| time_delta_s | double | False | s | source:time_delta | Time since start of recording. |
| y1 | int64 | False | px | source:y1 | Top row of the ROI box (cube row coordinate). |
| x1 | int64 | False | px | source:x1 | Left column of the ROI box. |
| y2 | int64 | False | px | source:y2 | Bottom row (exclusive slice end) of the ROI box. |
| x2 | int64 | False | px | source:x2 | Right column (exclusive slice end) of the ROI box. |
| bbox_width_px | int32 | False | px | derived | x2 - x1. |
| bbox_height_px | int32 | False | px | derived | y2 - y1. |
| center_x_px | float | False | px | derived | (x1 + x2) / 2. |
| center_y_px | float | False | px | derived | (y1 + y2) / 2. |
| displacement_px | float | True | px | derived | Euclidean displacement of the ROI centre from the previous row of the same ROI (motion / tracking-consistency indicator). Null for the first row. |
| bbox_in_image_bounds | bool | False |  | derived | True when 0 <= x1 < x2 <= image width and 0 <= y1 < y2 <= image height (272 x 512). |
| pressure_mmhg | int16 | False | mmHg | derived | Upper-arm cuff pressure parsed from stage label; 0 for baseline and rest periods. |
| phase | string | False |  | derived | baseline = before_clamping; clamping = cuff pressure > 0; rest = during_clamping_0mmHg (no-pressure recovery period recorded between clamping stages). |
| stage_block_index | int16 | False |  | derived | 0-based index of the contiguous stage segment in the session timeline (0 = baseline, 1 = 20 mmHg, 2 = rest, 3 = 40 mmHg, ...). Distinguishes the eight separate rest periods. |
| preceding_pressure_mmhg | int16 | True | mmHg | derived | For rest blocks: pressure of the clamping block immediately before (reperfusion context). Null for baseline and clamping blocks. |
| time_in_block_s | double | False | s | derived | time_delta_s minus time_delta_s of the first row of the same stage block. |
| exposure_ms | int16 | True | ms | joined | Camera exposure of the matched frame (cube metadata). |
| has_image_frame | bool | False |  | joined | True when frame_index is not null. |
| image_file | string | False |  | provenance | Dataset-relative path of the hyperspectral cube (.b2nd) that holds the frame. |
| image_locally_available | bool | False |  | joined | True when the complete cube file for this subject exists locally. |
| source_file | string | False |  | provenance | Dataset-relative path of the raw source file. |
| source_format | string | False |  | provenance | csv or feather: which raw copy was read (CSV preferred; feather used when no CSV exists). |

## `master_frames`

Frame index of each locally complete hyperspectral cube, from the per-frame metadata stored inside the .b2nd file. Backbone for synchronising images, ROIs and stages.

- **Grain:** one row per (subject, cube frame)
- **Primary key:** `subject_id, frame_index`
- **Rows:** 48,157 · **Row groups:** 3 · **Size:** 0.95 MB
- **Raw sources:** cube metadata / derived

| column | type | nullable | unit | origin | description |
|---|---|---|---|---|---|
| subject_id | string | False |  | source_path | Canonical subject identifier 'subject_NN' (matches cube file and ROI folder names). |
| frame_index | int32 | False |  | provenance | Index along axis 0 of the cube. |
| stage | string | False |  | cube_meta:stage | Stage label stored per frame in the cube. |
| time_delta_s | double | False | s | cube_meta:time_delta | Time since start of recording. |
| exposure_ms | int16 | False | ms | cube_meta:exposure | Camera exposure time. |
| frame_interval_s | double | True | s | derived | time_delta_s minus previous frame's time_delta_s. |
| pressure_mmhg | int16 | False | mmHg | derived | Upper-arm cuff pressure parsed from stage label; 0 for baseline and rest periods. |
| phase | string | False |  | derived | baseline = before_clamping; clamping = cuff pressure > 0; rest = during_clamping_0mmHg (no-pressure recovery period recorded between clamping stages). |
| stage_block_index | int16 | False |  | derived | 0-based index of the contiguous stage segment in the session timeline (0 = baseline, 1 = 20 mmHg, 2 = rest, 3 = 40 mmHg, ...). Distinguishes the eight separate rest periods. |
| preceding_pressure_mmhg | int16 | True | mmHg | derived | For rest blocks: pressure of the clamping block immediately before (reperfusion context). Null for baseline and clamping blocks. |
| time_in_block_s | double | False | s | derived | time_delta_s minus time_delta_s of the first row of the same stage block. |
| n_rois_tracked | int8 | False |  | joined | Number of locally available ROI tracks that have a row matched to this frame. |
| image_file | string | False |  | provenance | Dataset-relative path of the hyperspectral cube (.b2nd) that holds the frame. |

## `master_spectrometer`

HR2000+ diffuse reflectance reference spectra (long format) for all 10 subjects, 4 ROIs, baseline and 160 mmHg. One Parquet row group per (subject, stage, ROI).

- **Grain:** one row per (subject, stage, ROI, replicate spectrum, wavelength)
- **Primary key:** `subject_id, stage, roi_id, spectrum_index, wavelength_index`
- **Rows:** 4,397,250 · **Row groups:** 80 · **Size:** 35.56 MB
- **Raw sources:** `data/spectrometer/spectrometer.csv`

| column | type | nullable | unit | origin | description |
|---|---|---|---|---|---|
| subject_id | string | False |  | derived | 'subject N' -> 'subject_NN' (zero-padded) to match cube names. |
| subject_label_original | string | False |  | source:subject | Subject label exactly as in the raw file. |
| stage_original | string | False |  | source:stage | Stage label exactly as in the raw file. |
| stage | string | False |  | derived | Harmonised cube stage label: 'baseline (0 mmHg)' -> before_clamping, '160 mmHg' -> during_clamping_160mmHg (README mapping). |
| pressure_mmhg | int16 | False | mmHg | derived | Upper-arm cuff pressure parsed from stage label; 0 for baseline and rest periods. |
| phase | string | False |  | derived | baseline = before_clamping; clamping = cuff pressure > 0; rest = during_clamping_0mmHg (no-pressure recovery period recorded between clamping stages). |
| roi_id | int8 | False |  | source:ROI | ROI number (1-4), same numbering as ROI track files. |
| spectrum_index | int16 | False |  | derived | 0-based replicate spectrum number within (subject, stage, ROI): occurrence count of the wavelength within the group in file order. The file is wavelength-major; replicate order was verified (adjacent-wavelength correlation 0.996 aligned vs 0.14 shuffled). |
| wavelength_index | int16 | False |  | derived | 0-based index into the 550 sorted spectrometer wavelengths. |
| wavelength_nm | double | False | nm | source:wavelength [nm] | Spectrometer wavelength. |
| reflectance_au | double | False | a.u. | source:reflectance [a.u.] | Diffuse reflectance as provided (arbitrary units, unmodified). |
| flag_negative_reflectance | bool | False |  | derived | reflectance_au < 0 (noise floor indicator). |
| source_row_index | int64 | False |  | provenance | 0-based data-row position in the raw source file (header excluded). |
| source_file | string | False |  | provenance | Dataset-relative path of the raw source file. |

## `optics_ximea_filters`

Spectral response of the 16 XIMEA mosaic filters (400-1000 nm, 1 nm).

- **Grain:** one row per (filter, wavelength sample)
- **Primary key:** `filter_id, wavelength_sample_index`
- **Rows:** 9,616 · **Row groups:** 1 · **Size:** 0.12 MB
- **Raw sources:** `intermediates/optics/ximea_filters.csv`

| column | type | nullable | unit | origin | description |
|---|---|---|---|---|---|
| wavelength_nm | int64 | False | nm | source:Wavelength [nm] | Wavelength as provided. NOTE: integer-rounded in the raw file — per filter 601 samples map to 581 unique integers (20 duplicated, 20 skipped), so (filter, wavelength) is not unique. |
| filter_id | int64 | False |  | source:filter | Filter number 1-16. |
| wavelength_sample_index | int16 | False |  | derived | 0-based sample position within the filter's curve in file order (0-600); unique key with filter_id. |
| filter_response_au | double | False | a.u. | source:Filter response [a.u.] | Filter response. |
| channel_index | int8 | False |  | derived | filter_id - 1 = position on the cube channel axis (verified: filter peaks match README channel wavelengths within 2 nm). |
| channel_nominal_wavelength_nm | int16 | False | nm | derived | README nominal wavelength of that channel. |
| source_row_index | int32 | False |  | provenance | 0-based data-row position in the raw source file (header excluded). |
| source_file | string | False |  | provenance | Dataset-relative path of the raw source file. |

## `optics_xenon_light_source`

Relative irradiance of the xenon light source used during acquisition.

- **Grain:** one row per wavelength
- **Primary key:** `source_row_index`
- **Rows:** 2,033 · **Row groups:** 1 · **Size:** 0.04 MB
- **Raw sources:** `intermediates/optics/xenon_light_source.csv`

| column | type | nullable | unit | origin | description |
|---|---|---|---|---|---|
| wavelength_nm | double | False | nm | source:wavelength [nm] | Wavelength. |
| relative_irradiance_au | double | False | a.u. | source:relative_irradiance [a.u.] | Relative irradiance as provided (negative values present in the raw file, kept unmodified). |
| flag_negative_irradiance | bool | False |  | derived | relative_irradiance_au < 0. |
| source_row_index | int32 | False |  | provenance | 0-based data-row position in the raw source file (header excluded). |
| source_file | string | False |  | provenance | Dataset-relative path of the raw source file. |

## `color_checker_spectrometer_adapted`

Colour-checker reference spectra adapted to the 16 camera bands (as provided).

- **Grain:** one row per raw-file row (colour patch x camera band x replicate)
- **Primary key:** `source_row_index`
- **Rows:** 3,840 · **Row groups:** 1 · **Size:** 0.07 MB
- **Raw sources:** `intermediates/color_checker/spectrometer_adapted.csv`

| column | type | nullable | unit | origin | description |
|---|---|---|---|---|---|
| reflectance | double | False | a.u. | source:reflectance | Band-adapted reflectance as provided (values sum to ~1 over 16 bands; not interpreted further). |
| wavelength_nm | int64 | False | nm | source:wavelength | Nominal camera band wavelength. |
| color_name | string | False |  | source:color_name | Colour-checker patch name. |
| color_hex | string | False |  | source:color | Display colour of the patch. |
| band | int64 | False |  | source:band | Camera band index (= cube channel index). |
| color_index | int64 | False |  | source:ind | Colour-checker patch number. |
| source_row_index | int32 | False |  | provenance | 0-based data-row position in the raw source file (header excluded). |
| source_file | string | False |  | provenance | Dataset-relative path of the raw source file. |

## `color_checker_frames`

Per-frame metadata of the colour-checker XIMEA cubes (raw and normalised).

- **Grain:** one row per (colour-checker cube, frame)
- **Primary key:** `cube, frame_index`
- **Rows:** 480 · **Row groups:** 1 · **Size:** 0.01 MB
- **Raw sources:** cube metadata / derived

| column | type | nullable | unit | origin | description |
|---|---|---|---|---|---|
| cube | string | False |  | source_path | ximea_raw or ximea_norm. |
| frame_index | int32 | False |  | provenance | Index along axis 0 of the cube. |
| color_name | string | False |  | cube_meta:color | Patch imaged in the frame. |
| time_delta_s | double | False | s | cube_meta:time_delta | Time since start of recording. |
| exposure_ms | int16 | False | ms | cube_meta:exposure | Camera exposure time. |
| image_file | string | False |  | provenance | Dataset-relative path of the hyperspectral cube (.b2nd) that holds the frame. |

## `ref_channels`

Camera channel parameters: nominal wavelength, measured filter characteristics, dark-reference statistics.

- **Grain:** one row per camera channel
- **Primary key:** `channel_index`
- **Rows:** 16 · **Row groups:** 1 · **Size:** 0.01 MB
- **Raw sources:** `intermediates/optics/ximea_filters.csv`, `data/ximea/dark.b2nd`, `intermediates/color_checker/spectrometer_adapted.csv`

| column | type | nullable | unit | origin | description |
|---|---|---|---|---|---|
| channel_index | int8 | False |  | derived | Position on the cube channel (last) axis. |
| filter_id | int8 | False |  | derived | channel_index + 1 (filter number in ximea_filters). |
| nominal_wavelength_nm | int16 | False | nm | source:README.md | Channel wavelength listed in the dataset README. |
| peak_wavelength_nm | int16 | False | nm | derived | Argmax of the filter response curve. |
| peak_response_au | double | False | a.u. | derived | Maximum filter response. |
| centroid_wavelength_nm | double | False | nm | derived | Response-weighted mean wavelength over 400-1000 nm (includes NIR side lobes of the mosaic filters). |
| fwhm_nm | double | False | nm | derived | Width of the contiguous region around the peak above half maximum. |
| secondary_peak_ratio | double | False |  | derived | Highest response outside the main FWHM lobe (+/-10 nm) divided by the peak (spectral cross-talk indicator). |
| dark_mean | double | False | counts | derived | Mean of dark reference for this channel. |
| dark_std | double | False | counts | derived | Std of dark reference for this channel. |
| dark_min | double | False | counts | derived | Min of dark reference. |
| dark_max | double | False | counts | derived | Max of dark reference. |
| colorchecker_band_wavelength_nm | int16 | True | nm | joined | Wavelength assigned to this band in color_checker/spectrometer_adapted (consistency check). |

## `ref_stages`

Stage dictionary from data/metadata.json with pressure, phase and spectrometer label mapping.

- **Grain:** one row per stage label
- **Primary key:** `stage`
- **Rows:** 10 · **Row groups:** 1 · **Size:** 0.01 MB
- **Raw sources:** `data/metadata.json`

| column | type | nullable | unit | origin | description |
|---|---|---|---|---|---|
| stage_order | int8 | False |  | source:metadata.json | Order in metadata.json 'stages'. |
| stage | string | False |  | source:stage | Experimental stage label as written in the raw data (before_clamping | during_clamping_<P>mmHg). |
| pressure_mmhg | int16 | False | mmHg | derived | Upper-arm cuff pressure parsed from stage label; 0 for baseline and rest periods. |
| phase | string | False |  | derived | baseline = before_clamping; clamping = cuff pressure > 0; rest = during_clamping_0mmHg (no-pressure recovery period recorded between clamping stages). |
| spectrometer_stage_label | string | True |  | derived | Matching label in spectrometer.csv, if any. |
| blocks_per_session | int8 | True |  | derived | Number of contiguous blocks of this stage in a complete session (from local cubes; null if unseen). |

## `ref_subjects`

Subject coverage matrix: which modalities are available locally and their key acquisition parameters.

- **Grain:** one row per subject
- **Primary key:** `subject_id`
- **Rows:** 10 · **Row groups:** 1 · **Size:** 0.01 MB
- **Raw sources:** `data/metadata.json`

| column | type | nullable | unit | origin | description |
|---|---|---|---|---|---|
| subject_id | string | False |  | source_path | Canonical subject identifier 'subject_NN' (matches cube file and ROI folder names). |
| cube_status | string | False |  | derived | complete | partial_download | missing (local file system). |
| cube_file | string | True |  | provenance | Dataset-relative path of cube or partial-download stub. |
| cube_bytes | int64 | True | bytes | provenance | Size on disk. |
| n_frames | int32 | True |  | cube_meta | Frames in the cube (complete cubes only). |
| exposure_ms | int16 | True | ms | cube_meta | Exposure (unique per subject). |
| frame_rate_hz | double | True | Hz | derived | 1 / median frame interval. |
| duration_s | double | True | s | cube_meta | Last frame time_delta. |
| n_stage_blocks | int16 | True |  | derived | Contiguous stage blocks in the cube timeline. |
| roi_ids_available | string | False |  | source_path | Comma-separated ROI numbers with local track files. |
| n_roi_rows | int32 | False |  | derived | ROI rows in master_rois for the subject. |
| n_spectra_baseline | int16 | False |  | derived | Replicate spectra at baseline (all ROIs). |
| n_spectra_160mmHg | int16 | False |  | derived | Replicate spectra at 160 mmHg (all ROIs). |
| usable_roi_image_analysis | bool | False |  | derived | True when complete cube AND at least one ROI track exist (ROI-level spectral-temporal extraction possible). |

