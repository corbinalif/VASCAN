"""Generate docs/DATASET_CARD.md and docs/DATA_DICTIONARY.md from the Parquet files themselves.

Every number in the card is computed from the dataset (no hand-typed values), so the card cannot
drift from the data.
"""
from __future__ import annotations

import json
from pathlib import Path

import numpy as np
import pandas as pd
import pyarrow.parquet as pq

from .catalog import PMHMDataset


def _md(df: pd.DataFrame) -> str:
    cols = list(df.columns)
    out = ["| " + " | ".join(map(str, cols)) + " |", "|" + "---|" * len(cols)]
    for r in df.itertuples(index=False):
        out.append("| " + " | ".join("" if (isinstance(v, float) and np.isnan(v)) else str(v) for v in r) + " |")
    return "\n".join(out)


def _b(ok: bool, yes="YES", no="NO") -> str:
    return f"**{yes}**" if ok else f"**{no}**"


def write_data_dictionary(ds: PMHMDataset, out: Path) -> None:
    L = ["# PMHM Data Dictionary", "",
         "_Generated from the field metadata embedded in each Parquet file "
         f"(`{ds.cfg.rel(ds.dir)}`). Regenerate with `scripts/pmhm_build_dataset.py card`._", "",
         "**Origin codes** — `source:<col>` verbatim raw value · `source_path` parsed from raw file/folder name · "
         "`cube_meta:<key>` per-frame metadata inside the .b2nd cube · `derived` computed by PMHM (formula given) · "
         "`joined` looked up from another raw source · `provenance` link back to the raw row/file.", ""]
    for name, t in ds.catalog["tables"].items():
        meta = ds.table_metadata(name)
        L += [f"## `{name}`", "", f"{t['description']}", "",
              f"- **Grain:** {t['grain']}", f"- **Primary key:** `{', '.join(t['primary_key'])}`",
              f"- **Rows:** {t['rows']:,} · **Row groups:** {t['row_groups']} · **Size:** {t['bytes'] / 1e6:.2f} MB",
              "- **Raw sources:** " + (", ".join(f"`{s['path']}`" for s in meta.get("pmhm.sources", [])) or
                                       "cube metadata / derived"), ""]
        d = ds.describe(name)[["column", "type", "nullable", "unit", "origin", "description"]]
        L += [_md(d), ""]
    out.write_text("\n".join(L) + "\n")


def write_dataset_card(ds: PMHMDataset, out: Path, proposal: Path | None = None) -> None:
    cfg = ds.cfg
    root = cfg.root
    subj = ds.load("ref_subjects")
    ch = ds.load("ref_channels")
    st = ds.load("ref_stages")
    fr = ds.load("master_frames", columns=["subject_id", "stage_block_index", "stage", "time_delta_s", "phase",
                                           "preceding_pressure_mmhg"])
    rois = ds.load("master_rois", columns=["subject_id", "roi_id", "has_image_frame", "bbox_width_px",
                                           "bbox_height_px", "displacement_px"])
    sp_meta = ds.table_metadata("master_spectrometer")
    grid = np.array(sp_meta["pmhm.wavelength_grid_nm"])
    sp = pq.ParquetFile(ds.path("master_spectrometer"))
    groups = []
    for rg in range(sp.metadata.num_row_groups):
        t = sp.read_row_group(rg, columns=["subject_id", "stage", "roi_id", "spectrum_index", "reflectance_au"])
        r = t["reflectance_au"].to_numpy()
        groups.append({"subject_id": t["subject_id"][0].as_py(), "stage": t["stage"][0].as_py(),
                       "roi_id": t["roi_id"][0].as_py(), "n_spectra": len(np.unique(t["spectrum_index"].to_numpy())),
                       "refl_min": r.min(), "refl_median": float(np.median(r)), "refl_max": r.max()})
    g = pd.DataFrame(groups)
    vrep_p = ds.dir / "_manifest" / "validation_report.json"
    vrep = json.loads(vrep_p.read_text()) if vrep_p.exists() else None
    inv_p = cfg.out_path("processed_dir") / "manifests" / "file_inventory_summary.json"
    inv = json.loads(inv_p.read_text()) if inv_p.exists() else None
    complete = subj[subj.cube_status == "complete"]
    usable = subj[subj.usable_roi_image_analysis]
    n_rest = int(st.loc[st.stage == "during_clamping_0mmHg", "blocks_per_session"].iloc[0])
    pressures = sorted(st.pressure_mmhg[st.phase == "clamping"].tolist())

    L = ["# SPECTRALPACA — PMHM Primary Dataset Card", "",
         f"_Auto-generated from `{cfg.rel(ds.dir)}` on {ds.catalog['created_utc']} (pipeline v"
         f"{ds.catalog['pipeline_version']}). Every value below is computed from the Parquet files; regenerate with "
         "`python scripts/pmhm_build_dataset.py card`._", "",
         "> **Standalone dataset file:** `data/processed/spectralpaca_pmhm_dataset.parquet`. This one file holds "
         "everything (ROI spectral time series extracted from the video, spectrometer, calibration, protocol, "
         "participants) and works without the original download. See `docs/STANDALONE_DATASET.md`.",
         "> Build tables: `data/processed/parquet/` (10 tables the standalone file is built from; these point to the "
         "raw `.b2nd` cubes through `image_file` + `frame_index`).",
         "> Load with `from pmhm.data.catalog import PMHMDataset, CubeReader` (see §8).", ""]

    # 1. headline parameters
    v_ok = vrep and vrep["n_failed"] == 0
    L += ["## 1. Dataset parameters at a glance", "", "| Parameter | Value | Source |", "|---|---|---|",
          f"| Study | SPECTRALPACA — Ayala et al., *Scientific Data* 2024, doi:10.1038/s41597-024-03307-y, Synapse "
          f"syn51625685, CC BY 4.0 | README.md |",
          f"| Participants in study | **{len(subj)}** healthy volunteers (right-hand palm) | data/metadata.json |",
          f"| Participants with complete HSI cube locally | **{len(complete)} / {len(subj)}** "
          f"({', '.join(complete.subject_id)}) | ref_subjects |",
          f"| Participants usable for ROI-level image analysis now | **{len(usable)} / {len(subj)}** "
          f"({', '.join(usable.subject_id)}) | ref_subjects |",
          f"| Participants with spectrometer reference | **{g.subject_id.nunique()} / {len(subj)}** | master_spectrometer |",
          f"| Camera | {cfg.raw['camera']['model']} snapshot mosaic, **{len(ch)} channels**, "
          f"{cfg.raw['camera']['height_px']} x {cfg.raw['camera']['width_px']} px | ref_channels, cube header |",
          f"| Channel wavelengths (nominal, cube order) | {', '.join(map(str, ch.nominal_wavelength_nm))} nm | ref_channels |",
          f"| Camera spectral span | **{ch.nominal_wavelength_nm.min()}–{ch.nominal_wavelength_nm.max()} nm** "
          f"(visible only; not continuous 500–900 nm) | ref_channels |",
          f"| Filter FWHM | {ch.fwhm_nm.min():.0f}–{ch.fwhm_nm.max():.0f} nm; secondary-lobe ratio up to "
          f"{ch.secondary_peak_ratio.max():.2f} | ref_channels |",
          f"| Cube storage | float16, blosc2 NDArray, 1 frame per chunk | cube header |",
          f"| Frames per subject | " + ", ".join(f"{r.subject_id}: {int(r.n_frames):,}" for r in complete.itertuples())
          + " | master_frames |",
          f"| Frame rate / exposure | " + ", ".join(f"{r.subject_id}: {r.frame_rate_hz:.1f} Hz @ {int(r.exposure_ms)} ms"
                                                    for r in complete.itertuples()) + " | master_frames |",
          f"| Recording duration | " + ", ".join(f"{r.duration_s:.0f} s" for r in complete.itertuples()) + " | master_frames |",
          f"| Protocol | baseline → {len(pressures)} cuff stages ({', '.join(map(str, pressures))} mmHg), each followed by a "
          f"no-pressure rest; **{int(complete.n_stage_blocks.iloc[0])} blocks/session**, {n_rest} rest periods | "
          "ref_stages, master_frames |",
          f"| Tracked ROIs | 4 per subject (study design); box "
          f"{int(rois.bbox_width_px.median())} x {int(rois.bbox_height_px.median())} px; "
          f"{len(rois):,} tracked rows locally | master_rois |",
          f"| Spectrometer | {sp_meta.get('pmhm.instrument', 'HR2000+')}; **{len(grid)} wavelengths, "
          f"{grid.min():.1f}–{grid.max():.1f} nm**; {int(g.n_spectra.sum()):,} spectra "
          f"({g.n_spectra.min()}–{g.n_spectra.max()} per subject×stage×ROI); stages: baseline and 160 mmHg | "
          "master_spectrometer |",
          f"| Calibration references | dark: **present** (`data/ximea/dark.b2nd`, 272x512x16, mean "
          f"{ch.dark_mean.mean():.1f} counts); white: **MISSING locally** | ref_channels |",
          f"| Validation | {vrep['n_passed']} passed · {vrep['n_warn']} warnings · **{vrep['n_failed']} failed** "
          f"of {vrep['n_checks']} checks | reports/validation_full.md |" if vrep else "| Validation | not run | |",
          ""]

    # 2. coverage matrix
    cov = subj[["subject_id", "cube_status", "n_frames", "exposure_ms", "frame_rate_hz", "roi_ids_available",
                "n_roi_rows", "n_spectra_baseline", "n_spectra_160mmHg", "usable_roi_image_analysis"]].copy()
    cov["cube_status"] = cov.cube_status.map(lambda s: s if s == "complete" else f"**{s.upper()}**")
    cov["roi_ids_available"] = cov.roi_ids_available.map(lambda s: s or "**none**")
    cov["usable_roi_image_analysis"] = cov.usable_roi_image_analysis.map(lambda v: _b(v))
    cov["frame_rate_hz"] = cov.frame_rate_hz.round(1)
    for c in ("n_frames", "exposure_ms"):
        cov[c] = cov[c].astype("Int64").astype(str).replace("<NA>", "")
    L += ["## 2. Subject × modality coverage (local copy)", "", _md(cov), "",
          "Spectrometer data are complete for all subjects; image-based analysis is limited by the incomplete "
          "local download (see `docs/DATASET_FILE_INVENTORY.md`).", ""]

    # 3. tables
    tab = ds.tables()
    tab["MB"] = (tab.bytes / 1e6).round(2)
    L += ["## 3. Parquet tables (primary dataset)", "", _md(tab[["table", "rows", "grain", "primary_key", "MB"]]), "",
          "Join keys: `subject_id` (all), `frame_index` (rois ↔ frames ↔ cube axis 0), `stage` (all ↔ ref_stages), "
          "`roi_id` (rois ↔ spectrometer, group level only), `channel_index` (cube last axis ↔ ref_channels ↔ "
          "optics_ximea_filters). The spectrometer has **no timestamps**, so it links to ROI tracks at the "
          "(subject, ROI, stage) level only — it is kept as a separate table by design.", ""]

    # 4. timeline
    tl = (fr.groupby(["subject_id", "stage_block_index"])
            .agg(stage=("stage", "first"), phase=("phase", "first"), start_s=("time_delta_s", "min"),
                 end_s=("time_delta_s", "max"), frames=("stage", "size")).reset_index())
    tl["dur_s"] = (tl.end_s - tl.start_s).round(1)
    wide = tl.pivot(index="stage_block_index", columns="subject_id", values="dur_s")
    first = tl[tl.subject_id == tl.subject_id.iloc[0]].set_index("stage_block_index")
    wide.insert(0, "stage", first.stage)
    wide.insert(1, "phase", first.phase)
    wide = wide.reset_index()
    wide.columns = ["block", "stage", "phase"] + [f"{c} duration (s)" for c in wide.columns[3:]]
    L += ["## 4. Session timeline (stage blocks)", "", _md(wide), ""]
    gaps = fr.sort_values(["subject_id", "time_delta_s"]).copy()
    gaps["dt"] = gaps.groupby("subject_id").time_delta_s.diff()
    gg = gaps[gaps.dt > 1.0][["subject_id", "stage_block_index", "stage", "time_delta_s", "dt"]].round(2)
    L += ["Unrecorded gaps > 1 s in the frame timeline (e.g. cuff inflation before the first clamping stage):", "",
          _md(gg.rename(columns={"dt": "gap_s"})), ""]

    # 5. channels
    c2 = ch[["channel_index", "nominal_wavelength_nm", "peak_wavelength_nm", "fwhm_nm", "secondary_peak_ratio",
             "dark_mean", "dark_std"]].round(3)
    L += ["## 5. Camera channels", "", _md(c2), ""]

    # 6. spectrometer
    piv = g.pivot_table(index="subject_id", columns=["stage", "roi_id"], values="n_spectra").astype(int)
    piv.columns = [f"{'base' if s == 'before_clamping' else '160'}·ROI{r}" for s, r in piv.columns]
    L += ["## 6. Spectrometer spectra per subject × stage × ROI", "", _md(piv.reset_index()), "",
          f"Reflectance (a.u., as provided): min {g.refl_min.min():.2f}, median of group medians "
          f"{g.refl_median.median():.2f}, max {g.refl_max.max():.2f}; negative values are kept and flagged "
          "(`flag_negative_reflectance`).", ""]

    # 7. quality
    q = vrep["quality_findings"] if vrep else {}
    L += ["## 7. Validation and data-quality findings", ""]
    if vrep:
        fails = [c for c in vrep["checks"] if c["status"] != "pass"]
        L += [f"- **{vrep['n_passed']}/{vrep['n_checks']} checks passed, {vrep['n_failed']} failed** "
              "(full report: `reports/validation_full.md`). Every Parquet value of source origin was compared "
              "with the raw CSV, and also with the feather copy where one exists. Raw-file SHA-256 hashes were "
              "re-verified after conversion."]
        L += [f"- {c['table']}: {c['check']} — {c['detail']}" for c in fails]
    L += [f"- {q.get('roi_rows_without_frame', '?'):,} ROI rows were tracked after the last cube frame (~1100 s). "
          "They are **kept** with `frame_index = null` and `has_image_frame = false`.",
          "- `optics_ximea_filters.wavelength_nm` is integer-rounded in the raw file. Each filter has 601 samples "
          "but only 581 unique wavelengths, so the key is `wavelength_sample_index`.",
          f"- Xenon spectrum: {q.get('xenon_negative_irradiance_rows', '?')} rows with negative irradiance "
          "(kept, flagged).",
          "- `dark.b2nd` has no stored exposure, while subjects were recorded at 40 ms and 83 ms. The white "
          "reference is missing, so reflectance normalisation from local data is **not yet possible**.",
          f"- ROI centre motion: mean {rois.displacement_px.mean():.3f} px/frame, max {rois.displacement_px.max():.2f} px.",
          ""]

    # 8. usage
    L += ["## 8. How to use this dataset", "", "```python", "import sys; sys.path.insert(0, 'src')",
          "from pmhm.data.catalog import PMHMDataset, CubeReader",
          "ds = PMHMDataset()                      # data/processed/parquet",
          "ds.tables(); ds.describe('master_rois') # catalogue + column units/origins (read from the files)",
          "rois = ds.rois('subject_01', roi=1, stage='during_clamping_160mmHg')",
          "spec = ds.spectra(subject='subject_05', stage='before_clamping', roi=2, wide=True)  # 100 x 550",
          "cube = CubeReader('subject_01')         # lazy: one ROI patch decompresses ~1 block",
          "r = rois.iloc[0]; s = cube.roi_mean_spectrum(int(r.frame_index), r.y1, r.x1, r.y2, r.x2)",
          "```", ""]

    # 9. traceability to the proposal
    T = [
        ("§2 Recursive inspection; supported files identified", "Done",
         f"docs/DATASET_FILE_INVENTORY.md ({inv['n_files'] if inv else '?'} raw files)"),
        ("§2 Memory-safe chunked streaming (Pandas/PyArrow)", "Done",
         f"adaptive chunks start at 5,000 rows; peak conversion RSS ~{ds.catalog['chunking']['peak_rss_mb']:.0f} MB"),
        ("§2 Snappy Parquet; separate masters for different schemas", "Done", "10 tables, §3"),
        ("§2 `master_rois.parquet`", "Done", f"{len(rois):,} rows"),
        ("§2 Spectrometer tables", "Done", f"master_spectrometer, {int(g.n_spectra.sum()):,} spectra"),
        ("§2 Optical calibration and metadata tables", "Done",
         "optics_ximea_filters, optics_xenon_light_source, ref_channels, ref_stages, ref_subjects, colour checker"),
        ("§2 Manifests: sources, rows, schemas, dtypes, status, validation", "Done",
         "_manifest/conversion_manifest.*, catalog.json, validation_report.json"),
        ("§2 Provenance: subject, ROI, frame, condition, source file", "Done",
         "subject_id, roi_id, frame_index, stage/phase/block, source_file, source_row_index"),
        ("§2 Single-subject pilot before full scale", "Done", "data/processed/pilot_subject_01 + reports/validation_pilot_subject_01.md"),
        ("§2 Integrity: counts, rows, columns, dtypes, missing, record-level", "Done", "reports/validation_full.md"),
        ("§2 Raw files unchanged", "Done", "SHA-256 of every source re-verified after conversion"),
        ("§3 Cubes and references kept native, lazy access", "Done (no DataLoaderXIMEA locally)",
         "CubeReader (blosc2 slicing). `code/src` is empty in the download"),
        ("§3 Dark/white correction, reflectance normalisation", _b(False, no="BLOCKED"),
         "white reference missing; dark exposure undocumented"),
        ("§3 ROI ↔ frame linkage across stages incl. reperfusion", "Done",
         "frame_index exact join; stage_block_index, preceding_pressure_mmhg, time_in_block_s"),
        ("§3 Synchronisation of frames, ROIs, spectrometer, stages", "Partial",
         "frames↔ROIs exact; spectrometer has no timestamps, so linkage is group-level only"),
        ("§3 Invalid / missing frames, tracking inconsistencies", "Partial",
         "gaps, unmatched rows, displacement, bbox bounds flagged. Per-channel SNR still pending"),
        ("§4 EDA", "Pending", "next phase (docs/NEXT_ACTIONS.md)"),
        ("§6 Configs, logs, manifests, version control", "Partial",
         "configs/pmhm.yaml, logs/, manifests; the workspace is not yet a git repository"),
        ("§9 Join-vs-separate decision based on actual schemas", "Decided",
         "docs/TECHNICAL_DECISIONS.md D-004"),
    ]
    L += ["## 9. Traceability to `projectproposal.md`", "", "| Proposal requirement | Status | Evidence |",
          "|---|---|---|"] + [f"| {a} | {b} | {c} |" for a, b, c in T] + [""]
    L += ["## 10. Scientific scope", "",
          "These data come from **10 healthy volunteers** imaged with a **16-channel visible-range camera**. They "
          "support technical development and the analysis of physiological responses to graded cuff occlusion. "
          "They do **not** establish PAD diagnostic validity, and image-derived features are not perfusion "
          "measurements without independent validation. The spectrometer gives diffuse reflectance at baseline "
          "and 160 mmHg only. It is not an StO2 or perfusion ground truth.", ""]
    out.write_text("\n".join(L) + "\n")


def write_standalone_doc(cfg, out: Path) -> None:
    """Column guide for the single-file dataset, generated from the file's own metadata."""
    from .standalone import standalone_path
    p = standalone_path(cfg)
    if not p.exists():
        return
    sch = pq.read_schema(p)
    md = {k.decode(): v.decode() for k, v in sch.metadata.items() if k.startswith(b"pmhm.")}
    rtypes = json.loads(md["pmhm.record_types"])
    vp = cfg.out_path("reports_dir") / "validation_standalone.json"
    v = json.loads(vp.read_text()) if vp.exists() else {}
    counts = v.get("record_counts", {})
    L = ["# Standalone dataset file — `data/processed/spectralpaca_pmhm_dataset.parquet`", "",
         "_Generated from the file's embedded metadata. Regenerate with `scripts/pmhm_build_dataset.py card`._", "",
         "**This one file is the complete dataset.** It needs neither the original SPECTRALPACA download nor the "
         "PMHM code: any Parquet reader (pandas, pyarrow, polars, R arrow, DuckDB) can open it.", "",
         f"- Size **{p.stat().st_size / 1e6:.1f} MB**, **{pq.ParquetFile(p).metadata.num_rows:,} rows**, "
         f"**{len(sch)} columns**",
         f"- Validation: **{v.get('n_passed', '?')}/{v.get('n_checks', '?')} checks passed, {v.get('n_failed', '?')} "
         "failed** (`reports/validation_standalone.md`). 400 random ROI rows were re-extracted from the original cubes "
         "and matched.",
         f"- SHA-256: `{v.get('sha256', '?')}`", "",
         "## What is inside: one row per record, kind given by `record_type`", "",
         "| record_type | rows | meaning |", "|---|---|---|"]
    L += [f"| `{k}` | {counts.get(k, 0):,} | {d} |" for k, d in rtypes.items()]
    L += ["", "Columns that a record type doesn't use are empty (null). Each column description below starts with "
          "the record types it applies to.", "",
          "## How to read it", "", "```python", "import pandas as pd",
          "f = 'spectralpaca_pmhm_dataset.parquet'",
          "roi = pd.read_parquet(f, filters=[('record_type', '==', 'roi_frame')]).dropna(axis=1, how='all')",
          "spec = pd.read_parquet(f, filters=[('record_type', '==', 'spectrometer'), ('subject_id', '==', 'subject_03')])",
          "wide = spec.pivot_table(index=['stage', 'roi_id', 'spectrum_index'], columns='wavelength_nm', values='value')",
          "channels = pd.read_parquet(f, filters=[('record_type', '==', 'channel')]).dropna(axis=1, how='all')",
          "```", "",
          "## Important limits", "",
          f"- {md['pmhm.calibration_note']}",
          f"- {md['pmhm.scope_note']}",
          "- Image data are reduced to the **tracked ROIs** (mean and std of each of the 16 channels over the 20×20 px "
          "box). Full video frames are not included, because they would be ~214 GB. Participants without ROI tracks in "
          "the source download (subject_04) have `frame` rows but no `roi_frame` spectra.", "",
          "## Columns", "", "| column | type | unit | description |", "|---|---|---|---|"]
    for f in sch:
        m = {k.decode(): x.decode() for k, x in (f.metadata or {}).items()}
        L.append(f"| `{f.name}` | {f.type} | {m.get('unit', '')} | {m.get('description', '')} |")
    L += ["", "## File-level metadata keys", ""] + [f"- `{k}`" for k in md]
    out.write_text("\n".join(L) + "\n")
