# PMHM — instructions for AI agents working in this workspace

Project: **Peripheral Microvascular Health Monitoring (PMHM)** — "Non-Invasive Peripheral Microvascular Health
Monitoring Using Hyperspectral Imaging and Multimodal AI". Proposal: `projectproposal.md`.

## Session start (always)
1. Read `docs/PROJECT_STATUS.md` and `docs/NEXT_ACTIONS.md`; `docs/PROJECT_CONTEXT.md` for background.
2. `free -m` — the machine has 8 GB RAM and usually only ~0.5–1 GB free. Stream everything.
3. Continue from the highest-priority open item in `docs/NEXT_ACTIONS.md`; update the docs after each milestone.

## Environment
- Python: `~/.venv/bin/python` (Jupyter kernel `afrolalon`). System python has no packages.
- Pinned versions: `requirements-pmhm.txt`. Tests: `~/.venv/bin/python -m pytest -q tests`.
- GPU: GT 1030 (2 GB) — not suitable for training; CPU for all preprocessing.
- Not a git repository yet.

## Hard rules
- Raw data are immutable: `data/ximea/`, `data/spectrometer/`, `data/metadata.json`, `intermediates/`, `assets/`,
  `code/`, `README.md` (dataset README). Never write, move or delete there.
- Never touch `*.synapse_download_*` files (Synapse resume state of incomplete downloads).
- Never load a full cube (`subject_XX.b2nd`, ~26 GB); use `pmhm.data.catalog.CubeReader` (frame/ROI slicing).
- Regenerated outputs: the pipeline moves old output dirs to `data/processed/_versions/`. Only prune them when the
  user asks (the user approved pruning superseded versions, caches and old logs on 2026-11-14).
- `spectralpaca.ipynb` contains a plaintext Synapse token — never print, copy or commit it.
- Do not claim PAD diagnosis, StO2 or perfusion measurement from this dataset (10 healthy volunteers, 16 visible channels).

## Pipeline
```
~/.venv/bin/python scripts/pmhm_build_dataset.py all        # inventory -> pilot -> validate -> full -> validate -> standalone -> card
~/.venv/bin/python scripts/pmhm_build_dataset.py {inventory|convert|validate|standalone|card} [--pilot subject_01]
```
- Code: `src/pmhm/` (`data/schema.py` = single source of truth for every column; `convert.py`, `validate.py`,
  `catalog.py` loader, `card.py` docs generator, `inventory.py`). Config: `configs/pmhm.yaml`.
- **Standalone dataset file (what the user uses): `data/processed/spectralpaca_pmhm_dataset.parquet`.** It is a single
  file, independent of the raw download, with rows distinguished by `record_type`. Build/validate it with the
  `standalone` command; its guide is `docs/STANDALONE_DATASET.md`.
- Build tables: `data/processed/parquet/` (+ `_manifest/`), which the standalone file is built from. Docs generated from it: `docs/DATASET_CARD.md`,
  `docs/DATA_DICTIONARY.md`, `docs/DATASET_FILE_INVENTORY.md`, `reports/validation_*.md`.
- When adding a column: add it to `schema.py`, populate it in `convert.py`, add a check in `validate.py`, rerun `all`.
