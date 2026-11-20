# Phase E · Agreement and models (S13–S16)

![S13](https://img.shields.io/badge/S13-complete-2EA44F?style=flat-square)
![S14](https://img.shields.io/badge/S14%20%C2%B7%20H2-not%20supported-D73A49?style=flat-square)
![S15](https://img.shields.io/badge/S15-partial-DBAB09?style=flat-square)
![S16](https://img.shields.io/badge/S16-not%20started-6E7781?style=flat-square)

Work packages 5–6, months 7–10 of the [implementation plan](../../docs/PMHM_Implementation_Plan.pdf). Code: [`../pmhm_phase_a_e.ipynb`](../pmhm_phase_a_e.ipynb).

| Step | What it does | Notebook section | Status |
|:--|:--|:--:|:--|
| **S13** Camera–spectrometer agreement | Bland–Altman (including repeated measures), ICC(2,1), spectral angle and repeatability | 25 | done |
| **S14** Occlusion-state models and H2 | Classical model ladder for phase classification and pressure regression, with null, time-only and drift controls | 26–28 | done |
| **S15** Temporal models (gated) | Sequence models compared with the best classical model under the same validation | 28 | TCN and GRU run; CNN-LSTM, transformer and the full 20-configuration sweep still to do |
| **S16** Recovery from shorter or noisier recordings | Degrades rest-block series to find the minimum frame rate and duration for reliable recovery estimates | – | not started |

## S13 · Do the camera and the spectrometer agree?

Poorly. At 160 mmHg, the camera change sat on average 29.2 percentage points below the spectrometer change (limits of agreement −46.8 to −11.6, ICC 0.21). At ROI level the bias was −23.5 points (limits −71.5 to 24.6, ICC 0.19), and that analysis assumes the ROIs correspond, which is still unconfirmed.

The spectrometer isn't a clean reference either. Replicate spectra at one site vary by a median 16%, across sites by 27%, and the across-site ICC at baseline is 0.25–0.34.

## S14 · Can the spectra tell the protocol phase?

| Model | Balanced accuracy |
|:--|:-:|
| Shuffled-label null | 0.31 |
| Chance | 0.33 |
| Best spectral model, across participants (Beer–Lambert indices, logistic regression) | 0.61 (0.54–0.67) |
| Best spectral model, within participant (ratios, random forest) | 0.72 (95% CI 0.65–0.78) |
| **Elapsed time only** | **0.93** |

The time-only model wins because the pressure order is fixed, so knowing the clock means knowing the phase. Any study with this design needs that control.

- Pressure regression across participants: RMSE 35.6 mmHg, against 45.9 mmHg for predicting the mean. The drift check didn't flag either direction.
- 10-person spectrometer task (leave-one-participant-out): SVM reached 0.70 with L1-normalised or ratio features and 0.59 with raw values.

**H2 is not supported.** Ratios beat raw counts on the camera in both directions (0.58 / 0.50 vs 0.41 / 0.40), but not in the 10-person spectrometer task (0.56 vs 0.59, p = 0.72).

## S15 · Temporal models so far

The TCN and GRU (each under 100,000 parameters, three seeds) were worse than the best classical model in every comparison, by 0.14–0.19 for phase classification, with intervals entirely below zero.
