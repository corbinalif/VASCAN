# PMHM — Project Status

_Last updated 2026-11-14 (session 1)._

## Phase status
| Phase | Status |
|---|---|
| 1 Dataset audit | **Done**. `docs/DATASET_FILE_INVENTORY.md` |
| 2 Data integrity and calibration | **Integrity done** (131/131 checks pass). **Calibration blocked**: no white reference |
| 3–10 | Not started |

## Delivered in session 1
- Read-only inventory of 48 raw files (80.3 GB), checked against `metadata.json` for completeness.
- `pmhm` pipeline (`src/pmhm`, `scripts/pmhm_build_dataset.py`, `configs/pmhm.yaml`): inventory → pilot
  (subject_01) → validate → full conversion → validate → dataset card. Runs end-to-end in ~50 s.
- Primary dataset `data/processed/parquet/`, 10 tables, 37 MB:
  `master_rois` (125,323) · `master_frames` (48,157) · `master_spectrometer` (4,397,250 rows = 7,995 spectra) ·
  `optics_ximea_filters` · `optics_xenon_light_source` · `color_checker_spectrometer_adapted` ·
  `color_checker_frames` · `ref_channels` · `ref_stages` · `ref_subjects`.
- Validation: pilot 115/115, full 131/131 passed, 0 failed, 1 informational warning (negative reflectance values).
  Every source value was compared, CSV and feather copies were cross-checked, and raw SHA-256 hashes were re-verified.
- Generated docs: `DATASET_CARD.md` (parameters, coverage, timeline, channels, proposal traceability) and
  `DATA_DICTIONARY.md` (every column: type, unit, origin, description).
- Loader `PMHMDataset` and lazy `CubeReader`: 200 ROI spectra in 0.2 s for +0.7 MB RAM.
- 10 unit tests pass.

## Session 2 (2026-11-14): standalone single-file dataset
- The user's requirement: **one Parquet file usable as the dataset without the original download.** Session 1
  produced 10 tables that only *point to* the image cubes, which did not meet it.
- Built `data/processed/spectralpaca_pmhm_dataset.parquet`: 59.3 MB, 4,586,255 rows, 81 columns, 9 record types.
  It holds ROI spectral time series extracted from the cubes (125,323 ROI-frames, 16-channel mean and std),
  frames, the full spectrometer, filters, light source, colour checker, channels, stages and subjects.
- The user chose ROI mean spectra over full ROI pixel patches. Full frames are not feasible (~214 GB).
- Validation: 23 checks, 0 failed (`reports/validation_standalone.md`). 400 random ROI-frames were re-extracted via
  full-frame reads (max relative diff 5.9e-8). I also confirmed it reads with plain pandas from an isolated copy.
- Build time ~100 s, peak RSS 625 MB. `scripts/pmhm_build_dataset.py all` now includes the standalone build.

## Blocking issues
1. **Incomplete local download.** Subjects 03, 05, 07, 08 and 10 are partial Synapse stubs; 06 and 09 are absent.
   ROI tracks exist only for subject_01 (ROIs 1–4) and subject_02 (ROIs 1–3). The white reference, per-subject
   `metadata.json`, ROI videos, `color_checker/spectrometer.csv` and `code/src` (DataLoaderXIMEA) are missing.
   Only **2 subjects** can be used for ROI-level image analysis now, so participant-independent validation is not
   yet possible.
2. **Calibration.** No white reference, and the exposure of `dark.b2nd` is undocumented (subjects use 40 and 83 ms).

## Security finding
`spectralpaca.ipynb` contains a **plaintext Synapse personal access token** (download and **modify** scope) in
cell 1. Recommended: revoke it in Synapse settings, issue a new one, and load it from an environment variable or
`~/.synapseConfig`. Clearing the cell alone does not revoke it. The file is listed in `.gitignore`.

## Resource notes
8 GB RAM with typically only 0.5–1 GB free (5–6 GB of swap is used by other applications). Peak RSS: conversion
322 MB standalone, validation 695 MB, `all` in one process 812 MB. Disk: 207 GB free.
Cleanup at the user's request (2026-11-14): deleted superseded `_versions/` (4 old output dirs, 83 MB), Python and pytest caches, and 12 logs from
superseded runs. Kept the logs of the runs that produced the current outputs (`all` 23:02, `standalone` 23:27, `card` 23:29).
The raw dataset was kept on purpose (proposal §2/§6 require preserving the raw data).
