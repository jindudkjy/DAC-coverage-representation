#!/usr/bin/env python
"""Compare a reproduced CSV against its frozen reference by explicit keys."""

from __future__ import annotations

import argparse
from pathlib import Path

import pandas as pd

from dac_equilibrium.verification import compare_frames


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("actual", type=Path)
    parser.add_argument("expected", type=Path)
    parser.add_argument("--keys", nargs="+", required=True)
    parser.add_argument("--atol", type=float, default=1e-9)
    parser.add_argument("--rtol", type=float, default=1e-9)
    parser.add_argument("--report", type=Path)
    args = parser.parse_args()
    report = compare_frames(
        pd.read_csv(args.actual),
        pd.read_csv(args.expected),
        keys=args.keys,
        atol=args.atol,
        rtol=args.rtol,
    )
    if args.report:
        args.report.parent.mkdir(parents=True, exist_ok=True)
        report.to_csv(args.report, index=False)
    print(report.to_string(index=False))
    if not report.passed.all():
        raise SystemExit(1)


if __name__ == "__main__":
    main()

