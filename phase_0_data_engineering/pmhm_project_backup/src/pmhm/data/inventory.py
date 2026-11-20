"""Read-only dataset inventory: every raw file, its category, completeness and schema (headers only)."""
from __future__ import annotations

import json
import logging
import re
from pathlib import Path

import pandas as pd
import pyarrow as pa
import pyarrow.feather as pf

from ..config import Config
from ..utils.provenance import count_data_lines, sha256_file, utc_now

log = logging.getLogger(__name__)

# Directories created by PMHM itself (not raw data) — excluded from the raw inventory.
PMHM_DIRS = {"configs", "src", "scripts", "tests", "docs", "logs", "reports", "notebooks", "experiments",
             "checkpoints", "results", ".pytest_cache", "__pycache__", ".claude"}
PMHM_FILES = {"CLAUDE.md", ".gitignore", "requirements-pmhm.txt"}
PARTIAL = re.compile(r"\.synapse_download_\d+$")
SUBJ = re.compile(r"subject_(\d{2})")


def _category(rel: str) -> str:
    if PARTIAL.search(rel):
        return "partial_download"
    if rel.startswith("data/ximea/subject_") and rel.endswith(".b2nd"):
        return "hsi_cube"
    if rel.startswith("data/ximea/") and re.search(r"(dark|white)", rel):
        return "calibration_reference"
    if rel.startswith("data/spectrometer/"):
        return "spectrometer"
    if rel == "data/metadata.json":
        return "metadata"
    if rel.startswith("intermediates/rois/"):
        return "roi_track"
    if rel.startswith("intermediates/optics/"):
        return "optics_calibration"
    if rel.startswith("intermediates/color_checker/"):
        return "color_checker"
    if rel.startswith("assets/"):
        return "documentation_asset"
    if rel.startswith("code/"):
        return "loader_code"
    return "project_document"


def _probe(path: Path, ext: str, hash_limit: int) -> dict:
    info: dict = {}
    try:
        if ext == "csv":
            info["columns"] = list(pd.read_csv(path, nrows=0).columns)
            sample = pd.read_csv(path, nrows=1000)
            info["dtypes_sample"] = {k: str(v) for k, v in sample.dtypes.items()}
            info["rows"] = count_data_lines(path)
        elif ext == "feather":
            t = pf.read_table(path, memory_map=True)
            info["columns"] = t.schema.names
            info["dtypes_sample"] = {f.name: str(f.type) for f in t.schema}
            info["rows"] = t.num_rows
            del t
        elif ext == "b2nd":
            import blosc2
            a = blosc2.open(str(path), mode="r")
            info.update(shape=list(a.shape), dtype=str(a.dtype), chunks=list(a.chunks),
                        nchunks=a.schunk.nchunks, cratio=round(float(a.schunk.cratio), 3),
                        meta_keys=[k for k in a.schunk.meta.keys() if k != "b2nd"])
            info["complete_chunks"] = (a.schunk.nchunks == (a.shape[0] if a.ndim == 4 else 1))
        elif ext == "json":
            info["keys"] = list(json.loads(path.read_text()).keys())
    except Exception as e:  # never fail the inventory on one bad file
        info["probe_error"] = f"{type(e).__name__}: {e}"
    if ext in {"csv", "feather", "json", "npy"} and path.stat().st_size <= hash_limit:
        info["sha256"] = sha256_file(path)
    return info


def build_inventory(cfg: Config, hash_limit_bytes: int = 1024**3) -> tuple[pd.DataFrame, dict]:
    root = cfg.root
    processed = cfg.out_path("processed_dir").resolve()
    rows = []
    for path in sorted(root.rglob("*")):
        if not path.is_file():
            continue
        rel_parts = path.relative_to(root).parts
        if rel_parts[0] in PMHM_DIRS or any(p in {"__pycache__", ".pytest_cache"} for p in rel_parts):
            continue
        if path.resolve().is_relative_to(processed) or path.name in PMHM_FILES:
            continue
        rel = "/".join(rel_parts)
        name = PARTIAL.sub("", path.name)
        ext = name.rsplit(".", 1)[-1].lower() if "." in name else ""
        cat = _category(rel)
        m = SUBJ.search(rel)
        rec = {"path": rel, "category": cat, "extension": ext, "bytes": path.stat().st_size,
               "subject_id": m.group(0) if m else None,
               "roi_id": int(re.search(r"roi_(\d+)", name).group(1)) if re.search(r"roi_(\d+)\.", name) else None,
               "status": "partial_download" if cat == "partial_download" else "complete"}
        if cat != "partial_download":
            rec.update(_probe(path, ext, hash_limit_bytes))
        rows.append(rec)
    inv = pd.DataFrame(rows)

    # ---- expected vs present (driven by metadata.json, not assumptions) ----
    meta = json.loads(cfg.raw_path("metadata_json").read_text())
    subjects = sorted(meta["subjects"])
    present = set(inv.path)
    expected = []
    for s in subjects:
        cube = f"data/ximea/{s}.b2nd"
        stub = inv[(inv.category == "partial_download") & inv.path.str.startswith(cube)]
        expected.append({"item": cube, "kind": "hsi_cube", "subject_id": s,
                         "status": "present" if cube in present else ("partial_download" if len(stub) else "missing")})
        expected.append({"item": meta["subjects"][s], "kind": "subject_metadata_json", "subject_id": s,
                         "status": "present" if meta["subjects"][s] in present else "missing"})
        for r in range(1, 5):
            base = f"intermediates/rois/{s}/roi_{r}"
            fmts = [f for f in ("csv", "feather") if f"{base}.{f}" in present]
            expected.append({"item": base + ".(csv|feather)", "kind": "roi_track", "subject_id": s,
                             "status": ("present:" + "+".join(fmts)) if fmts else "missing"})
        mp4 = f"intermediates/rois/{s}/roi_tracking_rgb.mp4"
        expected.append({"item": mp4, "kind": "roi_video", "subject_id": s,
                         "status": "present" if mp4 in present else "missing"})
    for item, kind in [("data/ximea/white.npy|white.b2nd", "white_reference"),
                       ("data/ximea/dark.npy|dark.b2nd", "dark_reference"),
                       ("code/src/data/*.py (DataLoaderXIMEA)", "loader_code"),
                       ("intermediates/color_checker/spectrometer.csv", "color_checker_spectrometer")]:
        if kind == "white_reference":
            st = "present" if any(p.startswith("data/ximea/white") for p in present) else "missing"
        elif kind == "dark_reference":
            st = "present" if any(p.startswith("data/ximea/dark") for p in present) else "missing"
        elif kind == "loader_code":
            st = "present" if any(p.startswith("code/src/") and p.endswith(".py") for p in present) else "missing"
        else:
            st = "present" if item in present else (
                "partial_download" if any(p.startswith(item) for p in inv.path) else "missing")
        expected.append({"item": item, "kind": kind, "subject_id": None, "status": st})
    exp = pd.DataFrame(expected)
    summary = {"generated_utc": utc_now(), "dataset_root": str(root), "n_files": int(len(inv)),
               "total_bytes": int(inv.bytes.sum()), "expected_items": exp.to_dict("records")}
    return inv, summary


def write_inventory_markdown(inv: pd.DataFrame, summary: dict, out: Path) -> None:
    exp = pd.DataFrame(summary["expected_items"])
    gb = lambda b: f"{b / 1024**3:,.2f} GB" if b >= 1024**3 else f"{b / 1024**2:,.2f} MB"
    L = ["# SPECTRALPACA — Local Dataset File Inventory", "",
         f"_Generated {summary['generated_utc']} by `scripts/pmhm_build_dataset.py inventory` (read-only scan; "
         "no raw file was modified)._", "",
         f"- Dataset root: `{summary['dataset_root']}`",
         f"- Raw files found: **{summary['n_files']}**, total **{gb(summary['total_bytes'])}**", ""]
    L += ["## 1. Completeness against `data/metadata.json`", "",
          "| Subject | HSI cube | ROI 1 | ROI 2 | ROI 3 | ROI 4 | ROI video | subject metadata.json |",
          "|---|---|---|---|---|---|---|---|"]
    for s, g in exp[exp.subject_id.notna()].groupby("subject_id"):
        d = {r.kind: r.status for r in g.itertuples() if r.kind != "roi_track"}
        rois = [g[(g.kind == "roi_track") & g.item.str.contains(f"roi_{i}")].status.iloc[0] for i in range(1, 5)]
        cell = lambda v: f"**{v.upper()}**" if v in ("missing", "partial_download") else v
        L.append(f"| {s} | {cell(d['hsi_cube'])} | " + " | ".join(cell(r) for r in rois) +
                 f" | {cell(d['roi_video'])} | {cell(d['subject_metadata_json'])} |")
    L += ["", "| Global item | Status |", "|---|---|"]
    for r in exp[exp.subject_id.isna()].itertuples():
        L.append(f"| `{r.item}` ({r.kind}) | {'**' + r.status.upper() + '**' if r.status != 'present' else r.status} |")
    L += ["", "## 2. Files by category", "", "| Category | Files | Size |", "|---|---|---|"]
    for cat, g in inv.groupby("category"):
        L.append(f"| {cat} | {len(g)} | {gb(g.bytes.sum())} |")
    L += ["", "## 3. Hyperspectral cubes and calibration arrays (`.b2nd`, kept in native format)", "",
          "| File | Shape (frames, H, W, C) | dtype | chunks | stored chunks | compression ratio | per-frame metadata | size |",
          "|---|---|---|---|---|---|---|---|"]
    for r in inv[(inv.extension == "b2nd") & (inv.status == "complete")].itertuples():
        if not isinstance(r.shape, list):
            L.append(f"| `{r.path}` | PROBE ERROR: {getattr(r, 'probe_error', '?')} | | | | | | {gb(r.bytes)} |")
            continue
        L.append(f"| `{r.path}` | {tuple(r.shape)} | {r.dtype} | {tuple(int(x) for x in r.chunks)} | {int(r.nchunks):,} | {r.cratio} | "
                 f"{', '.join(r.meta_keys) or '—'} | {gb(r.bytes)} |")
    L += ["", "## 4. Partial downloads (Synapse resume stubs — left untouched)", "", "| File | Size |", "|---|---|"]
    for r in inv[inv.category == "partial_download"].itertuples():
        L.append(f"| `{r.path}` | {gb(r.bytes)} |")
    L += ["", "## 5. Tabular files (Parquet conversion candidates)", "",
          "| File | Category | Rows | Columns | Size | sha256 (first 12) |", "|---|---|---|---|---|---|"]
    for r in inv[inv.extension.isin(["csv", "feather"]) & (inv.status == "complete")].itertuples():
        cols = ", ".join(f"`{c}`" for c in r.columns) if isinstance(r.columns, list) else "?"
        L.append(f"| `{r.path}` | {r.category} | {int(r.rows):,} | {cols} | {gb(r.bytes)} | "
                 f"`{str(r.sha256)[:12]}` |")
    L += ["", "## 6. Other files", "", "| File | Category | Size |", "|---|---|---|"]
    for r in inv[~inv.extension.isin(["csv", "feather", "b2nd"]) & (inv.category != "partial_download")].itertuples():
        L.append(f"| `{r.path}` | {r.category} | {gb(r.bytes)} |")
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text("\n".join(L) + "\n")


def save_inventory(inv: pd.DataFrame, summary: dict, manifest_dir: Path) -> None:
    manifest_dir.mkdir(parents=True, exist_ok=True)
    flat = inv.copy()
    for c in flat.columns:
        if flat[c].map(lambda v: isinstance(v, (list, dict))).any():
            flat[c] = flat[c].map(lambda v: json.dumps(v) if isinstance(v, (list, dict)) else v)
    pa_tab = pa.Table.from_pandas(flat.astype({c: "string" for c in flat.columns if flat[c].dtype == object}),
                                  preserve_index=False)
    import pyarrow.parquet as pq
    pq.write_table(pa_tab, manifest_dir / "file_inventory.parquet", compression="snappy")
    (manifest_dir / "file_inventory_summary.json").write_text(json.dumps(summary, indent=2, default=str))
