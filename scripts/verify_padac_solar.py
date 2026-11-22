#!/usr/bin/env python
"""Verify the final 30-city, 435-pair solar-regeneration classification."""

from __future__ import annotations

import argparse
import itertools
import json
from pathlib import Path

import numpy as np
import pandas as pd


ROOT = Path(__file__).resolve().parents[1]


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--result-dir", type=Path, default=ROOT / "results/padac")
    parser.add_argument("--output", type=Path, default=ROOT / "results/padac/solar_pair_verification.json")
    args = parser.parse_args()
    files = sorted(args.result_dir.glob("*_primary_nz20.json"))
    if len(files) != 36:
        raise SystemExit(f"Need 36 city results; found {len(files)}")
    y_rows = []
    max_error = 0.0
    for path in files:
        row = json.loads(path.read_text(encoding="utf-8"))
        max_error = max(max_error, abs(row.get("Y_single_error", 0.0)), abs(row.get("Y_tensor_error", 0.0)))
        y_rows.extend([
            {"climate": row["city"], "representation": "single", "Y_recomputed": row["Y_single"]},
            {"climate": row["city"], "representation": "tensor", "Y_recomputed": row["Y_tensor"]},
        ])
    reference = pd.read_csv(ROOT / "data/frozen/ImCOF_wholeH_wholeY_aligned_climate_scores.csv")
    reference = reference.query("operating_mode == 'environmental_PADAC13X'")
    merged = reference.merge(pd.DataFrame(y_rows), on=["climate", "representation"], how="left", validate="one_to_one")
    table = merged.pivot(index="climate", columns="representation", values=["H_whole", "Y_recomputed"]).dropna().sort_index()
    counts = {"neither": 0, "H_only": 0, "Y_only": 0, "both": 0}
    for first, second in itertools.combinations(table.index, 2):
        h_product = np.sign(table.loc[first, ("H_whole", "single")] - table.loc[second, ("H_whole", "single")]) * np.sign(table.loc[first, ("H_whole", "tensor")] - table.loc[second, ("H_whole", "tensor")])
        y_product = np.sign(table.loc[first, ("Y_recomputed", "single")] - table.loc[second, ("Y_recomputed", "single")]) * np.sign(table.loc[first, ("Y_recomputed", "tensor")] - table.loc[second, ("Y_recomputed", "tensor")])
        if h_product == 0 or y_product == 0:
            raise AssertionError("Unexpected strict-order tie")
        label = "both" if h_product < 0 and y_product < 0 else "H_only" if h_product < 0 else "Y_only" if y_product < 0 else "neither"
        counts[label] += 1
    report = {
        "city_results": len(files),
        "evaluable_climates": len(table),
        "eligible_pairs": sum(counts.values()),
        **counts,
        "max_abs_city_Y_error": max_error,
        "claim_13_of_435_reproduced": len(table) == 30 and sum(counts.values()) == 435 and counts["Y_only"] == 13 and counts["both"] == 0,
    }
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(report, indent=2), encoding="utf-8")
    print(json.dumps(report, indent=2))
    if not report["claim_13_of_435_reproduced"]:
        raise SystemExit(1)


if __name__ == "__main__":
    main()
