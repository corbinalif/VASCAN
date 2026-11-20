"""Memory / disk monitoring and adaptive chunk sizing."""
from __future__ import annotations

import logging
import shutil
from pathlib import Path

import psutil

log = logging.getLogger(__name__)
MB = 1024 * 1024


class ResourceAbort(RuntimeError):
    """Raised when available memory falls below the configured safety floor."""


def snapshot(path: Path | None = None) -> dict[str, float]:
    vm = psutil.virtual_memory()
    sw = psutil.swap_memory()
    proc = psutil.Process()
    out = {
        "ram_available_mb": round(vm.available / MB, 1),
        "ram_used_pct": vm.percent,
        "swap_used_mb": round(sw.used / MB, 1),
        "process_rss_mb": round(proc.memory_info().rss / MB, 1),
    }
    if path is not None:
        du = shutil.disk_usage(path)
        out["disk_free_gb"] = round(du.free / 1024**3, 1)
    return out


class AdaptiveChunker:
    """Chooses the next CSV chunk size from current memory pressure."""

    def __init__(self, cfg: dict):
        self.size = int(cfg["csv_chunk_rows"])
        self.min = int(cfg["min_chunk_rows"])
        self.max = int(cfg["max_chunk_rows"])
        self.shrink_mb = float(cfg["shrink_below_available_mb"])
        self.grow_mb = float(cfg["grow_above_available_mb"])
        self.abort_mb = float(cfg["abort_below_available_mb"])
        self.adjustments: list[tuple[int, int, float]] = []
        self.min_available_mb = float("inf")
        self.peak_rss_mb = 0.0

    def next_size(self) -> int:
        snap = snapshot()
        avail = snap["ram_available_mb"]
        self.min_available_mb = min(self.min_available_mb, avail)
        self.peak_rss_mb = max(self.peak_rss_mb, snap["process_rss_mb"])
        if avail < self.abort_mb:
            raise ResourceAbort(f"available RAM {avail} MB < abort floor {self.abort_mb} MB")
        old = self.size
        if avail < self.shrink_mb and self.size > self.min:
            self.size = max(self.min, self.size // 2)
        elif avail > self.grow_mb and self.size < self.max:
            self.size = min(self.max, self.size * 2)
        if self.size != old:
            self.adjustments.append((old, self.size, avail))
            log.info("chunk size %d -> %d (available %.0f MB)", old, self.size, avail)
        return self.size

    def summary(self) -> dict:
        return {
            "final_chunk_rows": self.size,
            "n_adjustments": len(self.adjustments),
            "adjustments": self.adjustments[:50],
            "min_available_mb": None if self.min_available_mb == float("inf") else self.min_available_mb,
            "peak_rss_mb": self.peak_rss_mb,
        }
