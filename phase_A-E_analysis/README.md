# Phases A–E · Analysis

![steps](https://img.shields.io/badge/steps-S0%E2%80%93S14%20complete-2EA44F?style=flat-square)
![S15](https://img.shields.io/badge/S15-implemented-2EA44F?style=flat-square)
![S16](https://img.shields.io/badge/S16-implemented-2EA44F?style=flat-square)

All five analysis phases run from one notebook, [`pmhm_phase_a_e.ipynb`](pmhm_phase_a_e.ipynb). It is built as **three cells**: a description cell, a pipeline cell that runs S0–S14, and a **new extension cell (Section 31)** that adds S15 and S16. The step engine, checkpointing and resume logic are shared across all cells.

| Phase | Steps | Notebook cell / section |
|:--|:--|:--|
| **A** Foundation | S0–S2 | Cell 2 · sections 12–14 |
| **B** Signal conditioning | S3–S7 | Cell 2 · sections 15–19 |
| **C** Features | S8–S9 | Cell 2 · sections 20–21 |
| **D** Physiological response | S10–S12 | Cell 2 · sections 22–24 |
| **E** Agreement and models | S13–S14 | Cell 2 · sections 25–28 |
| **E** Full temporal sweep | S15 | Cell 3 · section 31 |
| **E** Recording degradation | S16 | Cell 3 · section 31 |

Sections 0–11 (cell 2) are shared infrastructure: configuration, imports, environment, logging, dataset validation, step engine, data access, statistics, optics, feature engineering, block windows and plotting. Sections 29–30 are reporting and the main S0–S14 run. Section 31 (cell 3) adds S15/S16 and re-runs the report.

## Results

The full run of 20 November 2026 (Kaggle, CPU, 32 minutes) is written up in **[PMHM_Phase_A-E_Results.pdf](PMHM_Phase_A-E_Results.pdf)**: every step's results with all tables and figures. The raw outputs are in [`pmhm_outputs/full/`](pmhm_outputs/full/) (report, figures, tables, models, predictions, logs; the resume caches are not committed). To rebuild the PDF from a run:

```bash
python build_results_pdf.py pmhm_outputs/full PMHM_Phase_A-E_Results.pdf
```

## Running

```bash
cd phase_A-E_analysis
jupyter lab pmhm_phase_a_e.ipynb
```

For a local run, the notebook looks for `../data/spectralpaca_pmhm_dataset.parquet`. If it's not there, it searches the repository. On Colab, put the file in `MyDrive/PMHM/`. On Kaggle, attach it as a dataset. Edit only the first block of **cell 2**; `QUICK_TEST = True` gives a fast smoke test. Results go to `pmhm_outputs/` next to the notebook.

**S15 / S16 (cell 3).** Run cell 2 first (or let RESUME reload S0–S14 from checkpoints), then run cell 3. S15 needs PyTorch and benefits greatly from a GPU — set `DEVICE = "cuda"` in cell 2. The 20-config × 4-backbone sweep is gated by a pilot-cost check that warns if the remaining wall-time exceeds `S15_PILOT_CPU_BUDGET_S` (default 2 h). S16 runs entirely on CPU and takes a few minutes.
