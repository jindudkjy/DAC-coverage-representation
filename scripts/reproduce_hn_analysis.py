#!/usr/bin/env python
"""Compatibility CLI for the canonical ``n_controlled_ordering.py`` path."""

from __future__ import annotations

import argparse
import json
from pathlib import Path

import pandas as pd

from n_controlled_ordering import write_outputs as write_n_controlled_outputs
from dac_equilibrium.metrics import transition_normalized_scores


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
    parser.add_argument("--permutations", type=int, default=3000)
    parser.add_argument("--seed", type=int, default=0)
    args = parser.parse_args()

    raw = pd.read_csv(args.input_file)
    if args.expected_rows and len(raw) != args.expected_rows:
        raise AssertionError(
            f"Expected {args.expected_rows} location rows, found {len(raw)}"
        )
    panel = transition_normalized_scores(raw)
    args.output_dir.mkdir(parents=True, exist_ok=True)
    by_material, summary, figure = write_n_controlled_outputs(
        raw,
        args.output_dir / "N_controlled_ordering_by_case.csv",
        args.output_dir / "SI_Table_S6_N_controlled_summary.csv",
        args.output_dir / "Fig3_source_data.csv",
        n_reassignments=args.permutations,
        seed=args.seed,
    )
    if len(by_material) != 108:
        raise AssertionError(f"Expected 108 material panels, found {len(by_material)}")
    if len(summary) != 12:
        raise AssertionError(f"Expected 12 Table S6 rows, found {len(summary)}")

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
    figure.to_csv(
        args.output_dir / "Figure_3b_source_data_recomputed.csv",
        index=False,
        float_format="%.16g",
    )
    permutation_overall = {}
    for branch, group in by_material.groupby("br"):
        permutation_overall[branch] = {
            "median_random_reassignment_fraction": float(
                group["perm_HN"].median()
            ),
            "materials_below_random_q025": int(
                group["below_HN"].sum()
            ),
        }
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
        "permutation_reassignments": args.permutations,
        "permutation_seed": args.seed,
        "permutation_order": "sorted material/branch/temporal case; H draws then H/N draws",
        "permutation_overall_by_branch": permutation_overall,
    }
    (args.output_dir / "Table_S6_HN_validation.json").write_text(
        json.dumps(audit, indent=2), encoding="utf-8"
    )
    print(json.dumps(audit))


if __name__ == "__main__":
    main()
