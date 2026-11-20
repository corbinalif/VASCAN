# Phase A · Foundation (S0–S2)

![status](https://img.shields.io/badge/status-complete-2EA44F?style=flat-square)
![sign-off](https://img.shields.io/badge/analysis%20plan-awaiting%20sign--off-DBAB09?style=flat-square)

Work package 1, months 1–2 of the [implementation plan](../../docs/PMHM_Implementation_Plan.pdf). Code: [`../pmhm_phase_a_e.ipynb`](../pmhm_phase_a_e.ipynb).

| Step | What it does | Notebook section |
|:--|:--|:--:|
| **S0** Environment and run manifest | Detects Colab, Kaggle or local; fixes seeds; checks the dataset's SHA-256; writes a run manifest with a configuration hash | 12 |
| **S1** Data access and contract tests | Loads each record type; checks the 81 columns, their types and the row counts; golden tests reproduce the proposal's preliminary numbers | 13 |
| **S2** Analysis plan frozen | Writes the confirmatory analyses, decision rules for H1 and H2, validation schemes and the sensitivity grid before results are seen | 14 |

## First full run

- All **19 of 19** contract and golden tests passed.
- The golden tests caught one wrong number in proposal v1.0. The spectrometer rise at 160 mmHg across 500–650 nm is 16.3–30.1% (median 20.8%), not 18–22%. Proposal v2.0 corrects it.
- The plan is frozen, but `PLAN_SIGNED_OFF` is still `False`. Until it is signed off, every result in Phases B–E is provisional.
- The question of whether spectrometer ROI *k* is the same skin site as camera ROI *k* is recorded as open (`ROI_CORRESPONDENCE_CONFIRMED = False`). It affects the ROI-level agreement in S13.
