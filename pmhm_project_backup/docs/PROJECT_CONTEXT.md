# PMHM — Project Context

_Central knowledge document. Last updated 2026-11-14._

## 1. Identity and goal
- **Project:** Peripheral Microvascular Health Monitoring (PMHM).
- **Title:** Non-Invasive Peripheral Microvascular Health Monitoring Using Hyperspectral Imaging and Multimodal AI.
- **Goal:** build a scientifically defensible, reproducible framework for analysing peripheral tissue oxygenation,
  haemoglobin-related spectral features and microvascular responses from spectral video, with temporal AI. The
  outcomes are a publication and a working prototype.
- **Current proposal scope** (`projectproposal.md`): a resource-efficient data-engineering and EDA pipeline for
  SPECTRALPACA, to serve as the foundation for later modelling.

## 2. Dataset: SPECTRALPACA (verified against the local files)
Ayala et al., *Scientific Data* 2024, doi:10.1038/s41597-024-03307-y, Synapse syn51625685, CC BY 4.0.

| Property | Verified value |
|---|---|
| Participants | 10 healthy volunteers, right-hand palm |
| Camera | XIMEA MQ022HG-IM-SM4x4-VIS snapshot mosaic, 16 channels, 465–641 nm (visible only), 272×512 px |
| Cube format | blosc2 NDArray `.b2nd` (README says `.dat`/`.npy`; the local files are `.b2nd`), float16, (frames, 272, 512, 16), one frame per chunk |
| Per-frame metadata inside the cube | `stage`, `time_delta` (s), `exposure` (ms) |
| Frame rate / exposure | 25 Hz @ 40 ms (subjects 01, 02); 12 Hz @ 83 ms (subject 04) |
| Session | ~1100 s; baseline → 20…160 mmHg in 20 mmHg steps, each followed by a no-pressure rest (`during_clamping_0mmHg`); 17 blocks |
| ROIs | 4 palm ROIs per subject, 20×20 px boxes, tracked per frame (`y1,x1,y2,x2,stage,time_delta`; the README's `file` column does not exist) |
| Spectrometer | HR2000+, 550 wavelengths 425.4–674.8 nm, ~100 replicate spectra per subject×ROI×stage, baseline and 160 mmHg only, no timestamps |
| References | dark (`dark.b2nd`, 272×512×16 float64, exposure not stored). White reference: not present locally |
| Optics | 16 filter response curves (400–1000 nm, integer-rounded wavelengths); xenon source relative irradiance |
| Colour checker | 24-patch cubes (raw and normalised, 240 frames each) plus band-adapted reference spectra |

**Local copy is incomplete.** See `docs/DATASET_FILE_INVENTORY.md`. Complete cubes exist only for subjects 01, 02
and 04, and ROI tracks only for subject 01 (ROIs 1–4) and subject 02 (ROIs 1–3).

## 3. Scientific framing (keep distinct)
- **StO2** (tissue O2 saturation, mixed arterial/capillary/venous) ≠ **SpO2** (arterial, pulse oximetry).
- HbO2 and Hb chromophores → total haemoglobin (≈ blood volume) ≠ **perfusion** (flow) ≠ **oxygen delivery** (flow × content).
- HSI measures diffuse reflectance. Oxygenation is inferred through a model (Beer–Lambert / Monte-Carlo / ML).
  Perfusion is **not** measured directly.
- Confounders: melanin, temperature, illumination geometry and stability, motion, posture, hydration,
  acclimatisation, SNR, and filter cross-talk. The mosaic filters have secondary lobes up to 0.81 of the peak; see `ref_channels`.
- Healthy-volunteer cuff occlusion is a physiological perturbation model. It is **not** a PAD cohort, so no
  diagnostic claims can be made.
- Reference measurements available: spectrometer reflectance only (no StO2 or laser-Doppler ground truth).

## 4. Literature foundation (citations still to be verified before academic use)
A. Real-time perfusion assessment with HSI after revascularisation in PAD (2026) ·
B. HSI + thermal imaging after endovascular treatment for PAD (2023) ·
C. Microcirculatory changes after PAD revascularisation with Hyperview (2023) ·
D. Cutaneous O2 saturation with a snapshot hyperspectral camera: feasibility (2021) ·
E. Vascular occlusion test using multispectral imaging: validation (2021) ·
F. Multimodal device for skin O2 saturation and microcirculation (2019) ·
G. SPECTRALPACA (2024), with DOI verified from the dataset README.

## 5. Architecture
```
SPECTRALPACA/                 (= PMHM workspace; raw dataset kept in place, never copied)
  data/ximea, data/spectrometer, data/metadata.json, intermediates/   RAW (read-only)
  data/processed/parquet/     PRIMARY analytical dataset (10 tables + _manifest/)
  data/processed/pilot_subject_01/   pilot output;  data/processed/_versions/  preserved older outputs
  data/processed/manifests/   raw file inventory (parquet/json)
  configs/pmhm.yaml  src/pmhm/  scripts/  tests/  docs/  reports/  logs/
```
Phases: 1 audit ✔ → 2 integrity/calibration (in progress) → 3 spectral preprocessing → 4 ROI/temporal features →
5 physiological response analysis → 6 classical ML → 7 temporal DL → 8 multimodal fusion → 9 participant-independent
validation → 10 reporting.
