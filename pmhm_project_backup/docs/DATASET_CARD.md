# SPECTRALPACA — PMHM Primary Dataset Card

_Auto-generated from `data/processed/parquet` on 2026-11-14T17:03:44Z (pipeline v0.1.0). Every value below is computed from the Parquet files; regenerate with `python scripts/pmhm_build_dataset.py card`._

> **Standalone dataset file:** `data/processed/spectralpaca_pmhm_dataset.parquet`. This one file holds everything (ROI spectral time series extracted from the video, spectrometer, calibration, protocol, participants) and works without the original download. See `docs/STANDALONE_DATASET.md`.
> Build tables: `data/processed/parquet/` (10 tables the standalone file is built from; these point to the raw `.b2nd` cubes through `image_file` + `frame_index`).
> Load with `from pmhm.data.catalog import PMHMDataset, CubeReader` (see §8).

## 1. Dataset parameters at a glance

| Parameter | Value | Source |
|---|---|---|
| Study | SPECTRALPACA — Ayala et al., *Scientific Data* 2024, doi:10.1038/s41597-024-03307-y, Synapse syn51625685, CC BY 4.0 | README.md |
| Participants in study | **10** healthy volunteers (right-hand palm) | data/metadata.json |
| Participants with complete HSI cube locally | **3 / 10** (subject_01, subject_02, subject_04) | ref_subjects |
| Participants usable for ROI-level image analysis now | **2 / 10** (subject_01, subject_02) | ref_subjects |
| Participants with spectrometer reference | **10 / 10** | master_spectrometer |
| Camera | XIMEA MQ022HG-IM-SM4x4-VIS snapshot mosaic, **16 channels**, 272 x 512 px | ref_channels, cube header |
| Channel wavelengths (nominal, cube order) | 488, 496, 478, 465, 598, 609, 585, 574, 641, 493, 632, 622, 538, 550, 524, 511 nm | ref_channels |
| Camera spectral span | **465–641 nm** (visible only; not continuous 500–900 nm) | ref_channels |
| Filter FWHM | 6–21 nm; secondary-lobe ratio up to 0.81 | ref_channels |
| Cube storage | float16, blosc2 NDArray, 1 frame per chunk | cube header |
| Frames per subject | subject_01: 17,576, subject_02: 17,741, subject_04: 12,840 | master_frames |
| Frame rate / exposure | subject_01: 25.0 Hz @ 40 ms, subject_02: 25.0 Hz @ 40 ms, subject_04: 12.0 Hz @ 83 ms | master_frames |
| Recording duration | 1100 s, 1100 s, 1100 s | master_frames |
| Protocol | baseline → 8 cuff stages (20, 40, 60, 80, 100, 120, 140, 160 mmHg), each followed by a no-pressure rest; **17 blocks/session**, 8 rest periods | ref_stages, master_frames |
| Tracked ROIs | 4 per subject (study design); box 20 x 20 px; 125,323 tracked rows locally | master_rois |
| Spectrometer | Ocean Insight HR2000+; **550 wavelengths, 425.4–674.8 nm**; 7,995 spectra (98–100 per subject×stage×ROI); stages: baseline and 160 mmHg | master_spectrometer |
| Calibration references | dark: **present** (`data/ximea/dark.b2nd`, 272x512x16, mean 10.9 counts); white: **MISSING locally** | ref_channels |
| Validation | 130 passed · 1 warnings · **0 failed** of 131 checks | reports/validation_full.md |

## 2. Subject × modality coverage (local copy)

| subject_id | cube_status | n_frames | exposure_ms | frame_rate_hz | roi_ids_available | n_roi_rows | n_spectra_baseline | n_spectra_160mmHg | usable_roi_image_analysis |
|---|---|---|---|---|---|---|---|---|---|
| subject_01 | complete | 17576 | 40 | 25.0 | 1,2,3,4 | 71344 | 398 | 400 | **YES** |
| subject_02 | complete | 17741 | 40 | 25.0 | 1,2,3 | 53979 | 400 | 398 | **YES** |
| subject_03 | **PARTIAL_DOWNLOAD** |  |  |  | **none** | 0 | 400 | 400 | **NO** |
| subject_04 | complete | 12840 | 83 | 12.0 | **none** | 0 | 400 | 400 | **NO** |
| subject_05 | **PARTIAL_DOWNLOAD** |  |  |  | **none** | 0 | 400 | 400 | **NO** |
| subject_06 | **MISSING** |  |  |  | **none** | 0 | 400 | 400 | **NO** |
| subject_07 | **PARTIAL_DOWNLOAD** |  |  |  | **none** | 0 | 400 | 400 | **NO** |
| subject_08 | **PARTIAL_DOWNLOAD** |  |  |  | **none** | 0 | 400 | 400 | **NO** |
| subject_09 | **MISSING** |  |  |  | **none** | 0 | 400 | 399 | **NO** |
| subject_10 | **PARTIAL_DOWNLOAD** |  |  |  | **none** | 0 | 400 | 400 | **NO** |

Spectrometer data are complete for all subjects; image-based analysis is limited by the incomplete local download (see `docs/DATASET_FILE_INVENTORY.md`).

## 3. Parquet tables (primary dataset)

| table | rows | grain | primary_key | MB |
|---|---|---|---|---|
| master_rois | 125323 | one row per (subject, ROI, tracked time point) | subject_id, roi_id, source_row_index | 1.48 |
| master_frames | 48157 | one row per (subject, cube frame) | subject_id, frame_index | 0.95 |
| master_spectrometer | 4397250 | one row per (subject, stage, ROI, replicate spectrum, wavelength) | subject_id, stage, roi_id, spectrum_index, wavelength_index | 35.56 |
| optics_ximea_filters | 9616 | one row per (filter, wavelength sample) | filter_id, wavelength_sample_index | 0.12 |
| optics_xenon_light_source | 2033 | one row per wavelength | source_row_index | 0.04 |
| color_checker_spectrometer_adapted | 3840 | one row per raw-file row (colour patch x camera band x replicate) | source_row_index | 0.07 |
| color_checker_frames | 480 | one row per (colour-checker cube, frame) | cube, frame_index | 0.01 |
| ref_channels | 16 | one row per camera channel | channel_index | 0.01 |
| ref_stages | 10 | one row per stage label | stage | 0.01 |
| ref_subjects | 10 | one row per subject | subject_id | 0.01 |

Join keys: `subject_id` (all), `frame_index` (rois ↔ frames ↔ cube axis 0), `stage` (all ↔ ref_stages), `roi_id` (rois ↔ spectrometer, group level only), `channel_index` (cube last axis ↔ ref_channels ↔ optics_ximea_filters). The spectrometer has **no timestamps**, so it links to ROI tracks at the (subject, ROI, stage) level only — it is kept as a separate table by design.

## 4. Session timeline (stage blocks)

| block | stage | phase | subject_01 duration (s) | subject_02 duration (s) | subject_04 duration (s) |
|---|---|---|---|---|---|
| 0 | before_clamping | baseline | 123.7 | 124.5 | 122.3 |
| 1 | during_clamping_20mmHg | clamping | 65.4 | 64.1 | 67.2 |
| 2 | during_clamping_0mmHg | rest | 75.8 | 61.9 | 60.2 |
| 3 | during_clamping_40mmHg | clamping | 55.2 | 60.1 | 58.6 |
| 4 | during_clamping_0mmHg | rest | 58.4 | 54.2 | 61.0 |
| 5 | during_clamping_60mmHg | clamping | 51.7 | 61.7 | 61.6 |
| 6 | during_clamping_0mmHg | rest | 58.8 | 61.2 | 58.3 |
| 7 | during_clamping_80mmHg | clamping | 59.9 | 58.2 | 56.9 |
| 8 | during_clamping_0mmHg | rest | 60.2 | 61.4 | 62.0 |
| 9 | during_clamping_100mmHg | clamping | 59.1 | 58.0 | 58.9 |
| 10 | during_clamping_0mmHg | rest | 63.7 | 61.0 | 62.3 |
| 11 | during_clamping_120mmHg | clamping | 54.5 | 58.9 | 64.8 |
| 12 | during_clamping_0mmHg | rest | 63.6 | 60.9 | 52.8 |
| 13 | during_clamping_140mmHg | clamping | 56.6 | 58.6 | 58.7 |
| 14 | during_clamping_0mmHg | rest | 61.1 | 61.4 | 61.8 |
| 15 | during_clamping_160mmHg | clamping | 59.9 | 58.1 | 59.5 |
| 16 | during_clamping_0mmHg | rest | 34.7 | 40.8 | 47.0 |

Unrecorded gaps > 1 s in the frame timeline (e.g. cuff inflation before the first clamping stage):

| subject_id | stage_block_index | stage | time_delta_s | gap_s |
|---|---|---|---|---|
| subject_01 | 1 | during_clamping_20mmHg | 159.03 | 35.38 |
| subject_02 | 1 | during_clamping_20mmHg | 154.31 | 29.81 |
| subject_02 | 4 | during_clamping_0mmHg | 343.26 | 2.76 |
| subject_04 | 1 | during_clamping_20mmHg | 146.94 | 24.66 |

## 5. Camera channels

| channel_index | nominal_wavelength_nm | peak_wavelength_nm | fwhm_nm | secondary_peak_ratio | dark_mean | dark_std |
|---|---|---|---|---|---|---|
| 0 | 488 | 488 | 18.0 | 0.334 | 10.836 | 2.546 |
| 1 | 496 | 498 | 11.0 | 0.205 | 10.819 | 2.511 |
| 2 | 478 | 478 | 8.0 | 0.453 | 10.844 | 2.516 |
| 3 | 465 | 463 | 21.0 | 0.163 | 10.825 | 2.513 |
| 4 | 598 | 598 | 7.0 | 0.815 | 10.871 | 2.544 |
| 5 | 609 | 609 | 10.0 | 0.505 | 10.882 | 2.513 |
| 6 | 585 | 586 | 7.0 | 0.367 | 10.89 | 2.516 |
| 7 | 574 | 574 | 7.0 | 0.368 | 10.851 | 2.509 |
| 8 | 641 | 643 | 13.0 | 0.583 | 10.85 | 2.491 |
| 9 | 493 | 492 | 10.0 | 0.634 | 10.839 | 2.457 |
| 10 | 632 | 630 | 15.0 | 0.647 | 10.854 | 2.457 |
| 11 | 622 | 622 | 11.0 | 0.462 | 10.842 | 2.464 |
| 12 | 538 | 538 | 8.0 | 0.141 | 10.872 | 2.508 |
| 13 | 550 | 551 | 6.0 | 0.205 | 10.881 | 2.471 |
| 14 | 524 | 525 | 8.0 | 0.153 | 10.894 | 2.475 |
| 15 | 511 | 513 | 11.0 | 0.154 | 10.859 | 2.468 |

## 6. Spectrometer spectra per subject × stage × ROI

| subject_id | base·ROI1 | base·ROI2 | base·ROI3 | base·ROI4 | 160·ROI1 | 160·ROI2 | 160·ROI3 | 160·ROI4 |
|---|---|---|---|---|---|---|---|---|
| subject_01 | 99 | 100 | 100 | 99 | 100 | 100 | 100 | 100 |
| subject_02 | 100 | 100 | 100 | 100 | 98 | 100 | 100 | 100 |
| subject_03 | 100 | 100 | 100 | 100 | 100 | 100 | 100 | 100 |
| subject_04 | 100 | 100 | 100 | 100 | 100 | 100 | 100 | 100 |
| subject_05 | 100 | 100 | 100 | 100 | 100 | 100 | 100 | 100 |
| subject_06 | 100 | 100 | 100 | 100 | 100 | 100 | 100 | 100 |
| subject_07 | 100 | 100 | 100 | 100 | 100 | 100 | 100 | 100 |
| subject_08 | 100 | 100 | 100 | 100 | 100 | 100 | 100 | 100 |
| subject_09 | 100 | 100 | 100 | 100 | 100 | 100 | 99 | 100 |
| subject_10 | 100 | 100 | 100 | 100 | 100 | 100 | 100 | 100 |

Reflectance (a.u., as provided): min -7.55, median of group medians 15.71, max 255.46; negative values are kept and flagged (`flag_negative_reflectance`).

## 7. Validation and data-quality findings

- **130/131 checks passed, 0 failed** (full report: `reports/validation_full.md`). Every Parquet value of source origin was compared with the raw CSV, and also with the feather copy where one exists. Raw-file SHA-256 hashes were re-verified after conversion.
- master_spectrometer: negative_reflectance_values — 14,705 rows < 0 (kept unmodified; flagged)
- 1,796 ROI rows were tracked after the last cube frame (~1100 s). They are **kept** with `frame_index = null` and `has_image_frame = false`.
- `optics_ximea_filters.wavelength_nm` is integer-rounded in the raw file. Each filter has 601 samples but only 581 unique wavelengths, so the key is `wavelength_sample_index`.
- Xenon spectrum: 491 rows with negative irradiance (kept, flagged).
- `dark.b2nd` has no stored exposure, while subjects were recorded at 40 ms and 83 ms. The white reference is missing, so reflectance normalisation from local data is **not yet possible**.
- ROI centre motion: mean 0.073 px/frame, max 3.16 px.

## 8. How to use this dataset

```python
import sys; sys.path.insert(0, 'src')
from pmhm.data.catalog import PMHMDataset, CubeReader
ds = PMHMDataset()                      # data/processed/parquet
ds.tables(); ds.describe('master_rois') # catalogue + column units/origins (read from the files)
rois = ds.rois('subject_01', roi=1, stage='during_clamping_160mmHg')
spec = ds.spectra(subject='subject_05', stage='before_clamping', roi=2, wide=True)  # 100 x 550
cube = CubeReader('subject_01')         # lazy: one ROI patch decompresses ~1 block
r = rois.iloc[0]; s = cube.roi_mean_spectrum(int(r.frame_index), r.y1, r.x1, r.y2, r.x2)
```

## 9. Traceability to `projectproposal.md`

| Proposal requirement | Status | Evidence |
|---|---|---|
| §2 Recursive inspection; supported files identified | Done | docs/DATASET_FILE_INVENTORY.md (48 raw files) |
| §2 Memory-safe chunked streaming (Pandas/PyArrow) | Done | adaptive chunks start at 5,000 rows; peak conversion RSS ~535 MB |
| §2 Snappy Parquet; separate masters for different schemas | Done | 10 tables, §3 |
| §2 `master_rois.parquet` | Done | 125,323 rows |
| §2 Spectrometer tables | Done | master_spectrometer, 7,995 spectra |
| §2 Optical calibration and metadata tables | Done | optics_ximea_filters, optics_xenon_light_source, ref_channels, ref_stages, ref_subjects, colour checker |
| §2 Manifests: sources, rows, schemas, dtypes, status, validation | Done | _manifest/conversion_manifest.*, catalog.json, validation_report.json |
| §2 Provenance: subject, ROI, frame, condition, source file | Done | subject_id, roi_id, frame_index, stage/phase/block, source_file, source_row_index |
| §2 Single-subject pilot before full scale | Done | data/processed/pilot_subject_01 + reports/validation_pilot_subject_01.md |
| §2 Integrity: counts, rows, columns, dtypes, missing, record-level | Done | reports/validation_full.md |
| §2 Raw files unchanged | Done | SHA-256 of every source re-verified after conversion |
| §3 Cubes and references kept native, lazy access | Done (no DataLoaderXIMEA locally) | CubeReader (blosc2 slicing). `code/src` is empty in the download |
| §3 Dark/white correction, reflectance normalisation | **BLOCKED** | white reference missing; dark exposure undocumented |
| §3 ROI ↔ frame linkage across stages incl. reperfusion | Done | frame_index exact join; stage_block_index, preceding_pressure_mmhg, time_in_block_s |
| §3 Synchronisation of frames, ROIs, spectrometer, stages | Partial | frames↔ROIs exact; spectrometer has no timestamps, so linkage is group-level only |
| §3 Invalid / missing frames, tracking inconsistencies | Partial | gaps, unmatched rows, displacement, bbox bounds flagged. Per-channel SNR still pending |
| §4 EDA | Pending | next phase (docs/NEXT_ACTIONS.md) |
| §6 Configs, logs, manifests, version control | Partial | configs/pmhm.yaml, logs/, manifests; the workspace is not yet a git repository |
| §9 Join-vs-separate decision based on actual schemas | Decided | docs/TECHNICAL_DECISIONS.md D-004 |

## 10. Scientific scope

These data come from **10 healthy volunteers** imaged with a **16-channel visible-range camera**. They support technical development and the analysis of physiological responses to graded cuff occlusion. They do **not** establish PAD diagnostic validity, and image-derived features are not perfusion measurements without independent validation. The spectrometer gives diffuse reflectance at baseline and 160 mmHg only. It is not an StO2 or perfusion ground truth.

