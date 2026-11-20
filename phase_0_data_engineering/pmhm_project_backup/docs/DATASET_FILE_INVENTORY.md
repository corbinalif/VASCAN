# SPECTRALPACA — Local Dataset File Inventory

_Generated 2026-11-14T17:03:00Z by `scripts/pmhm_build_dataset.py inventory` (read-only scan; no raw file was modified)._

- Dataset root: `/home/alifhossain/SPECTRALPACA`
- Raw files found: **48**, total **80.28 GB**

## 1. Completeness against `data/metadata.json`

| Subject | HSI cube | ROI 1 | ROI 2 | ROI 3 | ROI 4 | ROI video | subject metadata.json |
|---|---|---|---|---|---|---|---|
| subject_01 | present | present:csv | present:feather | present:csv+feather | present:feather | **MISSING** | **MISSING** |
| subject_02 | present | present:csv+feather | present:csv+feather | present:csv+feather | **MISSING** | **MISSING** | **MISSING** |
| subject_03 | **PARTIAL_DOWNLOAD** | **MISSING** | **MISSING** | **MISSING** | **MISSING** | **MISSING** | **MISSING** |
| subject_04 | present | **MISSING** | **MISSING** | **MISSING** | **MISSING** | **MISSING** | **MISSING** |
| subject_05 | **PARTIAL_DOWNLOAD** | **MISSING** | **MISSING** | **MISSING** | **MISSING** | **MISSING** | **MISSING** |
| subject_06 | **MISSING** | **MISSING** | **MISSING** | **MISSING** | **MISSING** | **MISSING** | **MISSING** |
| subject_07 | **PARTIAL_DOWNLOAD** | **MISSING** | **MISSING** | **MISSING** | **MISSING** | **MISSING** | **MISSING** |
| subject_08 | **PARTIAL_DOWNLOAD** | **MISSING** | **MISSING** | **MISSING** | **MISSING** | **MISSING** | **MISSING** |
| subject_09 | **MISSING** | **MISSING** | **MISSING** | **MISSING** | **MISSING** | **MISSING** | **MISSING** |
| subject_10 | **PARTIAL_DOWNLOAD** | **MISSING** | **MISSING** | **MISSING** | **MISSING** | **MISSING** | **MISSING** |

| Global item | Status |
|---|---|
| `data/ximea/white.npy|white.b2nd` (white_reference) | **MISSING** |
| `data/ximea/dark.npy|dark.b2nd` (dark_reference) | present |
| `code/src/data/*.py (DataLoaderXIMEA)` (loader_code) | **MISSING** |
| `intermediates/color_checker/spectrometer.csv` (color_checker_spectrometer) | **PARTIAL_DOWNLOAD** |

## 2. Files by category

| Category | Files | Size |
|---|---|---|
| calibration_reference | 1 | 10.74 MB |
| color_checker | 4 | 78.06 MB |
| documentation_asset | 8 | 4.02 MB |
| hsi_cube | 3 | 74.35 GB |
| loader_code | 5 | 0.00 MB |
| metadata | 1 | 0.00 MB |
| optics_calibration | 4 | 0.25 MB |
| partial_download | 6 | 5.62 GB |
| project_document | 3 | 0.02 MB |
| roi_track | 11 | 4.70 MB |
| spectrometer | 2 | 212.92 MB |

## 3. Hyperspectral cubes and calibration arrays (`.b2nd`, kept in native format)

| File | Shape (frames, H, W, C) | dtype | chunks | stored chunks | compression ratio | per-frame metadata | size |
|---|---|---|---|---|---|---|---|
| `data/ximea/dark.b2nd` | (272, 512, 16) | float64 | (272, 512, 16) | 1 | 1.675 | — | 10.74 MB |
| `data/ximea/subject_01.b2nd` | (17576, 272, 512, 16) | float16 | (1, 272, 512, 16) | 17,576 | 2.934 | stage, time_delta, exposure | 26.33 GB |
| `data/ximea/subject_02.b2nd` | (17741, 272, 512, 16) | float16 | (1, 272, 512, 16) | 17,741 | 2.912 | stage, time_delta, exposure | 26.77 GB |
| `data/ximea/subject_04.b2nd` | (12840, 272, 512, 16) | float16 | (1, 272, 512, 16) | 12,840 | 2.654 | stage, time_delta, exposure | 21.26 GB |
| `intermediates/color_checker/ximea_norm.b2nd` | (240, 100, 100, 16) | float16 | (1, 100, 100, 16) | 240 | 2.234 | color, time_delta, exposure | 41.96 MB |
| `intermediates/color_checker/ximea_raw.b2nd` | (240, 100, 100, 16) | float16 | (1, 100, 100, 16) | 240 | 2.614 | color, time_delta, exposure | 35.86 MB |

## 4. Partial downloads (Synapse resume stubs — left untouched)

| File | Size |
|---|---|
| `data/ximea/subject_03.b2nd.synapse_download_132463951` | 0.00 MB |
| `data/ximea/subject_05.b2nd.synapse_download_132463953` | 5.62 GB |
| `data/ximea/subject_07.b2nd.synapse_download_132463955` | 0.00 MB |
| `data/ximea/subject_08.b2nd.synapse_download_132463956` | 0.00 MB |
| `data/ximea/subject_10.b2nd.synapse_download_132463958` | 0.00 MB |
| `intermediates/color_checker/spectrometer.csv.synapse_download_132465380` | 0.00 MB |

## 5. Tabular files (Parquet conversion candidates)

| File | Category | Rows | Columns | Size | sha256 (first 12) |
|---|---|---|---|---|---|
| `data/spectrometer/spectrometer.csv` | spectrometer | 4,397,250 | `wavelength [nm]`, `reflectance [a.u.]`, `subject`, `stage`, `ROI` | 167.37 MB | `afde74369b27` |
| `data/spectrometer/spectrometer.feather` | spectrometer | 4,397,250 | `wavelength [nm]`, `reflectance [a.u.]`, `subject`, `stage`, `ROI` | 45.54 MB | `2912bdab8770` |
| `intermediates/color_checker/spectrometer_adapted.csv` | color_checker | 3,840 | `reflectance`, `wavelength`, `color_name`, `color`, `band`, `ind` | 0.17 MB | `d4f7e1ec7d21` |
| `intermediates/color_checker/spectrometer_adapted.feather` | color_checker | 3,840 | `reflectance`, `wavelength`, `color_name`, `color`, `band`, `ind` | 0.06 MB | `87ba500ac4da` |
| `intermediates/optics/xenon_light_source.csv` | optics_calibration | 2,033 | `wavelength [nm]`, `relative_irradiance [a.u.]` | 0.03 MB | `5722bbeb91f8` |
| `intermediates/optics/xenon_light_source.feather` | optics_calibration | 2,033 | `wavelength [nm]`, `relative_irradiance [a.u.]`, `__index_level_0__` | 0.02 MB | `68718c171e6e` |
| `intermediates/optics/ximea_filters.csv` | optics_calibration | 9,616 | `Wavelength [nm]`, `filter`, `Filter response [a.u.]` | 0.16 MB | `5a8a19a1c935` |
| `intermediates/optics/ximea_filters.feather` | optics_calibration | 9,616 | `Wavelength [nm]`, `filter`, `Filter response [a.u.]` | 0.05 MB | `abaca3b7ae1b` |
| `intermediates/rois/subject_01/roi_1.csv` | roi_track | 17,836 | `y1`, `x1`, `y2`, `x2`, `stage`, `time_delta` | 0.77 MB | `f03a55df35eb` |
| `intermediates/rois/subject_01/roi_2.feather` | roi_track | 17,836 | `y1`, `x1`, `y2`, `x2`, `stage`, `time_delta` | 0.15 MB | `6fcce977e83e` |
| `intermediates/rois/subject_01/roi_3.csv` | roi_track | 17,836 | `y1`, `x1`, `y2`, `x2`, `stage`, `time_delta` | 0.74 MB | `012921a013d0` |
| `intermediates/rois/subject_01/roi_3.feather` | roi_track | 17,836 | `y1`, `x1`, `y2`, `x2`, `stage`, `time_delta` | 0.15 MB | `e47109c2a3df` |
| `intermediates/rois/subject_01/roi_4.feather` | roi_track | 17,836 | `y1`, `x1`, `y2`, `x2`, `stage`, `time_delta` | 0.15 MB | `423c18dbc782` |
| `intermediates/rois/subject_02/roi_1.csv` | roi_track | 17,993 | `y1`, `x1`, `y2`, `x2`, `stage`, `time_delta` | 0.78 MB | `36b0513de410` |
| `intermediates/rois/subject_02/roi_1.feather` | roi_track | 17,993 | `y1`, `x1`, `y2`, `x2`, `stage`, `time_delta` | 0.14 MB | `ab2b4caa4ebf` |
| `intermediates/rois/subject_02/roi_2.csv` | roi_track | 17,993 | `y1`, `x1`, `y2`, `x2`, `stage`, `time_delta` | 0.78 MB | `2f71781dc2e8` |
| `intermediates/rois/subject_02/roi_2.feather` | roi_track | 17,993 | `y1`, `x1`, `y2`, `x2`, `stage`, `time_delta` | 0.15 MB | `56c11da6b458` |
| `intermediates/rois/subject_02/roi_3.csv` | roi_track | 17,993 | `y1`, `x1`, `y2`, `x2`, `stage`, `time_delta` | 0.74 MB | `cc1008c005e5` |
| `intermediates/rois/subject_02/roi_3.feather` | roi_track | 17,993 | `y1`, `x1`, `y2`, `x2`, `stage`, `time_delta` | 0.15 MB | `3dd2ed7c1a43` |

## 6. Other files

| File | Category | Size |
|---|---|---|
| `README.md` | project_document | 0.01 MB |
| `assets/animation.gif` | documentation_asset | 4.01 MB |
| `assets/channels.svg` | documentation_asset | 0.00 MB |
| `assets/files.svg` | documentation_asset | 0.00 MB |
| `assets/images.svg` | documentation_asset | 0.00 MB |
| `assets/perfusion.svg` | documentation_asset | 0.00 MB |
| `assets/size.svg` | documentation_asset | 0.00 MB |
| `assets/subjects.svg` | documentation_asset | 0.00 MB |
| `assets/videos.svg` | documentation_asset | 0.00 MB |
| `code/.env` | loader_code | 0.00 MB |
| `code/LICENSE` | loader_code | 0.00 MB |
| `code/requirements.txt` | loader_code | 0.00 MB |
| `code/setup.cfg` | loader_code | 0.00 MB |
| `code/setup.py` | loader_code | 0.00 MB |
| `data/metadata.json` | metadata | 0.00 MB |
| `projectproposal.md` | project_document | 0.01 MB |
| `spectralpaca.ipynb` | project_document | 0.01 MB |
