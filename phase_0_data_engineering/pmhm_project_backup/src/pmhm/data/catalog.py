"""Primary access layer for the PMHM Parquet dataset (+ lazy access to the native .b2nd cubes).

    from pmhm.data.catalog import PMHMDataset, CubeReader
    ds = PMHMDataset()
    ds.tables()                                  # catalogue: rows, grain, primary key
    ds.describe("master_rois")                   # units / origin / description, read from the Parquet file
    rois = ds.load("master_rois", filters=[("subject_id", "==", "subject_01"), ("roi_id", "==", 1)])
    wide = ds.spectra(subject="subject_03", stage="before_clamping", roi=2, wide=True)
    cube = CubeReader("subject_01")
    patch = cube.roi_patch(frame_index=100, y1=158, x1=297, y2=178, x2=317)   # (20, 20, 16), decompresses ~1 block
"""
from __future__ import annotations

import json
from pathlib import Path

import numpy as np
import pandas as pd
import pyarrow.dataset as pads
import pyarrow.parquet as pq

from ..config import Config, load_config


class PMHMDataset:
    def __init__(self, parquet_dir: Path | str | None = None, cfg: Config | None = None):
        self.cfg = cfg or load_config()
        self.dir = Path(parquet_dir) if parquet_dir else self.cfg.out_path("parquet_dir")
        cat = self.dir / "_manifest" / "catalog.json"
        if not cat.exists():
            raise FileNotFoundError(f"{cat} missing — run scripts/pmhm_build_dataset.py convert")
        self.catalog = json.loads(cat.read_text())

    # --- discovery -------------------------------------------------------------------------
    def tables(self) -> pd.DataFrame:
        return pd.DataFrame([{"table": k, "rows": v["rows"], "grain": v["grain"],
                              "primary_key": ", ".join(v["primary_key"]), "file": v["file"], "bytes": v["bytes"]}
                             for k, v in self.catalog["tables"].items()])

    def path(self, table: str) -> Path:
        return self.dir / f"{table}.parquet"

    def describe(self, table: str) -> pd.DataFrame:
        """Column documentation read from the Parquet file itself (self-describing files)."""
        sch = pq.read_schema(self.path(table))
        return pd.DataFrame([{"column": f.name, "type": str(f.type), "nullable": f.nullable,
                              **{k.decode(): v.decode() for k, v in (f.metadata or {}).items()}} for f in sch])

    def table_metadata(self, table: str) -> dict:
        md = pq.read_schema(self.path(table)).metadata or {}
        out = {}
        for k, v in md.items():
            k = k.decode()
            if k.startswith("pmhm."):
                try:
                    out[k] = json.loads(v)
                except json.JSONDecodeError:
                    out[k] = v.decode()
        return out

    # --- loading ---------------------------------------------------------------------------
    def scan(self, table: str) -> pads.Dataset:
        return pads.dataset(self.path(table), format="parquet")

    def load(self, table: str, columns: list[str] | None = None, filters=None) -> pd.DataFrame:
        """Predicate push-down read (row groups are skipped via statistics)."""
        return pq.read_table(self.path(table), columns=columns, filters=filters).to_pandas()

    def subjects(self) -> pd.DataFrame:
        return self.load("ref_subjects")

    def rois(self, subject: str, roi: int | None = None, stage: str | None = None,
             with_frames_only: bool = True) -> pd.DataFrame:
        f = [("subject_id", "==", subject)]
        if roi is not None:
            f.append(("roi_id", "==", roi))
        if stage is not None:
            f.append(("stage", "==", stage))
        if with_frames_only:
            f.append(("has_image_frame", "==", True))
        return self.load("master_rois", filters=f)

    def spectra(self, subject: str | None = None, stage: str | None = None, roi: int | None = None,
                wide: bool = False) -> pd.DataFrame:
        f = [(c, "==", v) for c, v in (("subject_id", subject), ("stage", stage), ("roi_id", roi)) if v is not None]
        cols = ["subject_id", "stage", "roi_id", "spectrum_index", "wavelength_nm", "reflectance_au"]
        df = self.load("master_spectrometer", columns=cols, filters=f or None)
        if not wide:
            return df
        return df.pivot_table(index=["subject_id", "stage", "roi_id", "spectrum_index"],
                              columns="wavelength_nm", values="reflectance_au", aggfunc="first")


class CubeReader:
    """Lazy, read-only frame/ROI access to a subject's .b2nd cube. Never loads the full cube."""

    def __init__(self, subject: str, cfg: Config | None = None):
        import blosc2
        self.cfg = cfg or load_config()
        self.path = self.cfg.raw_path("ximea_dir") / f"{subject}.b2nd"
        if not self.path.exists():
            raise FileNotFoundError(f"{self.path} not available locally (see ref_subjects.cube_status)")
        self.arr = blosc2.open(str(self.path), mode="r")
        self.shape, self.dtype = self.arr.shape, self.arr.dtype
        self.wavelengths_nm = np.array(self.cfg.channel_wavelengths)
        self._dark = None

    def __len__(self) -> int:
        return self.shape[0]

    def frame(self, frame_index: int) -> np.ndarray:
        return self.arr[frame_index]

    def roi_patch(self, frame_index: int, y1: int, x1: int, y2: int, x2: int) -> np.ndarray:
        return self.arr[frame_index, y1:y2, x1:x2, :]

    def dark(self) -> np.ndarray:
        if self._dark is None:
            import blosc2
            self._dark = blosc2.open(str(self.cfg.raw_path("dark_reference")), mode="r")[:]
        return self._dark

    def roi_mean_spectrum(self, frame_index: int, y1: int, x1: int, y2: int, x2: int,
                          subtract_dark: bool = False) -> np.ndarray:
        """Mean raw counts per channel (channel order = cube order, see wavelengths_nm).

        White-reference normalisation is NOT applied: the white reference is not available locally, and the
        exposure of dark.b2nd is undocumented (see docs/TECHNICAL_DECISIONS.md).
        """
        p = self.roi_patch(frame_index, y1, x1, y2, x2).astype(np.float32)
        if subtract_dark:
            p = p - self.dark()[y1:y2, x1:x2, :].astype(np.float32)
        return p.reshape(-1, p.shape[-1]).mean(0)
