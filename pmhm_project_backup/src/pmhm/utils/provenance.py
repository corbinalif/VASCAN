"""Hashing, versioned outputs and logging setup."""
from __future__ import annotations

import datetime as dt
import hashlib
import logging
import shutil
import sys
from pathlib import Path


def utc_now() -> str:
    return dt.datetime.now(dt.timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def stamp() -> str:
    return dt.datetime.now().strftime("%Y%m%d_%H%M%S")


def sha256_file(path: Path, bufsize: int = 4 * 1024 * 1024) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as fh:
        while chunk := fh.read(bufsize):
            h.update(chunk)
    return h.hexdigest()


def count_data_lines(path: Path) -> int:
    """Independent row count: newline count minus header (handles missing trailing newline)."""
    n = 0
    last = b"\n"
    with open(path, "rb") as fh:
        while chunk := fh.read(4 * 1024 * 1024):
            n += chunk.count(b"\n")
            last = chunk[-1:]
    if last != b"\n":
        n += 1
    return n - 1


def preserve_existing(out_dir: Path, versions_dir: Path) -> Path | None:
    """Move an existing output directory aside (never delete) before regenerating it."""
    if out_dir.exists() and any(out_dir.iterdir()):
        versions_dir.mkdir(parents=True, exist_ok=True)
        target = versions_dir / f"{out_dir.name}_{stamp()}"
        shutil.move(str(out_dir), str(target))
        return target
    return None


def setup_logging(log_dir: Path, name: str) -> Path:
    log_dir.mkdir(parents=True, exist_ok=True)
    path = log_dir / f"{name}_{stamp()}.log"
    fmt = logging.Formatter("%(asctime)s %(levelname)s %(name)s: %(message)s")
    root = logging.getLogger()
    root.setLevel(logging.INFO)
    for h in list(root.handlers):
        root.removeHandler(h)
    fh = logging.FileHandler(path)
    fh.setFormatter(fmt)
    sh = logging.StreamHandler(sys.stdout)
    sh.setFormatter(fmt)
    root.addHandler(fh)
    root.addHandler(sh)
    return path
