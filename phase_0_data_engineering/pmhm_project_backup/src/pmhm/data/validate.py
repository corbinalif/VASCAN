"""Independent validation of the PMHM Parquet dataset against the raw sources.

Uses code paths separate from the converter (whole-file pandas reads, different chunk sizes,
feather copies, cube metadata re-read) so a converter bug cannot validate itself.
"""
from __future__ import annotations

import json
import logging
from pathlib import Path

import numpy as np
import pandas as pd
import pyarrow as pa
import pyarrow.compute as pc
import pyarrow.feather as pf
import pyarrow.parquet as pq

from ..config import Config
from ..utils.provenance import count_data_lines, sha256_file, utc_now
from ..utils.resources import snapshot
from . import schema as S
from .stages import canonical_subject

log = logging.getLogger(__name__)


class Checks:
    def __init__(self):
        self.items: list[dict] = []

    def add(self, table: str, name: str, ok: bool | None, detail="", level="error"):
        status = "pass" if ok else ("warn" if level == "warn" or ok is None else "fail")
        self.items.append({"table": table, "check": name, "status": status, "detail": str(detail)})
        (log.info if status == "pass" else log.warning)("[%s] %s/%s: %s", status.upper(), table, name, detail)

    def eq(self, table, name, a, b, level="error"):
        self.add(table, name, a == b, f"{a} vs {b}", level)


def _arrays_equal(a, b) -> bool:
    a, b = np.asarray(a), np.asarray(b)
    if a.shape != b.shape:
        return False
    if a.dtype.kind == "f" or b.dtype.kind == "f":
        return bool(np.array_equal(a.astype(np.float64), b.astype(np.float64), equal_nan=True))
    return bool(np.array_equal(a.astype(str), b.astype(str)) if a.dtype.kind in "OUS" else np.array_equal(a, b))


def check_structure(ck: Checks, out: Path, catalog: dict) -> None:
    for name, spec in S.ALL_TABLES.items():
        p = out / f"{name}.parquet"
        if not p.exists():
            ck.add(name, "file_exists", False, p)
            continue
        sch = pq.read_schema(p)
        exp = spec.schema()
        ck.add(name, "schema_matches_spec",
               [(f.name, str(f.type)) for f in sch] == [(f.name, str(f.type)) for f in exp],
               f"{len(sch)} columns")
        ck.add(name, "column_metadata_embedded",
               all(f.metadata and b"description" in f.metadata and b"unit" in f.metadata for f in sch))
        ck.add(name, "table_metadata_embedded",
               all(k in (sch.metadata or {}) for k in (b"pmhm.table", b"pmhm.sources", b"pmhm.primary_key")))
        md = pq.ParquetFile(p).metadata
        # nulls in non-nullable columns, from column-chunk statistics
        nulls = {}
        for ci, col in enumerate(spec.columns):
            n = sum((md.row_group(r).column(ci).statistics.null_count or 0)
                    for r in range(md.num_row_groups) if md.row_group(r).column(ci).statistics)
            nulls[col.name] = n
        bad = {k: v for k, v in nulls.items() if v and not spec.columns[spec.names.index(k)].nullable}
        ck.add(name, "no_nulls_in_required_columns", not bad, bad or "ok")
        ent = catalog["tables"].get(name, {})
        ck.eq(name, "row_count_matches_catalog", md.num_rows, ent.get("rows"))
        ck.add(name, "sha256_matches_catalog", sha256_file(p) == ent.get("sha256"))
        # primary key uniqueness (row-group-wise for the large spectrometer table to bound memory:
        # each row group holds exactly one (subject, stage, ROI) group)
        pk = list(spec.primary_key)
        if name == "master_spectrometer":
            pf_ = pq.ParquetFile(p)
            seen, dup, grp_dup = set(), 0, 0
            for rg in range(md.num_row_groups):
                t = pf_.read_row_group(rg, columns=pk)
                g = t.select(pk[:3]).group_by(pk[:3]).aggregate([])
                if g.num_rows != 1:
                    grp_dup += 1
                key = tuple(g.to_pylist()[0].values())
                grp_dup += key in seen
                seen.add(key)
                dup += t.num_rows - t.select(pk[3:]).group_by(pk[3:]).aggregate([]).num_rows
            ck.add(name, "primary_key_unique", dup == 0 and grp_dup == 0,
                   f"{md.num_row_groups} row groups, {len(seen)} distinct (subject,stage,ROI), {dup} duplicate keys")
        else:
            t = pq.read_table(p, columns=pk)
            if t.num_rows:
                ck.eq(name, "primary_key_unique", t.group_by(pk).aggregate([]).num_rows, t.num_rows)
            del t
        # raw immutability: sources hashed at conversion time must still match
        srcs = json.loads(sch.metadata[b"pmhm.sources"])
        changed = [s["path"] for s in srcs if sha256_file(Path(catalog["dataset_root"]) / s["path"]) != s["sha256"]]
        ck.add(name, "raw_sources_unchanged_since_conversion", not changed, changed or f"{len(srcs)} sources verified")


def check_rois(ck: Checks, cfg: Config, out: Path, manifest: pd.DataFrame) -> None:
    t = "master_rois"
    rois = pd.read_parquet(out / f"{t}.parquet")
    frames = pd.read_parquet(out / "master_frames.parquet",
                             columns=["subject_id", "frame_index", "stage", "time_delta_s", "exposure_ms", "n_rois_tracked"])
    src = manifest[manifest.table == t]
    total = 0
    for m in src.itertuples():
        path = cfg.root / m.source
        raw = pd.read_csv(path) if m.format == "csv" else pf.read_table(path).to_pandas()
        sub = rois[(rois.subject_id == m.subject_id) & (rois.roi_id == int(m.roi_id))].sort_values("source_row_index")
        tag = f"{m.subject_id}/roi_{int(m.roi_id)}"
        n_lines = count_data_lines(path) if m.format == "csv" else pf.read_table(path).num_rows
        ck.eq(t, f"rowcount[{tag}]", len(sub), n_lines)
        same = all(_arrays_equal(sub[c].to_numpy(), raw[c].to_numpy()) for c in ("y1", "x1", "y2", "x2", "stage")) \
            and _arrays_equal(sub.time_delta_s.to_numpy(), raw.time_delta.to_numpy())
        ck.add(t, f"values_identical_to_source[{tag}]", same, m.source)
        if isinstance(m.alternate_copy, str) and m.alternate_copy:
            alt = pf.read_table(cfg.root / m.alternate_copy).to_pandas()
            ck.add(t, f"csv_feather_copies_identical[{tag}]",
                   len(alt) == len(raw) and all(_arrays_equal(alt[c].to_numpy(), raw[c].to_numpy()) for c in raw.columns),
                   m.alternate_copy)
        total += len(sub)
    ck.eq(t, "rows_equal_sum_of_sources", len(rois), total)
    # join correctness: matched frame must carry identical (stage, time_delta)
    j = rois[rois.has_image_frame].merge(frames, on=["subject_id", "frame_index"], suffixes=("", "_f"), how="left")
    ck.add(t, "frame_join_exact", bool((j.stage == j.stage_f).all() and (j.time_delta_s == j.time_delta_s_f).all()
                                       and (j.exposure_ms == j.exposure_ms_f).all()), f"{len(j)} matched rows")
    un = rois[~rois.has_image_frame & rois.image_locally_available]
    if len(un):
        last = frames.groupby("subject_id").time_delta_s.max()
        beyond = (un.time_delta_s > un.subject_id.map(last)).all()
        ck.add(t, "unmatched_rows_are_after_cube_end", bool(beyond),
               f"{len(un)} rows tracked after last cube frame (kept, frame_index=null)", level="warn" if beyond else "error")
    # derived columns re-computed
    ck.add(t, "derived_bbox_consistent", bool(((rois.x2 - rois.x1) == rois.bbox_width_px).all()
                                              and ((rois.y2 - rois.y1) == rois.bbox_height_px).all()))
    cnt = rois[rois.has_image_frame].groupby(["subject_id", "frame_index"]).size()
    fr = frames.set_index(["subject_id", "frame_index"]).n_rois_tracked
    ck.add("master_frames", "n_rois_tracked_consistent", bool((cnt.reindex(fr.index, fill_value=0) == fr).all()))
    oob = int((~rois.bbox_in_image_bounds).sum())
    ck.add(t, "bbox_within_image", oob == 0, f"{oob} out-of-bounds boxes", level="warn")


def check_frames(ck: Checks, cfg: Config, out: Path) -> None:
    import blosc2
    t = "master_frames"
    fr = pd.read_parquet(out / f"{t}.parquet", columns=["subject_id", "frame_index", "stage", "time_delta_s", "exposure_ms"])
    for s, g in fr.groupby("subject_id"):
        a = blosc2.open(str(cfg.raw_path("ximea_dir") / f"{s}.b2nd"), mode="r")
        m = a.schunk.meta
        ck.eq(t, f"rowcount_vs_cube_frames[{s}]", len(g), a.shape[0])
        ok = (_arrays_equal(g.stage.to_numpy(), np.array(m["stage"])) and _arrays_equal(g.time_delta_s, m["time_delta"])
              and _arrays_equal(g.exposure_ms.to_numpy(), np.array(m["exposure"])))
        ck.add(t, f"values_identical_to_cube_meta[{s}]", ok)
        ck.add(t, f"time_monotonic[{s}]", bool(np.all(np.diff(g.time_delta_s.to_numpy()) > 0)))


def check_spectrometer(ck: Checks, cfg: Config, out: Path, subjects: list[str] | None) -> None:
    t = "master_spectrometer"
    p = out / f"{t}.parquet"
    path = cfg.raw_path("spectrometer_csv")
    pf_ = pq.ParquetFile(p)
    # 1. tandem stream: CSV (independent chunk size) vs parquet batches, every row compared
    cols = ["wavelength_nm", "reflectance_au", "subject_label_original", "stage_original", "roi_id", "source_row_index"]
    batches = pf_.iter_batches(batch_size=65536, columns=cols)
    buf = None
    n_cmp, mismatch, pos = 0, 0, 0
    for chunk in pd.read_csv(path, chunksize=40000, float_precision="round_trip"):
        chunk["_row"] = np.arange(pos, pos + len(chunk))
        pos += len(chunk)
        if subjects:
            chunk = chunk[chunk.subject.map(canonical_subject).isin(subjects)]
        need = len(chunk)
        while need and (buf is None or len(buf) < need):
            nb = next(batches).to_pandas()
            buf = nb if buf is None else pd.concat([buf, nb], ignore_index=True)
        if not need:
            continue
        part, buf = buf.iloc[:need], buf.iloc[need:].reset_index(drop=True)
        eq = (np.array_equal(part.wavelength_nm.to_numpy(), chunk["wavelength [nm]"].to_numpy())
              and np.array_equal(part.reflectance_au.to_numpy(), chunk["reflectance [a.u.]"].to_numpy())
              and (part.subject_label_original.to_numpy() == chunk.subject.to_numpy()).all()
              and (part.stage_original.to_numpy() == chunk.stage.to_numpy()).all()
              and np.array_equal(part.roi_id.to_numpy().astype(int), chunk.ROI.to_numpy().astype(int))
              and np.array_equal(part.source_row_index.to_numpy(), chunk._row.to_numpy()))
        mismatch += 0 if eq else 1
        n_cmp += need
    leftover = (0 if buf is None else len(buf)) + sum(b.num_rows for b in batches)
    ck.add(t, "every_row_identical_to_csv", mismatch == 0 and leftover == 0,
           f"{n_cmp:,} rows compared, {mismatch} mismatching chunks, {leftover} extra parquet rows")
    ck.eq(t, "rowcount_vs_csv", pf_.metadata.num_rows, n_cmp)
    if not subjects:
        ck.eq(t, "rowcount_vs_independent_line_count", pf_.metadata.num_rows, count_data_lines(path))
    # 2. feather copy cross-check (column at a time to bound memory)
    fe = cfg.raw_path("spectrometer_feather")
    if fe.exists():
        fsub = pf.read_table(fe, columns=["subject"])
        if subjects:
            labels = [f"subject {int(s.split('_')[1])}" for s in subjects]
            mask = pc.is_in(fsub["subject"], value_set=pa.array(labels))
        else:
            mask = None
        ok = True
        for fcol, qcol in [("wavelength [nm]", "wavelength_nm"), ("reflectance [a.u.]", "reflectance_au"),
                           ("subject", "subject_label_original"), ("stage", "stage_original"), ("ROI", "roi_id")]:
            a = pf.read_table(fe, columns=[fcol])[fcol]
            a = a.filter(mask) if mask is not None else a
            b = pq.read_table(p, columns=[qcol])[qcol]
            if qcol == "roi_id":
                a = pc.cast(a, pa.int8())
            ok &= len(a) == len(b) and bool(pc.all(pc.equal(a, b)).as_py())
            del a, b
        ck.add(t, "identical_to_feather_copy", ok, cfg.rel(fe))
    # 3. scientific checks on derived spectrum_index, one row group = one (subject, stage, ROI)
    incomplete, corrs, n_spec = 0, [], 0
    for rg in range(pf_.metadata.num_row_groups):
        g = pf_.read_row_group(rg, columns=["spectrum_index", "wavelength_index", "reflectance_au"]).to_pandas()
        P = g.pivot(index="spectrum_index", columns="wavelength_index", values="reflectance_au")
        incomplete += int(P.isna().any(axis=1).sum())
        n_spec += len(P)
        X = P.to_numpy()
        if len(X) > 3:
            a, b = X[:, :-1], X[:, 1:]
            za = (a - a.mean(0)) / (a.std(0) + 1e-12)
            zb = (b - b.mean(0)) / (b.std(0) + 1e-12)
            corrs.append(float(np.median((za * zb).mean(0))))
    ck.add(t, "every_spectrum_has_full_wavelength_grid", incomplete == 0, f"{n_spec} spectra, {incomplete} incomplete")
    mc = float(np.min(corrs)) if corrs else float("nan")
    ck.add(t, "replicate_order_coherent(min adjacent-wl corr across groups)", mc > 0.8,
           f"min {mc:.3f}, median {np.median(corrs):.3f} over {len(corrs)} groups")
    neg = pq.read_table(p, columns=["flag_negative_reflectance"])["flag_negative_reflectance"]
    ck.add(t, "negative_reflectance_values", None, f"{pc.sum(neg).as_py():,} rows < 0 (kept unmodified; flagged)", "warn")


def check_small(ck: Checks, cfg: Config, out: Path) -> None:
    pairs = [("optics_ximea_filters", cfg.raw_path("optics_dir") / "ximea_filters.csv",
              {"Wavelength [nm]": "wavelength_nm", "filter": "filter_id", "Filter response [a.u.]": "filter_response_au"}),
             ("optics_xenon_light_source", cfg.raw_path("optics_dir") / "xenon_light_source.csv",
              {"wavelength [nm]": "wavelength_nm", "relative_irradiance [a.u.]": "relative_irradiance_au"}),
             ("color_checker_spectrometer_adapted", cfg.raw_path("color_checker_dir") / "spectrometer_adapted.csv",
              {"reflectance": "reflectance", "wavelength": "wavelength_nm", "color_name": "color_name",
               "color": "color_hex", "band": "band", "ind": "color_index"})]
    for t, src, cmap in pairs:
        q = pd.read_parquet(out / f"{t}.parquet").sort_values("source_row_index")
        raw = pd.read_csv(src, float_precision="round_trip")
        ck.eq(t, "rowcount_vs_source", len(q), count_data_lines(src))
        ck.add(t, "values_identical_to_csv", all(_arrays_equal(q[v].to_numpy(), raw[k].to_numpy()) for k, v in cmap.items()))
        fe = src.with_suffix(".feather")
        if fe.exists():
            f = pf.read_table(fe).to_pandas()
            exact, tol_ok, maxdiff = 0, True, 0.0
            for k, v in cmap.items():
                a, b = q[v].to_numpy(), f[k].to_numpy()
                if a.dtype.kind == "f":
                    dif = np.abs(a - b.astype(np.float64))
                    exact += int((dif != 0).sum())
                    maxdiff = max(maxdiff, float(dif.max()))
                    tol_ok &= bool(np.allclose(a, b, rtol=0, atol=1e-12))
                else:
                    tol_ok &= _arrays_equal(a, b)
            extra = set(f.columns) - set(cmap)
            ck.add(t, "values_identical_to_feather_copy(atol 1e-12)", tol_ok,
                   f"{exact} float values differ in last digits (max {maxdiff:.1e}; CSV text rounding)"
                   + (f"; extra feather column(s) ignored: {','.join(extra)}" if extra else ""))
    ch = pd.read_parquet(out / "ref_channels.parquet")
    d = (ch.peak_wavelength_nm - ch.nominal_wavelength_nm).abs()
    ck.add("ref_channels", "filter_peak_within_3nm_of_nominal", bool((d <= 3).all()), f"max |diff| {d.max()} nm")
    ck.add("ref_channels", "colorchecker_band_mapping_matches_nominal",
           bool((ch.colorchecker_band_wavelength_nm == ch.nominal_wavelength_nm).all()))


def quality_findings(cfg: Config, out: Path) -> dict:
    fr = pd.read_parquet(out / "master_frames.parquet",
                         columns=["subject_id", "stage_block_index", "stage", "time_delta_s", "frame_interval_s"])
    rois = pd.read_parquet(out / "master_rois.parquet",
                           columns=["subject_id", "roi_id", "displacement_px", "has_image_frame"])
    xe = pd.read_parquet(out / "optics_xenon_light_source.parquet", columns=["flag_negative_irradiance"])
    gaps = fr[fr.frame_interval_s > 1.0][["subject_id", "stage_block_index", "stage", "time_delta_s", "frame_interval_s"]]
    return {
        "timeline_gaps_over_1s": gaps.round(3).to_dict("records"),
        "frame_interval_median_s": fr.groupby("subject_id").frame_interval_s.median().round(4).to_dict(),
        "roi_displacement_px": rois.groupby(["subject_id", "roi_id"]).displacement_px.agg(["mean", "max"]).round(3)
                                   .reset_index().to_dict("records"),
        "roi_rows_without_frame": int((~rois.has_image_frame).sum()),
        "xenon_negative_irradiance_rows": int(xe.flag_negative_irradiance.sum()),
    }


def run_validation(cfg: Config, out: Path, subjects: list[str] | None = None) -> dict:
    catalog = json.loads((out / "_manifest" / "catalog.json").read_text())
    catalog["dataset_root"] = str(cfg.root)
    manifest = pd.read_parquet(out / "_manifest" / "conversion_manifest.parquet")
    ck = Checks()
    log.info("validation of %s | %s", out, snapshot(cfg.root))
    for fn, args in [(check_structure, (ck, out, catalog)), (check_frames, (ck, cfg, out)),
                     (check_rois, (ck, cfg, out, manifest)), (check_spectrometer, (ck, cfg, out, subjects)),
                     (check_small, (ck, cfg, out))]:
        fn(*args)
        log.info("%s done | %s", fn.__name__, snapshot())
    q = quality_findings(cfg, out)
    items = pd.DataFrame(ck.items)
    rep = {"validated_utc": utc_now(), "output_dir": cfg.rel(out), "subjects": subjects or "all",
           "n_checks": len(items), "n_passed": int((items.status == "pass").sum()),
           "n_warn": int((items.status == "warn").sum()), "n_failed": int((items.status == "fail").sum()),
           "checks": ck.items, "quality_findings": q, "resources": snapshot(cfg.root)}
    (out / "_manifest" / "validation_report.json").write_text(json.dumps(rep, indent=2, default=str))
    tag = "pilot_" + "_".join(subjects) if subjects else "full"
    md = [f"# PMHM Parquet validation report — {tag}", "",
          f"_Validated {rep['validated_utc']} — output `{rep['output_dir']}`_", "",
          f"**{rep['n_passed']} passed · {rep['n_warn']} warnings · {rep['n_failed']} failed** "
          f"(of {rep['n_checks']} checks)", "", "| Table | Check | Status | Detail |", "|---|---|---|---|"]
    for i in ck.items:
        st = {"pass": "PASS", "warn": "**WARN**", "fail": "**FAIL**"}[i["status"]]
        md.append(f"| {i['table']} | {i['check']} | {st} | {i['detail'].replace('|', '/')} |")
    md += ["", "## Data-quality findings (informational)", "", "```json", json.dumps(q, indent=1, default=str), "```"]
    rp = cfg.out_path("reports_dir") / f"validation_{tag}.md"
    rp.parent.mkdir(parents=True, exist_ok=True)
    rp.write_text("\n".join(md) + "\n")
    return rep
