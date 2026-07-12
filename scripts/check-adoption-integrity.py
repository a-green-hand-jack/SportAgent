#!/usr/bin/env python3
"""Check that template adoption preserved baseline tracked file bytes."""
from __future__ import annotations

import argparse
import importlib.util
import json
import sys
from pathlib import Path


def load_adopter():
    script = Path(__file__).resolve().with_name("adopt-existing-repo.py")
    spec = importlib.util.spec_from_file_location("adopt_existing_repo", script)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"could not load {script}")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def main(argv: list[str]) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("target", type=Path)
    parser.add_argument("--json", action="store_true")
    args = parser.parse_args(argv)
    adopter = load_adopter()
    result = adopter.integrity_result(args.target.resolve())
    if args.json:
        print(json.dumps(result, indent=2, sort_keys=True))
    else:
        print(
            "[check-adoption-integrity] "
            + ("OK" if result["ok"] else "FAIL")
            + f" -- present {result['present']}/{result['baseline_files']}"
        )
        for row in result["missing"]:
            print(f"missing {row['path']}")
    return 0 if result["ok"] else 1


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
