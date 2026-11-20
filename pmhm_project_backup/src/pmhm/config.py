"""Configuration loading and path resolution."""
from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any

import yaml

PROJECT_ROOT = Path(__file__).resolve().parents[2]
DEFAULT_CONFIG = PROJECT_ROOT / "configs" / "pmhm.yaml"


@dataclass
class Config:
    raw: dict[str, Any]
    path: Path

    @property
    def root(self) -> Path:
        return Path(self.raw["dataset_root"])

    def p(self, rel: str) -> Path:
        """Resolve a dataset-relative path."""
        q = Path(rel)
        return q if q.is_absolute() else self.root / q

    def raw_path(self, key: str) -> Path:
        return self.p(self.raw["raw"][key])

    def out_path(self, key: str) -> Path:
        return self.p(self.raw["outputs"][key])

    @property
    def conversion(self) -> dict[str, Any]:
        return self.raw["conversion"]

    @property
    def channel_wavelengths(self) -> list[int]:
        return list(self.raw["camera"]["channel_wavelengths_nm"])

    def rel(self, path: Path) -> str:
        """Path relative to dataset root (for provenance columns)."""
        try:
            return str(Path(path).resolve().relative_to(self.root.resolve()))
        except ValueError:
            return str(path)


def load_config(path: Path | str | None = None) -> Config:
    path = Path(path) if path else DEFAULT_CONFIG
    with open(path) as fh:
        return Config(raw=yaml.safe_load(fh), path=path)
