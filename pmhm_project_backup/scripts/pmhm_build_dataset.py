#!/usr/bin/env python
"""PMHM dataset build CLI.

    python scripts/pmhm_build_dataset.py inventory
    python scripts/pmhm_build_dataset.py convert --pilot subject_01
    python scripts/pmhm_build_dataset.py convert
    python scripts/pmhm_build_dataset.py validate [--pilot subject_01]
    python scripts/pmhm_build_dataset.py standalone   # build + validate data/processed/spectralpaca_pmhm_dataset.parquet
    python scripts/pmhm_build_dataset.py card         # regenerate docs/DATASET_CARD.md + DATA_DICTIONARY.md
    python scripts/pmhm_build_dataset.py all          # inventory -> pilot -> validate -> full -> validate -> card
"""
from __future__ import annotations

import argparse
import json
import logging
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from pmhm.config import load_config  # noqa: E402
from pmhm.utils.provenance import setup_logging  # noqa: E402
from pmhm.utils.resources import snapshot  # noqa: E402

log = logging.getLogger("pmhm.cli")


def out_dir(cfg, pilot: str | None) -> Path:
    if pilot:
        return cfg.p(cfg.raw["outputs"]["pilot_dir_template"].format(subject=pilot))
    return cfg.out_path("parquet_dir")


def cmd_inventory(cfg, args):
    from pmhm.data.inventory import build_inventory, save_inventory, write_inventory_markdown
    inv, summary = build_inventory(cfg)
    save_inventory(inv, summary, cfg.out_path("processed_dir") / "manifests")
    write_inventory_markdown(inv, summary, cfg.root / "docs" / "DATASET_FILE_INVENTORY.md")
    log.info("inventory: %d files, %.1f GB", summary["n_files"], summary["total_bytes"] / 1024**3)


def cmd_convert(cfg, args):
    from pmhm.data.convert import run_conversion
    res = run_conversion(cfg, out_dir(cfg, args.pilot), subjects=[args.pilot] if args.pilot else None)
    log.info("conversion finished: %s", json.dumps({k: v["rows"] for k, v in res["tables"].items()}))


def cmd_validate(cfg, args):
    from pmhm.data.validate import run_validation
    rep = run_validation(cfg, out_dir(cfg, args.pilot), subjects=[args.pilot] if args.pilot else None)
    log.info("validation: %d checks, %d failed", rep["n_checks"], rep["n_failed"])
    return 0 if rep["n_failed"] == 0 else 2


def cmd_standalone(cfg, args):
    from pmhm.data.standalone import build_standalone, validate_standalone
    info = build_standalone(cfg)
    rep = validate_standalone(cfg, info)
    log.info("standalone validation: %d checks, %d failed, %d warnings", rep["n_checks"], rep["n_failed"], rep["n_warn"])
    from pmhm.data.card import write_standalone_doc
    write_standalone_doc(cfg, cfg.root / "docs" / "STANDALONE_DATASET.md")
    return 0 if rep["n_failed"] == 0 else 2


def cmd_card(cfg, args):
    from pmhm.data.card import write_data_dictionary, write_dataset_card
    from pmhm.data.catalog import PMHMDataset
    ds = PMHMDataset(cfg=cfg)
    write_dataset_card(ds, cfg.root / "docs" / "DATASET_CARD.md", cfg.root / "projectproposal.md")
    write_data_dictionary(ds, cfg.root / "docs" / "DATA_DICTIONARY.md")
    from pmhm.data.card import write_standalone_doc
    write_standalone_doc(cfg, cfg.root / "docs" / "STANDALONE_DATASET.md")
    log.info("dataset card + data dictionary written to docs/")


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("command", choices=["inventory", "convert", "validate", "standalone", "card", "all"])
    ap.add_argument("--pilot", metavar="SUBJECT", help="restrict to one subject; writes to the pilot directory")
    ap.add_argument("--config", default=None)
    args = ap.parse_args()
    cfg = load_config(args.config)
    logfile = setup_logging(cfg.out_path("logs_dir"), f"pmhm_{args.command}{'_pilot' if args.pilot else ''}")
    log.info("start %s | resources %s | log %s", args.command, snapshot(cfg.root), logfile)
    rc = 0
    if args.command == "inventory":
        cmd_inventory(cfg, args)
    elif args.command == "convert":
        cmd_convert(cfg, args)
    elif args.command == "validate":
        rc = cmd_validate(cfg, args)
    elif args.command == "standalone":
        rc = cmd_standalone(cfg, args)
    elif args.command == "card":
        cmd_card(cfg, args)
    else:
        cmd_inventory(cfg, args)
        pilot = argparse.Namespace(pilot=args.pilot or "subject_01")
        cmd_convert(cfg, pilot)
        if cmd_validate(cfg, pilot) != 0:
            log.error("pilot validation failed — full conversion NOT started")
            return 2
        full = argparse.Namespace(pilot=None)
        cmd_convert(cfg, full)
        rc = cmd_validate(cfg, full)
        if rc == 0:
            rc = cmd_standalone(cfg, full)
        cmd_card(cfg, full)
    log.info("end %s | resources %s", args.command, snapshot(cfg.root))
    return rc


if __name__ == "__main__":
    sys.exit(main())
