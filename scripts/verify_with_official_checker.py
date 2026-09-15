"""Run an unmodified official checker executable for one model/solution triple."""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

from gmrp_alns.gmrp.checker import run_official_checker


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("checker", type=Path)
    parser.add_argument("model", type=Path)
    parser.add_argument("initial", type=Path)
    parser.add_argument("solution", type=Path)
    args = parser.parse_args()
    result = run_official_checker(args.checker, args.model, args.initial, args.solution)
    sys.stdout.write(result.stdout)
    sys.stderr.write(result.stderr)
    return result.returncode


if __name__ == "__main__":
    raise SystemExit(main())

