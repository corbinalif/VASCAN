# PMHM — Technical Decisions

Format: ID · decision · evidence · alternatives and implications.

**D-001 Keep the raw dataset in place; the workspace root is the dataset root.**
The 82 GB raw copy is not duplicated or moved. Processed outputs go to `data/processed/` and code to
`src/pmhm/`, `scripts/` and so on. The repository's suggested `data/raw/` is represented by the configured paths in
`configs/pmhm.yaml`, not by copies.

**D-002 Package name `pmhm` (src layout), not `src.*`.**
The original dataset loader is also called `src` (`code/src`, empty locally). A separate name avoids an import
clash if the original package is installed later.

**D-003 Sources: CSV is primary; feather is used only when no CSV exists; both copies are cross-validated.**
The CSV is the documented primary format. For subject_01, ROIs 2 and 4 exist only as feather. Where both copies
exist they are identical (ROIs), or equal within 1e-16 (`ximea_filters`: 1,414 float values differ in the last
digit from text rounding). `source_format` records which copy each row came from.

**D-004 Join-vs-separate (proposal §9), decided from the actual schemas.**
- ROI tracks ↔ cube frames: **joined.** The `(stage, time_delta)` match is exact and unique; 123,527 of 125,323 ROI
  rows match. The 1,796 unmatched rows lie after the cube end (~1100 s). They are kept, with `frame_index = null`.
- Spectrometer ↔ ROIs/frames: **kept separate.** The spectrometer has no timestamps, two stages only and a
  different spectral grid, so it relates at the `(subject_id, roi_id, stage)` level only. A row-level join would
  invent a synchronisation that does not exist.
- Optics, colour checker and dark reference live in wavelength or pixel domains, so they get separate tables.
  `ref_channels` links them via `channel_index`.

**D-005 Derived `spectrum_index` for spectrometer replicates.**
The raw file is wavelength-major with no spectrum ID, so the replicate number is the occurrence count within
`(subject, stage, ROI, wavelength)`. Validation: in all 80 groups the median adjacent-wavelength correlation across
replicates is ≥ 0.973 (0.14 when shuffled), and all 7,995 spectra have the full 550-point grid.

**D-006 Stage harmonisation and timeline derivation.**
`during_clamping_0mmHg` is labelled `phase = rest`. It occurs 8 times per session, so `stage_block_index` (0–16)
tells the rest periods apart, and `preceding_pressure_mmhg` gives the reperfusion context. Spectrometer stages map
`baseline (0 mmHg)` → `before_clamping` and `160 mmHg` → `during_clamping_160mmHg` (README). Original labels are
kept in `stage_original`.

**D-007 Self-describing Parquet.**
Each column carries `unit`, `origin` and `description` in its field metadata. Each file carries its table grain,
primary key, raw source paths with SHA-256 hashes, pipeline version and dataset citation. The data dictionary and
dataset card are generated from these files, so the documentation cannot drift from the data.

**D-008 Row-group layout.**
`master_spectrometer` has one row group per (subject, stage, ROI), 80 in total, so filtered reads skip groups via
statistics. `master_frames` has one row group per subject. The small tables use a single row group. Compression is
Snappy with dictionary encoding (4.4M rows → 35.6 MB, against 167 MB of CSV).

**D-009 Memory policy.**
CSV chunks start at 5,000 rows. They halve below 500 MB of available RAM, may double above 1.5 GB, and the run
aborts cleanly below 150 MB. Measured peak RSS: conversion 322 MB, validation 695 MB (validation compares whole
string columns of the 4.4M-row table; available RAM stayed above 600 MB).

**D-010 Independent validation.**
The validator uses different read paths from the converter: whole-file pandas reads, 40k-row chunks, the feather
copies, cube metadata re-read and recomputed derived columns. Every source-origin value is compared, with no
sampling.

**D-011 Calibration status: no reflectance normalisation yet.**
The white reference is missing locally, and `dark.b2nd` has no exposure metadata while subjects used 40 ms and
83 ms. `CubeReader.roi_mean_spectrum` therefore returns raw counts, with optional dark subtraction. Options: (a)
download the white reference; (b) use the colour-checker `ximea_norm` vs `ximea_raw` cubes to infer the
normalisation; (c) work with relative (ratio or first-difference) features that cancel illumination. This affects
the comparability of any absolute spectral feature.

**D-012 No git initialised yet.**
The proposal asks for version control, but committing is the user's decision. A `.gitignore` excluding raw and
processed data is prepared. The notebook holding a token must stay out of history; it is excluded in `.gitignore`.

**D-013 Standalone single-file dataset (user requirement).**
`data/processed/spectralpaca_pmhm_dataset.parquet` is one union-schema file. `record_type` selects the row kind
(roi_frame, frame, spectrometer, camera_filter, light_source, color_checker, channel, stage, subject). Columns that
a kind does not use are null, and each column description starts with the kinds it applies to. Each row group
holds a single record type, so filtering by `record_type` reads only the relevant groups.
Image content is reduced to per-channel ROI mean and std of raw counts (user choice, 2026-11-14). The alternatives
were full ROI pixel patches (~1–1.5 GB) or full frames (~214 GB, infeasible). Pixel patches can be added later as a
second file if spatial CNNs are needed.
