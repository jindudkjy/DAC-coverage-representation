#!/usr/bin/env python
"""Reproduce SI Table S6 and Figure 3b source data from the 2,826-row H/N panel."""

from __future__ import annotations

import argparse
import json
from pathlib import Path

import pandas as pd

from dac_equilibrium.metrics import summarize_transition_normalized_scores


ROOT = Path(__file__).resolve().parents[1]


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--input-file",
        type=Path,
        default=ROOT / "data/frozen/MAIN_climate_H_scores.csv",
    )
    parser.add_argument("--output-dir", type=Path, default=ROOT / "results/tables")
    parser.add_argument("--expected-rows", type=int, default=2826)
    args = parser.parse_args()

    raw = pd.read_csv(args.input_file)
    if args.expected_rows and len(raw) != args.expected_rows:
        raise AssertionError(
            f"Expected {args.expected_rows} location rows, found {len(raw)}"
        )
    panel, by_material, summary = summarize_transition_normalized_scores(raw)
    if len(by_material) != 108:
        raise AssertionError(f"Expected 108 material panels, found {len(by_material)}")
    if not (summary["n_materials"] == 9).all():
        raise AssertionError("Every branch/temporal summary must contain nine materials")

    args.output_dir.mkdir(parents=True, exist_ok=True)
    panel.to_csv(
        args.output_dir / "MAIN_climate_HN_scores_recomputed.csv",
        index=False,
        float_format="%.16g",
    )
    by_material.to_csv(
        args.output_dir / "Table_S6_HN_by_material_recomputed.csv",
        index=False,
        float_format="%.16g",
    )
    summary.to_csv(
        args.output_dir / "Table_S6_HN_summary_recomputed.csv",
        index=False,
        float_format="%.16g",
    )
    audit = {
        "input_file": str(args.input_file),
        "location_rows": len(panel),
        "material_panels": len(by_material),
        "summary_rows": len(summary),
        "materials": sorted(panel["material"].unique().tolist()),
        "branches": sorted(panel["branch"].unique().tolist()),
        "temporal_modes": sorted(panel["temporal_mode"].unique().tolist()),
        "definition": "H_per_transition = H / N",
        "partial_tau_definition": (
            "(tau_xy - tau_xN*tau_yN) / "
            "sqrt((1-tau_xN^2)*(1-tau_yN^2))"
        ),
    }
    (args.output_dir / "Table_S6_HN_validation.json").write_text(
        json.dumps(audit, indent=2), encoding="utf-8"
    )
    print(json.dumps(audit))


if __name__ == "__main__":
    main()
