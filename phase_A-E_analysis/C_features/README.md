# Phase C · Features (S8–S9)

![status](https://img.shields.io/badge/status-complete-2EA44F?style=flat-square)

Work package 3, months 3–5 of the [implementation plan](../../docs/PMHM_Implementation_Plan.pdf). Code: [`../pmhm_phase_a_e.ipynb`](../pmhm_phase_a_e.ipynb).

| Step | What it does | Notebook section |
|:--|:--|:--:|
| **S8** Frame-level features | Computes five feature families for every camera frame and every simulated spectrometer spectrum | 20 |
| **S9** Block features and smallest detectable change | Plateau-minus-reference changes per block, initial slopes, and the smallest detectable change (SDC95) by moving-block bootstrap | 21 |

## Feature families

| Code | Family | Idea |
|:--|:--|:--|
| `raw` | Raw counts | ROI mean camera counts per band, the reference everything else is compared with |
| `rel` | Relative reflectance | Each band divided by its own baseline level |
| `l1` | L1-normalised spectrum | Spectral shape with overall brightness removed |
| `ratio` | Band ratios | Primary: **550/609 nm**, where haemoglobin absorbs strongly at 550 nm and weakly at 609 nm. Secondary: each band over 609 and 641 nm |
| `mbll` | Modified Beer–Lambert | Relative oxy- and deoxyhaemoglobin indices from a fit to attenuation, ΔA = −ln ρ |

Smoothing (a 2 s rolling median) is used only for figures. Every analysis uses unsmoothed values.

These families are what Phase D's robustness test (S12) and Phase E's H2 test compare. Of the five, L1-normalised spectra, band ratios and Beer–Lambert indices turned out to be robust; see [Phase D](../D_physiological_response/).
