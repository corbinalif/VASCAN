"""Stage label parsing and session-timeline (block) derivation."""
from __future__ import annotations

import re
from collections.abc import Sequence

import numpy as np

_DURING = re.compile(r"^during_clamping_(\d+)mmHg$")
_SPEC_P = re.compile(r"^(\d+) mmHg$")
_SUBJ = re.compile(r"^subject[ _](\d+)$")


def parse_stage(label: str) -> tuple[int, str]:
    """Return (pressure_mmhg, phase) for a cube/ROI stage label."""
    if label == "before_clamping":
        return 0, "baseline"
    m = _DURING.match(label)
    if not m:
        raise ValueError(f"unrecognised stage label: {label!r}")
    p = int(m.group(1))
    return p, ("rest" if p == 0 else "clamping")


def harmonise_spectrometer_stage(label: str, stage_map: dict[str, str]) -> str:
    if label in stage_map:
        return stage_map[label]
    m = _SPEC_P.match(label)
    if m:
        return f"during_clamping_{int(m.group(1))}mmHg"
    raise ValueError(f"unrecognised spectrometer stage label: {label!r}")


def canonical_subject(label: str) -> str:
    m = _SUBJ.match(label.strip())
    if not m:
        raise ValueError(f"unrecognised subject label: {label!r}")
    return f"subject_{int(m.group(1)):02d}"


class BlockTracker:
    """Stateful run-length segmentation of an ordered stage sequence.

    Works across chunk boundaries: call ``update`` repeatedly with consecutive slices.
    """

    def __init__(self) -> None:
        self.last_stage: str | None = None
        self.block = -1
        self.block_start = 0.0
        self.cur_pressure = 0
        self.prev_block_pressure: int | None = None
        self.block_sequence: list[tuple[str, int]] = []  # (stage, n_rows)

    def update(self, stages: Sequence[str], times: np.ndarray):
        n = len(stages)
        block = np.empty(n, np.int16)
        prev_p = np.empty(n, np.float64)  # NaN encodes null
        t_in = np.empty(n, np.float64)
        pressure = np.empty(n, np.int16)
        phase: list[str] = [""] * n
        cache: dict[str, tuple[int, str]] = {}
        for i, (s, t) in enumerate(zip(stages, times)):
            if s != self.last_stage:
                if self.last_stage is not None:
                    self.prev_block_pressure = self.cur_pressure
                p, _ = cache.setdefault(s, parse_stage(s))
                self.block += 1
                self.block_start = float(t)
                self.cur_pressure = p
                self.last_stage = s
                self.block_sequence.append((s, 0))
            p, ph = cache.setdefault(s, parse_stage(s))
            st, cnt = self.block_sequence[-1]
            self.block_sequence[-1] = (st, cnt + 1)
            block[i] = self.block
            pressure[i] = p
            phase[i] = ph
            t_in[i] = float(t) - self.block_start
            prev_p[i] = (self.prev_block_pressure if (ph == "rest" and self.prev_block_pressure is not None)
                         else np.nan)
        return {"pressure_mmhg": pressure, "phase": phase, "stage_block_index": block,
                "preceding_pressure_mmhg": prev_p, "time_in_block_s": t_in}

