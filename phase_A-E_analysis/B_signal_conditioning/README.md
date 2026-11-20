# Phase B · Signal conditioning (S3–S7)

![status](https://img.shields.io/badge/status-complete-2EA44F?style=flat-square)
![cross-talk](https://img.shields.io/badge/cross--talk%20correction-not%20adopted-D73A49?style=flat-square)

Work package 2, months 2–4 of the [implementation plan](../../docs/PMHM_Implementation_Plan.pdf). Code: [`../pmhm_phase_a_e.ipynb`](../pmhm_phase_a_e.ipynb).

The camera data come without a white reference, and the dark frame has no recorded exposure. This phase works out how far the raw counts can be trusted and calibrated anyway.

| Step | What it does | Notebook section |
|:--|:--|:--:|
| **S3** Quality control and frame flags | Flags post-video rows, ROI motion above 1 px and near-saturated patches; estimates per-band noise; checks stage-label agreement | 15 |
| **S4** Dark offset and its uncertainty | Runs three dark scenarios (0, D, 2D) and propagates them into the 550/609 nm ratio | 16 |
| **S5** Spectrometer-to-camera forward model | Projects every spectrometer spectrum through the 16 filter curves and the xenon source spectrum | 17 |
| **S6** Relative reflectance and effective white | Baseline-referenced reflectance; a per-band gain anchored on the spectrometer; baseline drift | 18 |
| **S7** Cross-talk characterisation and correction | Fits a 16 × 16 ridge correction, leave-one-participant-out, and tests it on neutral colour-checker patches | 19 |

## First full run

**Quality.** Stage labels agreed between ROI and frame records in 100% of frames. No ROI came near saturation (largest pixel value 419 counts). 988 ROI rows were flagged for displacement above 1 px. Median per-band signal-to-noise ran from 242 at 465 nm to 340 at 609 nm. Recording gaps of 35.4 s and 29.8 s come before the first clamping block in participants 01 and 02.

**Dark offset.** No clamp-stage change of the primary ratio changed sign across the three scenarios.

**Forward model.** At most 0.29% of any band's response falls outside the spectrometer's range. Of the 14,705 negative spectrometer values, 4,540 fall inside band support and are kept.

**Gain.** A gain fitted on one participant predicted the other's baseline counts within 15% in all 16 bands, in both directions (largest error about 13%, in the blue bands). That was good enough to include absolute comparisons.

**Cross-talk.** The correction cut the held-out spectral angle on skin from 8.8° to 0.03° in all ten folds. It also roughly doubled the non-flatness of every neutral patch. It had learned the narrow range of skin spectra and doesn't transfer outside it, so it was not adopted. It stays in the sensitivity grid for S17.
