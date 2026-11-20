# PMHM — Next Actions (priority order)

1. **[User] Complete the Synapse download.** Re-run the sync with a **new** token, after revoking the one in the
   notebook. Missing: cubes for subjects 03, 05–10 (~180 GB more, and 207 GB is free, so check space first); ROI
   tracks for subjects 03–10 and subject_02 ROI 4; `white` reference; per-subject `metadata.json`; ROI videos;
   `code/src`; `color_checker/spectrometer.csv`. Then run `scripts/pmhm_build_dataset.py all`. The pipeline picks
   up new files automatically and rebuilds the standalone file.
2. **Calibration investigation (Phase 2).** Use `color_checker/ximea_raw` vs `ximea_norm` (same 240 frames) to test
   whether the normalisation (white/dark model) can be recovered. Characterise per-channel SNR from dark-reference
   statistics and from ROI patches. Determine the exposure dependence of dark (40 vs 83 ms).
3. ~~ROI spectral-temporal feature table~~: done in session 2 as `roi_frame` rows of the standalone file.
   Optional: a second file with full 20×20×16 ROI pixel patches (~1–1.5 GB) if spatial CNNs are planned.
4. **EDA (proposal §4).** Notebook `notebooks/01_eda.ipynb` on kernel `afrolalon`: stage-wise channel responses,
   reperfusion dynamics per rest block, ROI motion, spectrometer baseline-vs-160 mmHg differences, and inter-subject
   variability. Use only descriptive statistics; no oxygenation claims before calibration.
5. **Spectrometer ↔ camera band adaptation.** Integrate spectrometer spectra with `optics_ximea_filters` ×
   `optics_xenon_light_source` to simulate camera-band reflectance (cf. `color_checker_spectrometer_adapted`).
   This gives a reference for camera features at the (subject, ROI, stage) level.
6. Initialise git (with the prepared `.gitignore`) once the user agrees. Verify the literature citations A–F.
