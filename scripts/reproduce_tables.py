#!/usr/bin/env python
"""Reproduce independently computable manuscript/SI tables."""

from __future__ import annotations

import argparse
import json
from pathlib import Path

import pandas as pd

from dac_equilibrium.metrics import pairwise_reversal_table
from dac_equilibrium.verification import compare_frames
from dac_equilibrium.weather_support import (
    cap_subzero_rh_at_ice_saturation,
    immediate_boundary_state_counts,
    lower_temperature_weather_summary,
    measurement_domain_extensions,
)


def reproduce_measurement_domain(input_dir: Path, output_dir: Path, atol: float) -> None:
    weather = pd.read_csv(input_dir / "MAIN_climate_hourly_2015_2024.csv")
    bounds = pd.read_csv(input_dir / "MAIN_material_support_bounds.csv")
    raw = pd.read_excel(
        input_dir / "MAIN_equilibrium_dataset_master.xlsx",
        sheet_name="06_RAW_QRHT",
        header=2,
    )
    table, stats = measurement_domain_extensions(weather, bounds, raw)
    table.to_csv(output_dir / "measurement_domain_extension_recomputed.csv", index=False, float_format="%.16g")
    table[["material", "branch", "T_low", "T_high", "RH_low", "RH_high"]].drop_duplicates().to_csv(
        output_dir / "measurement_support_branch_bounds_from_master.csv", index=False
    )
    reference_path = input_dir / "immediate_boundary_extension_coverage_native1h.csv"
    if reference_path.exists():
        audit = compare_frames(
            table,
            pd.read_csv(reference_path),
            keys=["material", "branch", "T_low", "T_high", "RH_low", "RH_high", "extension"],
            atol=atol,
            rtol=0,
        )
        audit.to_csv(output_dir / "measurement_domain_extension_regression.csv", index=False)
        if not audit.passed.all():
            raise AssertionError("Measurement-domain regression failed")
    (output_dir / "measurement_domain_stats.json").write_text(
        json.dumps(stats, indent=2), encoding="utf-8"
    )
    lower_temperature_weather_summary(weather).to_csv(
        output_dir / "lower_temperature_weather_distribution_recomputed.csv", index=False
    )
    immediate_boundary_state_counts(weather).to_csv(
        output_dir / "immediate_boundary_state_counts_recomputed.csv", index=False
    )
    ice_capped = weather.copy()
    ice_capped["RH_pct"] = cap_subzero_rh_at_ice_saturation(
        ice_capped["temperature_C"], ice_capped["RH_pct"]
    )
    capped_table, _ = measurement_domain_extensions(ice_capped, bounds, raw)
    capped_table.to_csv(
        output_dir / "measurement_domain_extension_ice_capped_recomputed.csv",
        index=False,
        float_format="%.16g",
    )


def reproduce_ira_pairs(input_dir: Path, output_dir: Path, atol: float) -> None:
    scores = pd.read_csv(input_dir / "IRA_environmental_common_support_climate_scores.csv")
    summaries = []
    all_pairs = []
    for (branch, support), group in scores.groupby(["branch", "support_treatment"], sort=True):
        pairs, summary = pairwise_reversal_table(group)
        pairs.insert(0, "support_treatment", support)
        pairs.insert(0, "branch", branch)
        summary.update({"branch": branch, "support_treatment": support})
        all_pairs.append(pairs)
        summaries.append(summary)
    pair_table = pd.concat(all_pairs, ignore_index=True)
    summary_table = pd.DataFrame(summaries)
    pair_table.to_csv(output_dir / "IRA_shared_support_pairwise_recomputed_pairs.csv", index=False)
    summary_table.to_csv(output_dir / "IRA_shared_support_pairwise_recomputed_summary.csv", index=False)
    reference_path = input_dir / "IRA_environmental_common_support_transfer_summary.csv"
    if reference_path.exists():
        audit = compare_frames(
            summary_table,
            pd.read_csv(reference_path),
            keys=["branch", "support_treatment"],
            atol=atol,
            rtol=0,
        )
        audit.to_csv(output_dir / "IRA_shared_support_pairwise_regression.csv", index=False)
        if not audit.passed.all():
            raise AssertionError("IRA pairwise regression failed")


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--input-dir", type=Path, required=True)
    parser.add_argument("--output-dir", type=Path, default=Path("results"))
    parser.add_argument(
        "--target",
        choices=("all", "coverage", "measurement-domain", "ira-pairs"),
        default="all",
    )
    parser.add_argument("--atol", type=float, default=1e-9)
    args = parser.parse_args()
    args.output_dir.mkdir(parents=True, exist_ok=True)
    if args.target in {"all", "coverage", "measurement-domain"}:
        reproduce_measurement_domain(args.input_dir, args.output_dir, args.atol)
    if args.target in {"all", "ira-pairs"}:
        reproduce_ira_pairs(args.input_dir, args.output_dir, args.atol)


if __name__ == "__main__":
    main()

