"""Build and validate the standalone single-file dataset ``data/processed/spectralpaca_pmhm_dataset.parquet``.

The file is self-contained: ROI spectral time series are extracted from the hyperspectral cubes, and every other
table (spectrometer, optics, colour checker, channels, stages, subjects, frames) is stored as additional rows
distinguished by ``record_type``. After it is built, the original download is not needed to use it.

Inputs are the validated tables in data/processed/parquet/ plus the native cubes (read lazily, one ROI patch at a time).
"""
from __future__ import annotations

import json
import logging
import shutil
import time
from pathlib import Path

import numpy as np
import pandas as pd
import pyarrow as pa
import pyarrow.compute as pc
import pyarrow.parquet as pq

from .. import __version__
from ..config import Config
from ..utils.provenance import sha256_file, stamp, utc_now
from ..utils.resources import ResourceAbort, snapshot
from .catalog import CubeReader, PMHMDataset
from .convert import ParquetSink
from .schema import RECORD_TYPES, standalone_spec

log = logging.getLogger(__name__)
FILE_NAME = "spectralpaca_pmhm_dataset.parquet"
BATCH = 5000


def standalone_path(cfg: Config) -> Path:
    return cfg.out_path("processed_dir") / FILE_NAME


class UnionSink(ParquetSink):
    """ParquetSink that fills the columns a record type does not use with nulls."""

    def write_records(self, record_type: str, n: int, cols: dict) -> None:
        if n == 0:
            return
        full = {"record_type": np.full(n, record_type, dtype=object)}
        for c in self.spec.columns:
            if c.name == "record_type":
                continue
            full[c.name] = cols[c.name] if c.name in cols else pa.nulls(n, c.type)
        unknown = set(cols) - set(self.spec.names)
        if unknown:
            raise KeyError(f"{record_type}: columns not in schema {sorted(unknown)}")
        self.write(full)


def _obj(v) -> np.ndarray:
    return np.asarray(v, dtype=object)


def _check_mem(floor_mb: float) -> None:
    avail = snapshot()["ram_available_mb"]
    if avail < floor_mb:
        raise ResourceAbort(f"available RAM {avail} MB below floor {floor_mb} MB")


# ----------------------------------------------------------------------------- record writers
def write_roi_frames(sink: UnionSink, ds: PMHMDataset, wls: list[int], floor_mb: float) -> dict:
    stats = {}
    rois_all = ds.load("master_rois", columns=["subject_id", "roi_id"]).drop_duplicates()
    for subj, roi in rois_all.itertuples(index=False):
        r = ds.load("master_rois", filters=[("subject_id", "==", subj), ("roi_id", "==", int(roi))]) \
              .sort_values("source_row_index").reset_index(drop=True)
        cube = CubeReader(subj, cfg=ds.cfg) if r.image_locally_available.any() else None
        t0 = time.time()
        for a in range(0, len(r), BATCH):
            _check_mem(floor_mb)
            b = r.iloc[a:a + BATCH]
            n = len(b)
            mean = np.full((n, len(wls)), np.nan, np.float32)
            std = np.full((n, len(wls)), np.nan, np.float32)
            pmin = np.full(n, np.nan, np.float32)
            pmax = np.full(n, np.nan, np.float32)
            has = b.has_image_frame.to_numpy() & (cube is not None)
            for k, row in enumerate(b.itertuples(index=False)):
                if not has[k]:
                    continue
                p = cube.roi_patch(int(row.frame_index), row.y1, row.x1, row.y2, row.x2).astype(np.float64)
                flat = p.reshape(-1, p.shape[-1])
                mean[k] = flat.mean(0)
                std[k] = flat.std(0)
                pmin[k], pmax[k] = flat.min(), flat.max()
            cols = {c: b[c].to_numpy() for c in ("subject_id", "roi_id", "time_delta_s", "stage", "pressure_mmhg",
                                                  "stage_block_index", "time_in_block_s", "y1", "x1", "y2", "x2",
                                                  "displacement_px", "source_row_index")}
            cols["subject_id"], cols["stage"] = _obj(cols["subject_id"]), _obj(cols["stage"])
            cols["phase"] = _obj(b.phase)
            cols["frame_index"] = b.frame_index.to_numpy(np.float64)
            cols["preceding_pressure_mmhg"] = b.preceding_pressure_mmhg.to_numpy(np.float64)
            cols["exposure_ms"] = b.exposure_ms.to_numpy(np.float64)
            cols["has_image_frame"] = has
            cols["source_file"] = _obj(b.source_file)
            for ch, wl in enumerate(wls):
                cols[f"ch{ch:02d}_{wl}nm_mean"] = mean[:, ch]
                cols[f"ch{ch:02d}_{wl}nm_std"] = std[:, ch]
            cols["roi_patch_min"], cols["roi_patch_max"] = pmin, pmax
            sink.write_records("roi_frame", n, cols)
        sink.flush()  # one row group per (subject, ROI)
        stats[f"{subj}/roi_{roi}"] = {"rows": len(r), "patches_extracted": int(r.has_image_frame.sum()),
                                      "seconds": round(time.time() - t0, 1)}
        log.info("roi_frame %s roi_%d: %d rows (%d patches) in %.1fs | %s", subj, roi, len(r),
                 r.has_image_frame.sum(), time.time() - t0, snapshot())
    return stats


def write_frames(sink: UnionSink, ds: PMHMDataset) -> int:
    f = ds.load("master_frames")
    for subj, g in f.groupby("subject_id", sort=True):
        sink.write_records("frame", len(g), {
            "subject_id": _obj(g.subject_id), "frame_index": g.frame_index.to_numpy(), "stage": _obj(g.stage),
            "time_delta_s": g.time_delta_s.to_numpy(), "exposure_ms": g.exposure_ms.to_numpy(),
            "frame_interval_s": g.frame_interval_s.to_numpy(), "pressure_mmhg": g.pressure_mmhg.to_numpy(),
            "phase": _obj(g.phase), "stage_block_index": g.stage_block_index.to_numpy(),
            "preceding_pressure_mmhg": g.preceding_pressure_mmhg.to_numpy(np.float64),
            "time_in_block_s": g.time_in_block_s.to_numpy(), "n_rois_tracked": g.n_rois_tracked.to_numpy(),
            "source_file": _obj(g.image_file)})
        sink.flush()
    return len(f)


def write_spectrometer(sink: UnionSink, ds: PMHMDataset) -> int:
    pf_ = pq.ParquetFile(ds.path("master_spectrometer"))
    n = 0
    for rg in range(pf_.metadata.num_row_groups):  # one (subject, stage, ROI) per row group
        t = pf_.read_row_group(rg)
        m = t.num_rows
        sink.write_records("spectrometer", m, {
            "subject_id": t["subject_id"], "roi_id": t["roi_id"], "stage": t["stage"],
            "pressure_mmhg": t["pressure_mmhg"], "phase": t["phase"], "wavelength_nm": t["wavelength_nm"],
            "wavelength_index": t["wavelength_index"], "value": t["reflectance_au"],
            "value_quantity": pa.array(["diffuse_reflectance"] * m, pa.string()),
            "flag_negative_value": t["flag_negative_reflectance"], "spectrum_index": t["spectrum_index"],
            "source_file": t["source_file"], "source_row_index": t["source_row_index"]})
        sink.flush()
        n += m
    return n


def write_reference(sink: UnionSink, ds: PMHMDataset) -> dict:
    out = {}
    f = ds.load("optics_ximea_filters")
    sink.write_records("camera_filter", len(f), {
        "wavelength_nm": f.wavelength_nm.to_numpy(np.float64), "wavelength_index": f.wavelength_sample_index.to_numpy(),
        "value": f.filter_response_au.to_numpy(), "value_quantity": _obj(["filter_response"] * len(f)),
        "channel_index": f.channel_index.to_numpy(), "source_file": _obj(f.source_file),
        "source_row_index": f.source_row_index.to_numpy()})
    sink.flush()  # one row group per record type
    out["camera_filter"] = len(f)
    x = ds.load("optics_xenon_light_source")
    sink.write_records("light_source", len(x), {
        "wavelength_nm": x.wavelength_nm.to_numpy(), "value": x.relative_irradiance_au.to_numpy(),
        "value_quantity": _obj(["relative_irradiance"] * len(x)), "flag_negative_value": x.flag_negative_irradiance.to_numpy(),
        "source_file": _obj(x.source_file), "source_row_index": x.source_row_index.to_numpy()})
    sink.flush()  # one row group per record type
    out["light_source"] = len(x)
    c = ds.load("color_checker_spectrometer_adapted")
    sink.write_records("color_checker", len(c), {
        "wavelength_nm": c.wavelength_nm.to_numpy(np.float64), "value": c.reflectance.to_numpy(),
        "value_quantity": _obj(["band_adapted_reflectance"] * len(c)), "channel_index": c.band.to_numpy(),
        "color_name": _obj(c.color_name), "color_index": c.color_index.to_numpy(), "color_hex": _obj(c.color_hex),
        "source_file": _obj(c.source_file), "source_row_index": c.source_row_index.to_numpy()})
    sink.flush()  # one row group per record type
    out["color_checker"] = len(c)
    ch = ds.load("ref_channels")
    sink.write_records("channel", len(ch), {
        "channel_index": ch.channel_index.to_numpy(), "wavelength_nm": ch.nominal_wavelength_nm.to_numpy(np.float64),
        "peak_wavelength_nm": ch.peak_wavelength_nm.to_numpy(), "fwhm_nm": ch.fwhm_nm.to_numpy(),
        "secondary_peak_ratio": ch.secondary_peak_ratio.to_numpy(), "dark_mean": ch.dark_mean.to_numpy(),
        "dark_std": ch.dark_std.to_numpy(),
        "source_file": _obj(["intermediates/optics/ximea_filters.csv + data/ximea/dark.b2nd"] * len(ch))})
    sink.flush()  # one row group per record type
    out["channel"] = len(ch)
    st = ds.load("ref_stages")
    sink.write_records("stage", len(st), {
        "stage_order": st.stage_order.to_numpy(), "stage": _obj(st.stage), "pressure_mmhg": st.pressure_mmhg.to_numpy(),
        "phase": _obj(st.phase), "spectrometer_stage_label": _obj(st.spectrometer_stage_label),
        "blocks_per_session": st.blocks_per_session.to_numpy(np.float64),
        "source_file": _obj(["data/metadata.json"] * len(st))})
    sink.flush()  # one row group per record type
    out["stage"] = len(st)
    su = ds.load("ref_subjects")
    sink.write_records("subject", len(su), {
        "subject_id": _obj(su.subject_id), "cube_status": _obj(su.cube_status), "n_frames": su.n_frames.to_numpy(np.float64),
        "exposure_ms": su.exposure_ms.to_numpy(np.float64), "frame_rate_hz": su.frame_rate_hz.to_numpy(),
        "duration_s": su.duration_s.to_numpy(), "roi_ids_available": _obj(su.roi_ids_available),
        "n_spectra_baseline": su.n_spectra_baseline.to_numpy(), "n_spectra_160mmHg": su.n_spectra_160mmHg.to_numpy(),
        "source_file": _obj(su.cube_file)})
    out["subject"] = len(su)
    sink.flush()
    return out


# ----------------------------------------------------------------------------- build
def build_standalone(cfg: Config) -> dict:
    t0 = time.time()
    ds = PMHMDataset(cfg=cfg)
    wls = cfg.channel_wavelengths
    spec = standalone_spec(wls)
    out = standalone_path(cfg)
    if out.exists():
        vdir = cfg.out_path("versions_dir")
        vdir.mkdir(parents=True, exist_ok=True)
        moved = vdir / f"{out.stem}_{stamp()}.parquet"
        shutil.move(str(out), str(moved))
        log.info("previous standalone file preserved at %s", moved)
    sp_meta = ds.table_metadata("master_spectrometer")
    meta = {
        "pmhm.title": "SPECTRALPACA - PMHM standalone dataset",
        "pmhm.dataset": "SPECTRALPACA (Ayala et al., Sci Data 2024, doi:10.1038/s41597-024-03307-y, Synapse syn51625685)",
        "pmhm.license": "CC BY 4.0 (dataset)",
        "pmhm.pipeline_version": __version__, "pmhm.created_utc": utc_now(),
        "pmhm.record_types": json.dumps(RECORD_TYPES),
        "pmhm.how_to_read": "Filter on record_type first, e.g. pandas.read_parquet(f, filters=[('record_type','==',"
                            "'roi_frame')]). Columns not used by a record type are null; each column's description "
                            "starts with the record types it applies to.",
        "pmhm.camera": json.dumps({"model": cfg.raw["camera"]["model"], "height_px": cfg.raw["camera"]["height_px"],
                                   "width_px": cfg.raw["camera"]["width_px"], "channel_order_nm": wls,
                                   "roi_box_px": [20, 20]}),
        "pmhm.spectrometer": json.dumps({"model": cfg.raw["spectrometer"]["model"],
                                         "wavelength_grid_nm": sp_meta.get("pmhm.wavelength_grid_nm")}),
        "pmhm.calibration_note": "ROI values are raw camera counts. No white reference is available in the source "
                                 "download and the dark reference exposure is undocumented; dark statistics per "
                                 "channel are given in record_type='channel' rows.",
        "pmhm.scope_note": "10 healthy volunteers, 16 visible channels (465-641 nm). Not a PAD cohort; values are "
                           "not StO2 or perfusion measurements.",
        "pmhm.built_from": json.dumps({k: {"sha256": v["sha256"], "rows": v["rows"]}
                                       for k, v in ds.catalog["tables"].items()}),
    }
    sink = UnionSink(out, spec, meta, cfg.conversion)
    floor = float(cfg.conversion["abort_below_available_mb"])
    counts = {}
    try:
        roi_stats = write_roi_frames(sink, ds, wls, floor)
        counts["roi_frame"] = sum(v["rows"] for v in roi_stats.values())
        counts["frame"] = write_frames(sink, ds)
        counts["spectrometer"] = write_spectrometer(sink, ds)
        counts.update(write_reference(sink, ds))
        res = sink.close()
    except BaseException:
        sink.writer.close()
        sink.tmp.unlink(missing_ok=True)  # incomplete temp output only; never a finished file
        raise
    res.update(path=cfg.rel(out), sha256=sha256_file(out), record_counts=counts, roi_extraction=roi_stats,
               elapsed_s=round(time.time() - t0, 1), resources=snapshot(cfg.root))
    log.info("standalone file %s: %d rows, %.1f MB, %.0fs", out.name, res["rows"], res["bytes"] / 1e6, res["elapsed_s"])
    return res


# ----------------------------------------------------------------------------- validation
def validate_standalone(cfg: Config, build_info: dict | None = None, n_sample: int = 400, seed: int = 0) -> dict:
    from .validate import Checks
    ds = PMHMDataset(cfg=cfg)
    path = standalone_path(cfg)
    wls = cfg.channel_wavelengths
    spec = standalone_spec(wls)
    ck = Checks()
    T = "standalone"
    sch = pq.read_schema(path)
    ck.add(T, "schema_matches_spec", [(f.name, str(f.type)) for f in sch] ==
           [(f.name, str(f.type)) for f in spec.schema()], f"{len(sch)} columns")
    ck.add(T, "column_docs_embedded", all(f.metadata and b"description" in f.metadata for f in sch))
    ck.add(T, "file_metadata_embedded", all(k in sch.metadata for k in (b"pmhm.record_types", b"pmhm.camera",
                                                                         b"pmhm.dataset", b"pmhm.how_to_read")))
    rt = pq.read_table(path, columns=["record_type"])["record_type"]
    counts = pc.value_counts(rt).to_pylist()
    counts = {d["values"]: d["counts"] for d in counts}
    del rt
    expected = {"roi_frame": "master_rois", "frame": "master_frames", "spectrometer": "master_spectrometer",
                "camera_filter": "optics_ximea_filters", "light_source": "optics_xenon_light_source",
                "color_checker": "color_checker_spectrometer_adapted", "channel": "ref_channels",
                "stage": "ref_stages", "subject": "ref_subjects"}
    for rtype, table in expected.items():
        ck.eq(T, f"rows[{rtype}]_equal_{table}", counts.get(rtype, 0), ds.catalog["tables"][table]["rows"])
    ck.add(T, "no_unknown_record_types", set(counts) <= set(RECORD_TYPES), sorted(counts))

    # spectrometer values identical to the validated table (row group by row group)
    pf_ = pq.ParquetFile(path)
    sp = pq.ParquetFile(ds.path("master_spectrometer"))
    rg_types = []
    for i in range(pf_.metadata.num_row_groups):
        stats = pf_.metadata.row_group(i).column(0).statistics
        rg_types.append(stats.min if stats and stats.min == stats.max else None)
    ck.add(T, "each_row_group_single_record_type", None not in rg_types, f"{len(rg_types)} row groups")
    sp_rgs = [i for i, t in enumerate(rg_types) if t == "spectrometer"]
    ok = len(sp_rgs) == sp.metadata.num_row_groups
    for i, j in zip(sp_rgs, range(sp.metadata.num_row_groups)):
        a = pf_.read_row_group(i, columns=["subject_id", "stage", "roi_id", "spectrum_index", "wavelength_nm",
                                           "value", "source_row_index"])
        b = sp.read_row_group(j, columns=["subject_id", "stage", "roi_id", "spectrum_index", "wavelength_nm",
                                          "reflectance_au", "source_row_index"])
        ok &= a.num_rows == b.num_rows and all(
            pc.all(pc.equal(a[x], b[y])).as_py() for x, y in [("subject_id", "subject_id"), ("stage", "stage"),
                                                                ("roi_id", "roi_id"), ("spectrum_index", "spectrum_index"),
                                                                ("wavelength_nm", "wavelength_nm"), ("value", "reflectance_au"),
                                                                ("source_row_index", "source_row_index")])
    ck.add(T, "spectrometer_values_identical", bool(ok), f"{len(sp_rgs)} row groups compared")

    # ROI rows: coordinates/time identical; spectral values re-computed by a different read path
    roi = pq.read_table(path, filters=[("record_type", "==", "roi_frame")]).to_pandas()
    src = ds.load("master_rois")
    key = ["subject_id", "roi_id", "source_row_index"]
    m = roi.merge(src, on=key, suffixes=("", "_src"), how="outer", indicator=True)
    ck.add(T, "roi_rows_match_master_rois_1to1", bool((m._merge == "both").all()), m._merge.value_counts().to_dict())
    same = all(bool((m[c].astype("float64") == m[c + "_src"].astype("float64")).all())
               for c in ("y1", "x1", "y2", "x2", "time_delta_s"))
    same &= bool(((m.frame_index.isna() & m.frame_index_src.isna()) | (m.frame_index == m.frame_index_src)).all())
    ck.add(T, "roi_coordinates_time_frame_identical", same)
    mean_cols = [f"ch{ch:02d}_{wl}nm_mean" for ch, wl in enumerate(wls)]
    std_cols = [f"ch{ch:02d}_{wl}nm_std" for ch, wl in enumerate(wls)]
    has = roi.has_image_frame.astype(bool)
    ck.add(T, "spectral_values_present_iff_image_frame",
           bool(roi.loc[has, mean_cols].notna().all().all() and roi.loc[~has, mean_cols].isna().all().all()),
           f"{int(has.sum())} with values, {int((~has).sum())} without (tracked after cube end)")
    rng = np.random.default_rng(seed)
    sample = roi[has].iloc[rng.choice(int(has.sum()), size=min(n_sample, int(has.sum())), replace=False)]
    cubes, max_rel = {}, 0.0
    for r in sample.itertuples(index=False):
        c = cubes.setdefault(r.subject_id, CubeReader(r.subject_id, cfg=cfg))
        frame = np.asarray(c.frame(int(r.frame_index)), dtype=np.float64)  # whole frame, then numpy slice
        p = frame[r.y1:r.y2, r.x1:r.x2, :].reshape(-1, frame.shape[-1])
        stored_m = np.array([getattr(r, k) for k in mean_cols], np.float64)
        stored_s = np.array([getattr(r, k) for k in std_cols], np.float64)
        rel = max(np.max(np.abs(stored_m - p.mean(0)) / np.maximum(1.0, np.abs(p.mean(0)))),
                  np.max(np.abs(stored_s - p.std(0)) / np.maximum(1.0, p.std(0))))
        max_rel = max(max_rel, float(rel))
    ck.add(T, "roi_spectra_recomputed_from_cube", max_rel < 1e-5,
           f"{len(sample)} random ROI-frames re-extracted via full-frame read; max relative diff {max_rel:.2e}")
    for k in ("frame", "subject", "stage", "channel"):
        n_null_src = pq.read_table(path, columns=["source_file", "record_type"],
                                   filters=[("record_type", "==", k)])["source_file"].null_count
        ck.add(T, f"provenance_present[{k}]", n_null_src == 0,
               f"{n_null_src} null source_file" + (" (subjects with no cube in the download)" if k == "subject" else ""),
               level="warn" if k == "subject" else "error")

    items = pd.DataFrame(ck.items)
    rep = {"validated_utc": utc_now(), "file": cfg.rel(path), "sha256": sha256_file(path),
           "bytes": path.stat().st_size, "rows": pf_.metadata.num_rows, "record_counts": counts,
           "n_checks": len(items), "n_passed": int((items.status == "pass").sum()),
           "n_warn": int((items.status == "warn").sum()), "n_failed": int((items.status == "fail").sum()),
           "checks": ck.items, "build": build_info}
    rp = cfg.out_path("reports_dir")
    (rp / "validation_standalone.json").write_text(json.dumps(rep, indent=2, default=str))
    md = [f"# Validation — standalone file `{rep['file']}`", "", f"_Validated {rep['validated_utc']}_", "",
          f"- Size: {rep['bytes'] / 1e6:.1f} MB · rows: {rep['rows']:,} · sha256 `{rep['sha256']}`",
          f"- **{rep['n_passed']} passed · {rep['n_warn']} warnings · {rep['n_failed']} failed**", "",
          "| record_type | rows |", "|---|---|"] + [f"| {k} | {v:,} |" for k, v in counts.items()] + [
          "", "| Check | Status | Detail |", "|---|---|---|"] + [
          f"| {i['check']} | {i['status'].upper()} | {str(i['detail']).replace('|', '/')} |" for i in ck.items]
    (rp / "validation_standalone.md").write_text("\n".join(md) + "\n")
    return rep
