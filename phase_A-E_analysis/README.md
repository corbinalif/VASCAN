# Phases A–E · Analysis

![steps](https://img.shields.io/badge/steps-S0%E2%80%93S14%20complete-2EA44F?style=flat-square)
![S15](https://img.shields.io/badge/S15-partial-DBAB09?style=flat-square)
![S16](https://img.shields.io/badge/S16-not%20started-6E7781?style=flat-square)

All five analysis phases run from one notebook, [`pmhm_phase_a_e.ipynb`](pmhm_phase_a_e.ipynb). It is built as two cells: a description, and a single pipeline cell that runs the steps in dependency order through a checkpointed step engine. I kept it as one file so it runs unchanged on Colab, Kaggle or a laptop.

Each phase folder below explains its steps, points to the notebook section that implements them, and summarises the first full run.

| Phase | Steps | Folder | Notebook sections |
|:--|:--|:--|:--|
| **A** Foundation | S0–S2 | [`A_foundation/`](A_foundation/) | 12–14 |
| **B** Signal conditioning | S3–S7 | [`B_signal_conditioning/`](B_signal_conditioning/) | 15–19 |
| **C** Features | S8–S9 | [`C_features/`](C_features/) | 20–21 |
| **D** Physiological response | S10–S12 | [`D_physiological_response/`](D_physiological_response/) | 22–24 |
| **E** Agreement and models | S13–S16 | [`E_agreement_and_models/`](E_agreement_and_models/) | 25–28 |

Sections 0–11 are shared infrastructure: configuration, imports, environment, logging, dataset validation, the step engine, data access, statistics, optics, feature engineering, block windows and plotting. Sections 29–30 are reporting and the main run.

## Running

```bash
cd phase_A-E_analysis
jupyter lab pmhm_phase_a_e.ipynb
```

For a local run, the notebook looks for `../data/spectralpaca_pmhm_dataset.parquet`. If it's not there, it searches the repository. On Colab, put the file in `MyDrive/PMHM/`. On Kaggle, attach it as a dataset. Edit only the first block of the pipeline cell; `QUICK_TEST = True` gives a fast smoke test. Results go to `pmhm_outputs/` next to the notebook.
