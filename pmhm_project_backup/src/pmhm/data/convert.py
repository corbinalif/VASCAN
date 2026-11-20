"""Memory-safe conversion of SPECTRALPACA tabular data (and cube frame metadata) to Parquet.

Raw files are opened read-only. Outputs are written to ``*.parquet.tmp`` and renamed on success;
a pre-existing output directory is moved to ``data/processed/_versions`` (never deleted).
"""
from __future__ import annotations

import json
import logging
import re
import time
from collections import Counter
from pathlib import Path

import numpy as np
import pandas as pd
import pyarrow as pa
import pyarrow.compute  # noqa: F401  (pa.compute)
import pyarrow.feather as pf
import pyarrow.parquet as pq

from .. import __version__
from ..config import Config
from ..utils.provenance import preserve_existing, sha256_file, utc_now
from ..utils.resources import AdaptiveChunker, snapshot
from . import schema as S
from .stages import BlockTracker, canonical_subject, harmonise_spectrometer_stage, parse_stage

log = logging.getLogger(__name__)
CUBE_RE = re.compile(r"^(subject_\d{2})\.b2nd$")
ROI_RE = re.compile(r"^roi_(\d+)\.(csv|feather)$")


# ----------------------------------------------------------------------------- helpers
def arr(values, typ: pa.DataType) -> pa.Array:
    """numpy/pandas/list -> Arrow array; NaN in a float array becomes null for integer targets."""
    if isinstance(values, pa.ChunkedArray):
        values = values.combine_chunks()
    if isinstance(values, pa.Array):
        return values.cast(typ)
    if isinstance(values, pd.Series):
        values = values.to_numpy()
    if isinstance(values, np.ndarray) and values.dtype.kind == "f" and pa.types.is_integer(typ):
        mask = np.isnan(values)
        return pa.array(np.where(mask, 0, values).astype(np.int64), type=typ, mask=mask)
    # from_pandas=True: None/NaN become null (never the string 'nan')
    return pa.array(values, type=typ, from_pandas=True)


def make_table(spec: S.TableSpec, cols: dict, schema: pa.Schema) -> pa.Table:
    missing = set(spec.names) - set(cols)
    if missing:
        raise KeyError(f"{spec.name}: missing columns {sorted(missing)}")
    n = {len(v) for v in cols.values()}
    if len(n) != 1:
        raise ValueError(f"{spec.name}: ragged columns {n}")
    return pa.Table.from_arrays([arr(cols[c.name], c.type) for c in spec.columns], schema=schema)


def full(n: int, value) -> np.ndarray:
    return np.full(n, value, dtype=object if isinstance(value, str) else None)


class ParquetSink:
    """Buffered ParquetWriter: explicit row-group boundaries, atomic rename on close."""

    def __init__(self, path: Path, spec: S.TableSpec, meta: dict[str, str], cfg: dict):
        self.path, self.spec = path, spec
        self.schema = spec.schema(meta)
        self.tmp = path.with_name(path.name + ".tmp")
        self.writer = pq.ParquetWriter(self.tmp, self.schema, compression=cfg["compression"],
                                       write_statistics=True, use_dictionary=True)
        self.max_rows = int(cfg["max_row_group_rows"])
        self.buf: list[pa.Table] = []
        self.buf_rows = self.rows = self.row_groups = 0

    def write(self, cols: dict) -> None:
        t = make_table(self.spec, cols, self.schema)
        if t.num_rows == 0:
            return
        self.buf.append(t)
        self.buf_rows += t.num_rows
        if self.buf_rows >= self.max_rows:
            self.flush()

    def flush(self) -> None:
        if not self.buf:
            return
        t = pa.concat_tables(self.buf)
        self.writer.write_table(t, row_group_size=t.num_rows)
        self.rows += t.num_rows
        self.row_groups += 1
        self.buf, self.buf_rows = [], 0

    def close(self) -> dict:
        self.flush()
        self.writer.close()
        self.tmp.rename(self.path)
        return {"file": self.path.name, "rows": self.rows, "row_groups": self.row_groups,
                "bytes": self.path.stat().st_size}


def write_small(path: Path, spec: S.TableSpec, cols: dict, meta: dict, cfg: dict) -> dict:
    sink = ParquetSink(path, spec, meta, cfg)
    sink.write(cols)
    return sink.close()


def _running_cumcount(keys: pd.Series, state: Counter) -> np.ndarray:
    """Occurrence number of each key in file order, carried across chunks via ``state``."""
    within = keys.groupby(keys, sort=False).cumcount().to_numpy()
    out = within + np.array([state[k] for k in keys])
    state.update(keys.value_counts().to_dict())
    return out


def stream_csv(path: Path, dtype: dict, chunker: AdaptiveChunker, usecols=None):
    """Yield (start_row, chunk) with chunk size re-evaluated against memory pressure on every read."""
    reader = pd.read_csv(path, dtype=dtype, usecols=usecols, chunksize=chunker.size,
                         float_precision="round_trip", engine="c")
    start = 0
    with reader:
        while True:
            try:
                chunk = reader.get_chunk(chunker.next_size())
            except StopIteration:
                return
            yield start, chunk
            start += len(chunk)


def source_meta(cfg: Config, paths: list[Path], extra: dict | None = None) -> dict[str, str]:
    srcs = [{"path": cfg.rel(p), "sha256": sha256_file(p), "bytes": p.stat().st_size} for p in paths]
    meta = {"pmhm.sources": json.dumps(srcs), "pmhm.pipeline_version": __version__,
            "pmhm.created_utc": utc_now(), "pmhm.dataset": "SPECTRALPACA (Ayala et al., Sci Data 2024, "
            "doi:10.1038/s41597-024-03307-y, Synapse syn51625685)", "pmhm.license": "CC BY 4.0 (dataset)"}
    meta.update({k: (v if isinstance(v, str) else json.dumps(v)) for k, v in (extra or {}).items()})
    return meta


# ----------------------------------------------------------------------------- cube frame metadata
def discover_cubes(cfg: Config) -> dict[str, Path]:
    return {m.group(1): p for p in sorted(cfg.raw_path("ximea_dir").iterdir())
            if (m := CUBE_RE.match(p.name)) and p.is_file()}


def load_frame_meta(path: Path) -> dict:
    import blosc2
    a = blosc2.open(str(path), mode="r")
    m = a.schunk.meta
    stage = list(m["stage"])
    td = np.asarray(m["time_delta"], dtype=np.float64)
    exp = np.asarray(m["exposure"], dtype=np.int64)
    if not (len(stage) == len(td) == len(exp) == a.shape[0] == a.schunk.nchunks):
        raise ValueError(f"{path.name}: metadata length mismatch vs shape {a.shape}")
    keys = list(zip(stage, td.tolist()))
    lookup = {k: i for i, k in enumerate(keys)}
    if len(lookup) != len(keys):
        raise ValueError(f"{path.name}: duplicate (stage, time_delta) keys — ROI join would be ambiguous")
    return {"stage": stage, "time_delta": td, "exposure": exp, "lookup": lookup, "shape": a.shape,
            "dtype": str(a.dtype), "roi_count": np.zeros(len(stage), np.int16)}


# ----------------------------------------------------------------------------- converters
def convert_rois(cfg, out, subjects, frames, cubes, chunker, manifest) -> dict:
    roi_dir = cfg.raw_path("rois_dir")
    H, W = cfg.raw["camera"]["height_px"], cfg.raw["camera"]["width_px"]
    plan = []  # (subject, roi_id, primary_path, fmt, alt_path)
    for sdir in sorted(p for p in roi_dir.iterdir() if p.is_dir()):
        if subjects and sdir.name not in subjects:
            continue
        found: dict[int, dict[str, Path]] = {}
        for f in sdir.iterdir():
            if m := ROI_RE.match(f.name):
                found.setdefault(int(m.group(1)), {})[m.group(2)] = f
        for rid in sorted(found):
            fm = found[rid]
            prim = "csv" if "csv" in fm else "feather"
            plan.append((sdir.name, rid, fm[prim], prim, fm.get("feather") if prim == "csv" else None))
    meta = source_meta(cfg, [p for *_, p, _, _ in plan] + [a for *_, a in plan if a],
                       {"pmhm.image_shape_hw": [H, W]})
    sink = ParquetSink(out / "master_rois.parquet", S.MASTER_ROIS, meta, cfg.conversion)
    dtype = {"y1": "int64", "x1": "int64", "y2": "int64", "x2": "int64", "stage": "str", "time_delta": "float64"}
    for subj, rid, path, fmt, alt in plan:
        fr = frames.get(subj)
        tracker, prev_c, n_src, n_matched = BlockTracker(), None, 0, 0
        cube_rel = f"{cfg.raw['raw']['ximea_dir']}/{subj}.b2nd"
        if fmt == "csv":
            chunks = stream_csv(path, dtype, chunker)
        else:
            df = pf.read_table(path).to_pandas()
            chunks = iter([(0, df)])
        for start, c in chunks:
            n = len(c)
            stages = c["stage"].astype(str).tolist()
            td = c["time_delta"].to_numpy(np.float64)
            blk = tracker.update(stages, td)
            cx = ((c.x1 + c.x2) / 2).to_numpy(np.float32)
            cy = ((c.y1 + c.y2) / 2).to_numpy(np.float32)
            px = np.concatenate([[np.nan if prev_c is None else prev_c[0]], cx[:-1]])
            py = np.concatenate([[np.nan if prev_c is None else prev_c[1]], cy[:-1]])
            disp = np.sqrt((cx - px) ** 2 + (cy - py) ** 2).astype(np.float32)
            prev_c = (cx[-1], cy[-1])
            if fr is not None:
                fidx = np.array([fr["lookup"].get(k, -1) for k in zip(stages, td.tolist())], np.int64)
                has = fidx >= 0
                np.add.at(fr["roi_count"], fidx[has], 1)
                exp = np.where(has, fr["exposure"][np.where(has, fidx, 0)], 0).astype(np.float64)
                exp[~has] = np.nan
                fidx_f = np.where(has, fidx, 0).astype(np.float64)
                fidx_f[~has] = np.nan
            else:
                has = np.zeros(n, bool)
                fidx_f = exp = np.full(n, np.nan)
            n_matched += int(has.sum())
            inb = ((c.x1 >= 0) & (c.x1 < c.x2) & (c.x2 <= W) & (c.y1 >= 0) & (c.y1 < c.y2) & (c.y2 <= H)).to_numpy()
            sink.write({
                "subject_id": full(n, subj), "roi_id": np.full(n, rid), "source_row_index": np.arange(start, start + n),
                "frame_index": fidx_f, "stage": np.array(stages, dtype=object), "time_delta_s": td,
                "y1": c.y1.to_numpy(), "x1": c.x1.to_numpy(), "y2": c.y2.to_numpy(), "x2": c.x2.to_numpy(),
                "bbox_width_px": (c.x2 - c.x1).to_numpy(), "bbox_height_px": (c.y2 - c.y1).to_numpy(),
                "center_x_px": cx, "center_y_px": cy, "displacement_px": disp, "bbox_in_image_bounds": inb,
                **blk, "exposure_ms": exp, "has_image_frame": has, "image_file": full(n, cube_rel),
                "image_locally_available": np.full(n, subj in cubes), "source_file": full(n, cfg.rel(path)),
                "source_format": full(n, fmt),
            })
            n_src += n
        manifest.append({"source": cfg.rel(path), "format": fmt, "table": "master_rois", "subject_id": subj,
                         "roi_id": rid, "source_rows": n_src, "rows_written": n_src,
                         "rows_matched_to_frame": n_matched, "rows_without_frame": n_src - n_matched,
                         "alternate_copy": cfg.rel(alt) if alt else None, "status": "converted"})
        log.info("ROI %s roi_%d (%s): %d rows, %d matched to frames", subj, rid, fmt, n_src, n_matched)
    return sink.close()


def convert_frames(cfg, out, frames, cubes) -> dict:
    meta = source_meta(cfg, [], {"pmhm.cube_files": {s: cfg.rel(cubes[s]) for s in frames},
                                 "pmhm.cube_shapes": {s: list(f["shape"]) for s, f in frames.items()},
                                 "pmhm.channel_wavelengths_nm": cfg.channel_wavelengths})
    sink = ParquetSink(out / "master_frames.parquet", S.MASTER_FRAMES, meta, cfg.conversion)
    for subj, f in frames.items():
        n = len(f["stage"])
        blk = BlockTracker()
        cols = blk.update(f["stage"], f["time_delta"])
        f["block_sequence"] = blk.block_sequence
        dt = np.concatenate([[np.nan], np.diff(f["time_delta"])])
        sink.write({"subject_id": full(n, subj), "frame_index": np.arange(n), "stage": np.array(f["stage"], object),
                    "time_delta_s": f["time_delta"], "exposure_ms": f["exposure"], "frame_interval_s": dt, **cols,
                    "n_rois_tracked": f["roi_count"], "image_file": full(n, cfg.rel(cubes[subj]))})
        sink.flush()  # one row group per subject
    return sink.close()


def convert_spectrometer(cfg, out, subjects, chunker, manifest) -> dict:
    path = cfg.raw_path("spectrometer_csv")
    stage_map = cfg.raw["spectrometer"]["stage_map"]
    dtype = {"wavelength [nm]": "float64", "reflectance [a.u.]": "float64", "subject": "str", "stage": "str",
             "ROI": "int64"}
    # pass 1: wavelength grid (one float column only)
    wl = set()
    for _, c in stream_csv(path, {"wavelength [nm]": "float64"}, chunker, usecols=["wavelength [nm]"]):
        wl.update(c["wavelength [nm]"].unique().tolist())
    grid = np.array(sorted(wl))
    wl_index = {w: i for i, w in enumerate(grid.tolist())}
    meta = source_meta(cfg, [path], {"pmhm.wavelength_grid_nm": [round(w, 3) for w in grid.tolist()],
                                     "pmhm.stage_map": stage_map, "pmhm.instrument": cfg.raw["spectrometer"]["model"]})
    sink = ParquetSink(out / "master_spectrometer.parquet", S.MASTER_SPECTROMETER, meta, cfg.conversion)
    counters: Counter = Counter()
    cur_key, n_src, n_written, groups = None, 0, 0, Counter()
    subj_cache, stage_cache, parsed = {}, {}, {}
    for start, c in stream_csv(path, dtype, chunker):
        n_src += len(c)
        subj = c["subject"].map(lambda v: subj_cache[v] if v in subj_cache else subj_cache.setdefault(v, canonical_subject(v)))
        keep = subj.isin(subjects).to_numpy() if subjects else np.ones(len(c), bool)
        if not keep.any():
            continue
        c, subj = c[keep], subj[keep]
        rows = np.arange(start, start + len(keep))[keep]
        st = c["stage"].map(lambda v: stage_cache[v] if v in stage_cache else stage_cache.setdefault(v, harmonise_spectrometer_stage(v, stage_map)))
        gkey = (subj + "|" + st + "|" + c["ROI"].astype(str)).to_numpy()
        w = c["wavelength [nm]"].to_numpy()
        # replicate index = running occurrence count of (group, wavelength), carried across chunks
        rep = _running_cumcount(pd.Series(gkey) + "|" + pd.Series(w).map(repr), counters)
        # split chunk at group changes so each (subject, stage, ROI) becomes one row group
        bounds = np.flatnonzero(gkey[1:] != gkey[:-1]) + 1
        for a, b in zip(np.r_[0, bounds], np.r_[bounds, len(gkey)]):
            if cur_key is not None and gkey[a] != cur_key:
                sink.flush()
            cur_key = gkey[a]
            groups[cur_key] += b - a
            sl = slice(a, b)
            stg = st.to_numpy()[sl]
            pp = [parsed[s] if s in parsed else parsed.setdefault(s, parse_stage(s)) for s in stg]
            sink.write({
                "subject_id": subj.to_numpy()[sl], "subject_label_original": c["subject"].to_numpy()[sl],
                "stage_original": c["stage"].to_numpy()[sl], "stage": stg,
                "pressure_mmhg": np.array([p for p, _ in pp]), "phase": np.array([ph for _, ph in pp], object),
                "roi_id": c["ROI"].to_numpy()[sl], "spectrum_index": rep[sl],
                "wavelength_index": np.array([wl_index[x] for x in w[sl]]), "wavelength_nm": w[sl],
                "reflectance_au": c["reflectance [a.u.]"].to_numpy()[sl],
                "flag_negative_reflectance": c["reflectance [a.u.]"].to_numpy()[sl] < 0,
                "source_row_index": rows[sl], "source_file": full(b - a, cfg.rel(path)),
            })
            n_written += b - a
        if (start // chunker.size) % 100 == 0:
            log.info("spectrometer: %d source rows read, %d written | %s", n_src, n_written, snapshot())
    res = sink.close()
    manifest.append({"source": cfg.rel(path), "format": "csv", "table": "master_spectrometer",
                     "subject_id": ",".join(subjects) if subjects else "all", "source_rows": n_src,
                     "rows_written": n_written, "status": "converted",
                     "alternate_copy": cfg.rel(cfg.raw_path("spectrometer_feather")),
                     "notes": f"{len(groups)} (subject,stage,ROI) groups; {len(grid)} wavelengths"})
    res["n_groups"] = len(groups)
    return res


def convert_small_csv(cfg, out, name, spec, path, dtype, build, chunker, manifest, extra_meta=None) -> dict:
    sink = ParquetSink(out / f"{name}.parquet", spec, source_meta(cfg, [path], extra_meta), cfg.conversion)
    n = 0
    for start, c in stream_csv(path, dtype, chunker):
        cols = build(c)
        cols["source_row_index"] = np.arange(start, start + len(c))
        cols["source_file"] = full(len(c), cfg.rel(path))
        sink.write(cols)
        n += len(c)
    res = sink.close()
    manifest.append({"source": cfg.rel(path), "format": "csv", "table": name, "source_rows": n,
                     "rows_written": res["rows"], "status": "converted",
                     "alternate_copy": cfg.rel(path.with_suffix(".feather")) if path.with_suffix(".feather").exists() else None})
    return res


def convert_optics_and_cc(cfg, out, chunker, manifest) -> dict:
    wls = cfg.channel_wavelengths
    od, cd = cfg.raw_path("optics_dir"), cfg.raw_path("color_checker_dir")
    res = {}
    filt_state: Counter = Counter()
    res["optics_ximea_filters"] = convert_small_csv(
        cfg, out, "optics_ximea_filters", S.OPTICS_FILTERS, od / "ximea_filters.csv",
        {"Wavelength [nm]": "int64", "filter": "int64", "Filter response [a.u.]": "float64"},
        lambda c: {"wavelength_nm": c["Wavelength [nm]"].to_numpy(), "filter_id": c["filter"].to_numpy(),
                   "wavelength_sample_index": _running_cumcount(c["filter"], filt_state),
                   "filter_response_au": c["Filter response [a.u.]"].to_numpy(),
                   "channel_index": (c["filter"] - 1).to_numpy(),
                   "channel_nominal_wavelength_nm": np.array([wls[f - 1] for f in c["filter"]])},
        chunker, manifest)
    res["optics_xenon_light_source"] = convert_small_csv(
        cfg, out, "optics_xenon_light_source", S.OPTICS_XENON, od / "xenon_light_source.csv",
        {"wavelength [nm]": "float64", "relative_irradiance [a.u.]": "float64"},
        lambda c: {"wavelength_nm": c["wavelength [nm]"].to_numpy(),
                   "relative_irradiance_au": c["relative_irradiance [a.u.]"].to_numpy(),
                   "flag_negative_irradiance": (c["relative_irradiance [a.u.]"] < 0).to_numpy()},
        chunker, manifest)
    res["color_checker_spectrometer_adapted"] = convert_small_csv(
        cfg, out, "color_checker_spectrometer_adapted", S.COLOR_CHECKER_SPEC, cd / "spectrometer_adapted.csv",
        {"reflectance": "float64", "wavelength": "int64", "color_name": "str", "color": "str", "band": "int64",
         "ind": "int64"},
        lambda c: {"reflectance": c.reflectance.to_numpy(), "wavelength_nm": c.wavelength.to_numpy(),
                   "color_name": c.color_name.to_numpy(), "color_hex": c.color.to_numpy(),
                   "band": c.band.to_numpy(), "color_index": c.ind.to_numpy()},
        chunker, manifest)
    # colour-checker cube frame metadata
    import blosc2
    cols = {k: [] for k in S.COLOR_CHECKER_FRAMES.names}
    paths = []
    for cube in ("ximea_raw", "ximea_norm"):
        p = cd / f"{cube}.b2nd"
        if not p.exists():
            continue
        paths.append(p)
        a = blosc2.open(str(p), mode="r")
        m = a.schunk.meta
        n = a.shape[0]
        cols["cube"] += [cube] * n
        cols["frame_index"] += list(range(n))
        cols["color_name"] += list(m["color"])
        cols["time_delta_s"] += list(m["time_delta"])
        cols["exposure_ms"] += list(m["exposure"])
        cols["image_file"] += [cfg.rel(p)] * n
        manifest.append({"source": cfg.rel(p), "format": "b2nd(meta only)", "table": "color_checker_frames",
                         "source_rows": n, "rows_written": n, "status": "converted",
                         "notes": f"cube shape {tuple(a.shape)} {a.dtype} kept native"})
    res["color_checker_frames"] = write_small(out / "color_checker_frames.parquet", S.COLOR_CHECKER_FRAMES,
                                              {k: np.array(v, dtype=object) if k in ("cube", "color_name", "image_file")
                                               else np.array(v) for k, v in cols.items()},
                                              source_meta(cfg, []), cfg.conversion)
    return res


def build_ref_channels(cfg, out) -> dict:
    import blosc2
    wls = cfg.channel_wavelengths
    f = pd.read_csv(cfg.raw_path("optics_dir") / "ximea_filters.csv")
    f.columns = ["wl", "filter", "resp"]
    dark_p = cfg.raw_path("dark_reference")
    dark = blosc2.open(str(dark_p), mode="r")[:] if dark_p.exists() else None
    cc = pd.read_csv(cfg.raw_path("color_checker_dir") / "spectrometer_adapted.csv", usecols=["band", "wavelength"])
    cc_map = cc.drop_duplicates().set_index("band").wavelength.to_dict()
    rows = {k: [] for k in S.REF_CHANNELS.names}
    for ch in range(len(wls)):
        g = f[f["filter"] == ch + 1].sort_values("wl")
        w, r = g.wl.to_numpy(), g.resp.to_numpy()
        ip = int(np.argmax(r))
        half = r[ip] / 2
        lo = ip
        while lo > 0 and r[lo - 1] >= half:
            lo -= 1
        hi = ip
        while hi < len(r) - 1 and r[hi + 1] >= half:
            hi += 1
        outside = (w < w[lo] - 10) | (w > w[hi] + 10)
        rows["channel_index"].append(ch)
        rows["filter_id"].append(ch + 1)
        rows["nominal_wavelength_nm"].append(wls[ch])
        rows["peak_wavelength_nm"].append(int(w[ip]))
        rows["peak_response_au"].append(float(r[ip]))
        rows["centroid_wavelength_nm"].append(float((w * r).sum() / r.sum()))
        rows["fwhm_nm"].append(float(w[hi] - w[lo] + 1))
        rows["secondary_peak_ratio"].append(float(r[outside].max() / r[ip]) if outside.any() else 0.0)
        d = dark[..., ch] if dark is not None else np.array([np.nan])
        rows["dark_mean"].append(float(d.mean()))
        rows["dark_std"].append(float(d.std()))
        rows["dark_min"].append(float(d.min()))
        rows["dark_max"].append(float(d.max()))
        rows["colorchecker_band_wavelength_nm"].append(float(cc_map.get(ch, np.nan)))
    cols = {k: np.array(v, dtype=np.float64) if k == "colorchecker_band_wavelength_nm" else np.array(v)
            for k, v in rows.items()}
    meta = source_meta(cfg, [cfg.raw_path("optics_dir") / "ximea_filters.csv", dark_p,
                             cfg.raw_path("color_checker_dir") / "spectrometer_adapted.csv"],
                       {"pmhm.camera": cfg.raw["camera"]["model"],
                        "pmhm.dark_reference_shape": list(dark.shape) if dark is not None else None,
                        "pmhm.dark_reference_exposure_ms": "unknown (not stored in dark.b2nd)",
                        "pmhm.white_reference": "missing locally"})
    return write_small(out / "ref_channels.parquet", S.REF_CHANNELS, cols, meta, cfg.conversion)


def build_ref_stages(cfg, out, frames) -> dict:
    md = json.loads(cfg.raw_path("metadata_json").read_text())
    inv_map = {v: k for k, v in cfg.raw["spectrometer"]["stage_map"].items()}
    blocks = Counter()
    if frames:
        seq = next(iter(frames.values())).get("block_sequence", [])
        blocks = Counter(s for s, _ in seq)
    rows = {k: [] for k in S.REF_STAGES.names}
    for i, s in enumerate(md["stages"]):
        p, ph = parse_stage(s)
        rows["stage_order"].append(i)
        rows["stage"].append(s)
        rows["pressure_mmhg"].append(p)
        rows["phase"].append(ph)
        rows["spectrometer_stage_label"].append(inv_map.get(s))
        rows["blocks_per_session"].append(float(blocks[s]) if blocks else np.nan)
    cols = {k: (np.array(v, dtype=object) if k in ("stage", "phase", "spectrometer_stage_label")
                else np.array(v, dtype=np.float64 if k == "blocks_per_session" else None)) for k, v in rows.items()}
    return write_small(out / "ref_stages.parquet", S.REF_STAGES, cols,
                       source_meta(cfg, [cfg.raw_path("metadata_json")]), cfg.conversion)


def build_ref_subjects(cfg, out, subjects, frames, cubes, manifest) -> dict:
    md = json.loads(cfg.raw_path("metadata_json").read_text())
    ximea = cfg.raw_path("ximea_dir")
    rois = pq.read_table(out / "master_rois.parquet", columns=["subject_id", "roi_id"]).to_pandas()
    # row group = one (subject, stage, ROI) group -> count spectra per row group (bounded memory)
    sp = pq.ParquetFile(out / "master_spectrometer.parquet")
    nspec: Counter = Counter()
    for rg in range(sp.metadata.num_row_groups):
        t = sp.read_row_group(rg, columns=["subject_id", "stage", "spectrum_index"])
        key = (t["subject_id"][0].as_py(), t["stage"][0].as_py())
        nspec[key] += len(pa.compute.unique(t["spectrum_index"]))
    rows = {k: [] for k in S.REF_SUBJECTS.names}
    for s in sorted(md["subjects"]):
        if subjects and s not in subjects:
            continue
        stubs = sorted(ximea.glob(f"{s}.b2nd.synapse_download_*"))
        if s in cubes:
            status, cf, nb = "complete", cubes[s], cubes[s].stat().st_size
        elif stubs:
            status, cf, nb = "partial_download", stubs[0], stubs[0].stat().st_size
        else:
            status, cf, nb = "missing", None, np.nan
        f = frames.get(s)
        r_ids = sorted(rois[rois.subject_id == s].roi_id.unique().tolist())
        rows["subject_id"].append(s)
        rows["cube_status"].append(status)
        rows["cube_file"].append(cfg.rel(cf) if cf else None)
        rows["cube_bytes"].append(nb)
        rows["n_frames"].append(len(f["stage"]) if f else np.nan)
        rows["exposure_ms"].append(float(np.unique(f["exposure"])[0]) if f and len(np.unique(f["exposure"])) == 1
                                   else np.nan)
        rows["frame_rate_hz"].append(float(1 / np.median(np.diff(f["time_delta"]))) if f else np.nan)
        rows["duration_s"].append(float(f["time_delta"][-1]) if f else np.nan)
        rows["n_stage_blocks"].append(float(len(f.get("block_sequence", []))) if f else np.nan)
        rows["roi_ids_available"].append(",".join(map(str, r_ids)))
        rows["n_roi_rows"].append(int((rois.subject_id == s).sum()))
        rows["n_spectra_baseline"].append(int(nspec.get((s, "before_clamping"), 0)))
        rows["n_spectra_160mmHg"].append(int(nspec.get((s, "during_clamping_160mmHg"), 0)))
        rows["usable_roi_image_analysis"].append(status == "complete" and len(r_ids) > 0)
    strs = {"subject_id", "cube_status", "cube_file", "roi_ids_available"}
    cols = {k: np.array(v, dtype=object if k in strs else (bool if k == "usable_roi_image_analysis" else np.float64))
            for k, v in rows.items()}
    return write_small(out / "ref_subjects.parquet", S.REF_SUBJECTS, cols,
                       source_meta(cfg, [cfg.raw_path("metadata_json")]), cfg.conversion)


# ----------------------------------------------------------------------------- orchestration
def run_conversion(cfg: Config, out: Path, subjects: list[str] | None = None) -> dict:
    t0 = time.time()
    moved = preserve_existing(out, cfg.out_path("versions_dir"))
    if moved:
        log.info("previous output preserved at %s", moved)
    out.mkdir(parents=True, exist_ok=True)
    chunker = AdaptiveChunker(cfg.conversion)
    manifest: list[dict] = []
    tables: dict[str, dict] = {}
    log.info("conversion -> %s (subjects=%s) | %s", out, subjects or "all", snapshot(cfg.root))

    cubes = discover_cubes(cfg)
    frames = {s: load_frame_meta(p) for s, p in cubes.items() if not subjects or s in subjects}
    for s, p in cubes.items():
        if s in frames:
            manifest.append({"source": cfg.rel(p), "format": "b2nd(meta only)", "table": "master_frames",
                             "subject_id": s, "source_rows": len(frames[s]["stage"]),
                             "rows_written": len(frames[s]["stage"]), "status": "converted",
                             "notes": f"cube {tuple(frames[s]['shape'])} {frames[s]['dtype']} kept native"})

    tables["master_rois"] = convert_rois(cfg, out, subjects, frames, cubes, chunker, manifest)
    tables["master_frames"] = convert_frames(cfg, out, frames, cubes)
    tables["master_spectrometer"] = convert_spectrometer(cfg, out, subjects, chunker, manifest)
    tables.update(convert_optics_and_cc(cfg, out, chunker, manifest))
    tables["ref_channels"] = build_ref_channels(cfg, out)
    tables["ref_stages"] = build_ref_stages(cfg, out, frames)
    tables["ref_subjects"] = build_ref_subjects(cfg, out, subjects, frames, cubes, manifest)

    # sources intentionally NOT converted (kept native) — recorded so nothing is silently skipped
    for p in sorted(cfg.raw_path("ximea_dir").glob("*.synapse_download_*")) + \
            sorted(cfg.raw_path("color_checker_dir").glob("*.synapse_download_*")):
        manifest.append({"source": cfg.rel(p), "format": "partial", "table": None, "status": "skipped_incomplete_download"})
    for p in [cfg.raw_path("dark_reference")]:
        manifest.append({"source": cfg.rel(p), "format": "b2nd", "table": "ref_channels(summary stats)",
                         "status": "kept_native", "notes": "2-D calibration array; per-channel stats only"})

    mdir = out / "_manifest"
    mdir.mkdir(exist_ok=True)
    for name, info in tables.items():
        info["sha256"] = sha256_file(out / info["file"])
        spec = S.ALL_TABLES[name]
        info.update(grain=spec.grain, description=spec.description, primary_key=list(spec.primary_key),
                    columns=spec.names)
    man = pd.DataFrame(manifest)
    for c in man.columns:
        if man[c].dtype == object:
            man[c] = man[c].astype("string")
    pq.write_table(pa.Table.from_pandas(man, preserve_index=False), mdir / "conversion_manifest.parquet")
    man.to_csv(mdir / "conversion_manifest.csv", index=False)
    run = {"created_utc": utc_now(), "pipeline_version": __version__, "output_dir": cfg.rel(out),
           "subjects": subjects or "all", "elapsed_s": round(time.time() - t0, 1), "chunking": chunker.summary(),
           "resources_end": snapshot(cfg.root), "previous_version_moved_to": cfg.rel(moved) if moved else None,
           "tables": tables}
    (mdir / "catalog.json").write_text(json.dumps(run, indent=2, default=str))
    dd = pd.DataFrame([{"table": t.name, "column": c.name, "type": str(c.type), "nullable": c.nullable,
                        "unit": c.unit, "origin": c.origin, "description": c.description}
                       for t in S.ALL_TABLES.values() for c in t.columns])
    dd.to_csv(mdir / "data_dictionary.csv", index=False)
    log.info("conversion done in %.1fs | %s", time.time() - t0, snapshot(cfg.root))
    return run
