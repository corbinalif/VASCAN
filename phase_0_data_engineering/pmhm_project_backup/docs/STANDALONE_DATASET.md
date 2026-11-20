# Standalone dataset file — `data/processed/spectralpaca_pmhm_dataset.parquet`

_Generated from the file's embedded metadata. Regenerate with `scripts/pmhm_build_dataset.py card`._

**This one file is the complete dataset.** It needs neither the original SPECTRALPACA download nor the PMHM code: any Parquet reader (pandas, pyarrow, polars, R arrow, DuckDB) can open it.

- Size **59.3 MB**, **4,586,255 rows**, **81 columns**
- Validation: **22/23 checks passed, 0 failed** (`reports/validation_standalone.md`). 400 random ROI rows were re-extracted from the original cubes and matched.
- SHA-256: `eb77b66a76f27eab5a053fe564954d9fe4ef584423f1053cb46542ac38961226`

## What is inside: one row per record, kind given by `record_type`

| record_type | rows | meaning |
|---|---|---|
| `roi_frame` | 125,323 | One tracked palm ROI in one video frame: ROI box + per-channel mean/std of the raw camera counts inside the box (extracted from the hyperspectral cube). Rows tracked after the cube end have null spectral values (has_image_frame = false). |
| `frame` | 48,157 | One video frame of a locally complete cube: stage, time, exposure (no pixel data). |
| `spectrometer` | 4,397,250 | One wavelength sample of one HR2000+ reference spectrum (value = diffuse reflectance, a.u.). |
| `camera_filter` | 9,616 | One wavelength sample of one camera filter response curve (value = response, a.u.). |
| `light_source` | 2,033 | One wavelength sample of the xenon light-source spectrum (value = relative irradiance, a.u.). |
| `color_checker` | 3,840 | One colour-checker patch reference value for one camera band (value = band-adapted reflectance). |
| `channel` | 16 | One camera channel: nominal/peak wavelength, FWHM, cross-talk, dark-reference statistics. |
| `stage` | 10 | One protocol stage: cuff pressure, phase, spectrometer label, blocks per session. |
| `subject` | 10 | One participant: data availability and acquisition parameters. |

Columns that a record type doesn't use are empty (null). Each column description below starts with the record types it applies to.

## How to read it

```python
import pandas as pd
f = 'spectralpaca_pmhm_dataset.parquet'
roi = pd.read_parquet(f, filters=[('record_type', '==', 'roi_frame')]).dropna(axis=1, how='all')
spec = pd.read_parquet(f, filters=[('record_type', '==', 'spectrometer'), ('subject_id', '==', 'subject_03')])
wide = spec.pivot_table(index=['stage', 'roi_id', 'spectrum_index'], columns='wavelength_nm', values='value')
channels = pd.read_parquet(f, filters=[('record_type', '==', 'channel')]).dropna(axis=1, how='all')
```

## Important limits

- ROI values are raw camera counts. No white reference is available in the source download and the dark reference exposure is undocumented; dark statistics per channel are given in record_type='channel' rows.
- 10 healthy volunteers, 16 visible channels (465-641 nm). Not a PAD cohort; values are not StO2 or perfusion measurements.
- Image data are reduced to the **tracked ROIs** (mean and std of each of the 16 channels over the 20×20 px box). Full video frames are not included, because they would be ~214 GB. Participants without ROI tracks in the source download (subject_04) have `frame` rows but no `roi_frame` spectra.

## Columns

| column | type | unit | description |
|---|---|---|---|
| `record_type` | string |  | [roi_frame,frame,spectrometer,camera_filter,light_source,color_checker,channel,stage,subject] Row kind; filter on it first. Values: roi_frame, frame, spectrometer, camera_filter, light_source, color_checker, channel, stage, subject |
| `subject_id` | string |  | [roi_frame,frame,spectrometer,subject] Participant 'subject_NN'. |
| `roi_id` | int8 |  | [roi_frame,spectrometer] Palm ROI number 1-4. |
| `frame_index` | int32 |  | [roi_frame,frame] Frame number in the original cube (axis 0). Null for ROI rows tracked after the cube end. |
| `time_delta_s` | double | s | [roi_frame,frame] Time since start of recording. |
| `stage` | string |  | [roi_frame,frame,spectrometer,stage] Protocol stage label (before_clamping | during_clamping_<P>mmHg). |
| `pressure_mmhg` | int16 | mmHg | [roi_frame,frame,spectrometer,stage] Upper-arm cuff pressure; 0 at baseline and rest. |
| `phase` | string |  | [roi_frame,frame,spectrometer,stage] baseline | clamping | rest (no-pressure recovery between clamping stages). |
| `stage_block_index` | int16 |  | [roi_frame,frame] Contiguous stage segment 0-16 in the session timeline (distinguishes the 8 rest periods). |
| `preceding_pressure_mmhg` | int16 | mmHg | [roi_frame,frame] For rest rows: pressure of the clamping block just before (reperfusion context). |
| `time_in_block_s` | double | s | [roi_frame,frame] Time since block start. |
| `exposure_ms` | int16 | ms | [roi_frame,frame,subject] Camera exposure time. |
| `has_image_frame` | bool |  | [roi_frame] True when spectral values were extracted (a cube frame exists for this time point). |
| `y1` | int16 | px | [roi_frame] ROI box top row. |
| `x1` | int16 | px | [roi_frame] ROI box left column. |
| `y2` | int16 | px | [roi_frame] ROI box bottom row (exclusive). |
| `x2` | int16 | px | [roi_frame] ROI box right column (exclusive). |
| `displacement_px` | float | px | [roi_frame] ROI centre motion since the previous frame (tracking/motion indicator). |
| `ch00_488nm_mean` | float | counts | [roi_frame] Mean raw camera value of channel 0 (488 nm nominal) over the ROI pixels (no dark/white correction). |
| `ch01_496nm_mean` | float | counts | [roi_frame] Mean raw camera value of channel 1 (496 nm nominal) over the ROI pixels (no dark/white correction). |
| `ch02_478nm_mean` | float | counts | [roi_frame] Mean raw camera value of channel 2 (478 nm nominal) over the ROI pixels (no dark/white correction). |
| `ch03_465nm_mean` | float | counts | [roi_frame] Mean raw camera value of channel 3 (465 nm nominal) over the ROI pixels (no dark/white correction). |
| `ch04_598nm_mean` | float | counts | [roi_frame] Mean raw camera value of channel 4 (598 nm nominal) over the ROI pixels (no dark/white correction). |
| `ch05_609nm_mean` | float | counts | [roi_frame] Mean raw camera value of channel 5 (609 nm nominal) over the ROI pixels (no dark/white correction). |
| `ch06_585nm_mean` | float | counts | [roi_frame] Mean raw camera value of channel 6 (585 nm nominal) over the ROI pixels (no dark/white correction). |
| `ch07_574nm_mean` | float | counts | [roi_frame] Mean raw camera value of channel 7 (574 nm nominal) over the ROI pixels (no dark/white correction). |
| `ch08_641nm_mean` | float | counts | [roi_frame] Mean raw camera value of channel 8 (641 nm nominal) over the ROI pixels (no dark/white correction). |
| `ch09_493nm_mean` | float | counts | [roi_frame] Mean raw camera value of channel 9 (493 nm nominal) over the ROI pixels (no dark/white correction). |
| `ch10_632nm_mean` | float | counts | [roi_frame] Mean raw camera value of channel 10 (632 nm nominal) over the ROI pixels (no dark/white correction). |
| `ch11_622nm_mean` | float | counts | [roi_frame] Mean raw camera value of channel 11 (622 nm nominal) over the ROI pixels (no dark/white correction). |
| `ch12_538nm_mean` | float | counts | [roi_frame] Mean raw camera value of channel 12 (538 nm nominal) over the ROI pixels (no dark/white correction). |
| `ch13_550nm_mean` | float | counts | [roi_frame] Mean raw camera value of channel 13 (550 nm nominal) over the ROI pixels (no dark/white correction). |
| `ch14_524nm_mean` | float | counts | [roi_frame] Mean raw camera value of channel 14 (524 nm nominal) over the ROI pixels (no dark/white correction). |
| `ch15_511nm_mean` | float | counts | [roi_frame] Mean raw camera value of channel 15 (511 nm nominal) over the ROI pixels (no dark/white correction). |
| `ch00_488nm_std` | float | counts | [roi_frame] Standard deviation over the ROI pixels of channel 0 (488 nm). |
| `ch01_496nm_std` | float | counts | [roi_frame] Standard deviation over the ROI pixels of channel 1 (496 nm). |
| `ch02_478nm_std` | float | counts | [roi_frame] Standard deviation over the ROI pixels of channel 2 (478 nm). |
| `ch03_465nm_std` | float | counts | [roi_frame] Standard deviation over the ROI pixels of channel 3 (465 nm). |
| `ch04_598nm_std` | float | counts | [roi_frame] Standard deviation over the ROI pixels of channel 4 (598 nm). |
| `ch05_609nm_std` | float | counts | [roi_frame] Standard deviation over the ROI pixels of channel 5 (609 nm). |
| `ch06_585nm_std` | float | counts | [roi_frame] Standard deviation over the ROI pixels of channel 6 (585 nm). |
| `ch07_574nm_std` | float | counts | [roi_frame] Standard deviation over the ROI pixels of channel 7 (574 nm). |
| `ch08_641nm_std` | float | counts | [roi_frame] Standard deviation over the ROI pixels of channel 8 (641 nm). |
| `ch09_493nm_std` | float | counts | [roi_frame] Standard deviation over the ROI pixels of channel 9 (493 nm). |
| `ch10_632nm_std` | float | counts | [roi_frame] Standard deviation over the ROI pixels of channel 10 (632 nm). |
| `ch11_622nm_std` | float | counts | [roi_frame] Standard deviation over the ROI pixels of channel 11 (622 nm). |
| `ch12_538nm_std` | float | counts | [roi_frame] Standard deviation over the ROI pixels of channel 12 (538 nm). |
| `ch13_550nm_std` | float | counts | [roi_frame] Standard deviation over the ROI pixels of channel 13 (550 nm). |
| `ch14_524nm_std` | float | counts | [roi_frame] Standard deviation over the ROI pixels of channel 14 (524 nm). |
| `ch15_511nm_std` | float | counts | [roi_frame] Standard deviation over the ROI pixels of channel 15 (511 nm). |
| `roi_patch_min` | float | counts | [roi_frame] Minimum value in the ROI patch (all channels). |
| `roi_patch_max` | float | counts | [roi_frame] Maximum value in the ROI patch (all channels). |
| `frame_interval_s` | double | s | [frame] Time since previous frame. |
| `n_rois_tracked` | int8 |  | [frame] ROI tracks available for this frame. |
| `wavelength_nm` | double | nm | [spectrometer,camera_filter,light_source,color_checker,channel] Wavelength of the sample (channel rows: nominal wavelength). |
| `wavelength_index` | int16 |  | [spectrometer,camera_filter] Sample position on the instrument's wavelength grid. |
| `value` | double | a.u. | [spectrometer,camera_filter,light_source,color_checker] Measured value, unmodified; meaning given by value_quantity. |
| `value_quantity` | string |  | [spectrometer,camera_filter,light_source,color_checker] diffuse_reflectance | filter_response | relative_irradiance | band_adapted_reflectance. |
| `flag_negative_value` | bool |  | [spectrometer,light_source] value < 0 (noise floor). |
| `spectrum_index` | int16 |  | [spectrometer] Replicate spectrum number within (subject, stage, ROI). |
| `channel_index` | int8 |  | [camera_filter,color_checker,channel] Camera channel = position in the cube's channel axis (ch00..ch15 columns). |
| `color_name` | string |  | [color_checker] Colour-checker patch name. |
| `color_index` | int16 |  | [color_checker] Colour-checker patch number. |
| `color_hex` | string |  | [color_checker] Display colour of the patch. |
| `peak_wavelength_nm` | int16 | nm | [channel] Filter response peak. |
| `fwhm_nm` | double | nm | [channel] Filter full width at half maximum. |
| `secondary_peak_ratio` | double |  | [channel] Out-of-band lobe / peak (cross-talk). |
| `dark_mean` | double | counts | [channel] Dark-reference mean for the channel. |
| `dark_std` | double | counts | [channel] Dark-reference standard deviation. |
| `stage_order` | int8 |  | [stage] Order of the stage in the protocol list. |
| `spectrometer_stage_label` | string |  | [stage] Label used in the spectrometer file. |
| `blocks_per_session` | int8 |  | [stage] Times the stage occurs per session. |
| `cube_status` | string |  | [subject] complete | partial_download | missing in the source download. |
| `n_frames` | int32 |  | [subject] Video frames recorded. |
| `frame_rate_hz` | double | Hz | [subject] Video frame rate. |
| `duration_s` | double | s | [subject] Recording duration. |
| `roi_ids_available` | string |  | [subject] ROIs with tracking data. |
| `n_spectra_baseline` | int16 |  | [subject] Spectrometer spectra at baseline. |
| `n_spectra_160mmHg` | int16 |  | [subject] Spectrometer spectra at 160 mmHg. |
| `source_file` | string |  | [roi_frame,frame,spectrometer,camera_filter,light_source,color_checker,channel,stage,subject] Raw file of the original download the row came from. |
| `source_row_index` | int64 |  | [roi_frame,spectrometer,camera_filter,light_source,color_checker] Row position in that raw file. |

## File-level metadata keys

- `pmhm.table`
- `pmhm.grain`
- `pmhm.description`
- `pmhm.primary_key`
- `pmhm.title`
- `pmhm.dataset`
- `pmhm.license`
- `pmhm.pipeline_version`
- `pmhm.created_utc`
- `pmhm.record_types`
- `pmhm.how_to_read`
- `pmhm.camera`
- `pmhm.spectrometer`
- `pmhm.calibration_note`
- `pmhm.scope_note`
- `pmhm.built_from`
