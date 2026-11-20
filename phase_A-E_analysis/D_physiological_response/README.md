# Phase D · Physiological response (S10–S12)

![H1](https://img.shields.io/badge/H1-not%20supported-D73A49?style=flat-square)
![RQ2](https://img.shields.io/badge/RQ2-descriptive-6F42C1?style=flat-square)
![RQ3](https://img.shields.io/badge/RQ3-3%20robust%20families-2EA44F?style=flat-square)

Work package 4, months 5–7 of the [implementation plan](../../docs/PMHM_Implementation_Plan.pdf). Code: [`../pmhm_phase_a_e.ipynb`](../pmhm_phase_a_e.ipynb).

| Step | What it does | Notebook section |
|:--|:--|:--:|
| **S10** Dose–response and H1 | Exact permutation trend test per camera participant, a placebo test on rest-to-rest drift, and an independent 10-person spectrometer arm | 22 |
| **S11** Recovery kinetics (RQ2) | Exponential fits to each post-release recovery, with model-free fallbacks | 23 |
| **S12** Feature robustness (RQ3) | Scores each feature family on between-person variation, drift, effect-to-noise and dark sensitivity | 24 |

## S10 · Does the 550/609 nm ratio fall with pressure?

No, not steadily. In both camera participants the change grew from 20 mmHg to about 100 mmHg, peaked at 100 mmHg (participant 01, −0.022) and 120 mmHg (participant 02, −0.032), then returned to near zero at 140–160 mmHg.

- Monotone trend tests: p = 0.87 and 0.67. No onset pressure met the SDC95 criterion, and the clamp trend didn't beat the placebo trend.
- Spectrometer arm, 10 participants at 160 mmHg: change in log(S550/S609) −0.003 (95% CI −0.028 to 0.027), Wilcoxon p = 0.25. Four rose and six fell.

**H1 is not supported.** The non-monotone shape is an exploratory observation. It was spotted in the same two people it would be tested on, so it needs independent data.

## S11 · Recovery

Only 43% of exponential fits met the acceptance rule, so the pre-specified model-free measures were used instead. Recovery was still incomplete 20 s after release in 5 of 5 blocks for participant 01 and 5 of 6 for participant 02. Neither half-recovery time nor overshoot depended on the preceding pressure (Holm-adjusted p ≥ 0.25).

## S12 · Which features are robust?

| Family | Between-person CV | Baseline drift | Effect / noise at 160 mmHg | Dark sensitivity | Robust |
|:--|:-:|:-:|:-:|:-:|:-:|
| Raw counts | 0.236 | 1.90 | 2.79 | n/a | reference |
| Relative reflectance | n/a | 1.90 | 2.76 | 0.09 | no |
| L1-normalised | 0.028 | 0.77 | 3.40 | 0.17 | **yes** |
| Band ratios | 0.040 | 0.77 | 3.14 | 0.16 | **yes** |
| Beer–Lambert indices | n/a | 0.94 | 4.99 | 0.11 | **yes** |

<sub>Family medians. Drift is the absolute baseline slope per 100 s relative to baseline SD.</sub>
