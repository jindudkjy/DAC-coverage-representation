#!/usr/bin/env python
"""Reproduce independently computable manuscript/SI tables."""

from __future__ import annotations

import argparse
import json
from pathlib import Path

import pandas as pd

from n_controlled_ordering import write_outputs as write_n_controlled_outputs
from dac_equilibrium.h_panel import reconstruct_h_panel
from dac_equilibrium.metrics import pairwise_reversal_table, transition_normalized_scores
from dac_equilibrium.verification import compare_frames
from dac_equilibrium.weather_support import (
    cap_subzero_rh_at_ice_saturation,
    immediate_boundary_state_counts,
    lower_temperature_weather_summary,
    measurement_domain_extensions,
)


def reproduce_measurement_domain(
    input_dir: Path,
    output_dir: Path,
    atol: float,
    weather_file: Path,
    bounds_file: Path,
    equilibrium_file: Path,
) -> None:
    weather = pd.read_csv(weather_file)
    bounds = pd.read_csv(bounds_file)
    raw = pd.read_excel(
        equilibrium_file,
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


def reproduce_hn(source: Path, output_dir: Path, permutations: int, seed: int) -> None:
    raw = pd.read_csv(source)
    panel = transition_normalized_scores(raw)
    by_material, summary, figure = write_n_controlled_outputs(
        raw,
        output_dir / "N_controlled_ordering_by_case.csv",
        output_dir / "SI_Table_S6_N_controlled_summary.csv",
        output_dir / "Fig3_source_data.csv",
        n_reassignments=permutations,
        seed=seed,
    )
    if len(panel) != 2826 or len(by_material) != 108:
        raise AssertionError(
            f"Unexpected H/N panel dimensions: {len(panel)} rows, {len(by_material)} groups"
        )
    panel.to_csv(output_dir / "MAIN_climate_HN_scores_recomputed.csv", index=False, float_format="%.16g")
    # Compatibility aliases retained for earlier public-repository commands.
    by_material.to_csv(output_dir / "Table_S6_HN_by_material_recomputed.csv", index=False, float_format="%.16g")
    summary.to_csv(output_dir / "Table_S6_HN_summary_recomputed.csv", index=False, float_format="%.16g")
    figure.to_csv(output_dir / "Figure_3b_source_data_recomputed.csv", index=False, float_format="%.16g")


def reproduce_h_panel(
    weather_file: Path,
    equilibrium_file: Path,
    bounds_file: Path,
    reference_file: Path,
    output_dir: Path,
    atol: float,
) -> Path:
    panel = reconstruct_h_panel(weather_file, equilibrium_file, bounds_file)
    output = output_dir / "MAIN_climate_H_scores_recomputed.csv"
    panel.to_csv(output, index=False, float_format="%.16g")
    if len(panel) != 2826:
        raise AssertionError(f"Expected 2,826 H-panel rows, found {len(panel)}")
    if reference_file.exists():
        audit = compare_frames(
            panel,
            pd.read_csv(reference_file),
            keys=["material", "branch", "temporal_mode", "climate_class", "city"],
            atol=atol,
            rtol=0,
        )
        audit.to_csv(output_dir / "MAIN_climate_H_scores_regression.csv", index=False)
        if not audit.passed.all():
            raise AssertionError("Raw-input H-panel regression failed")
    return output


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--input-dir", type=Path, required=True)
    parser.add_argument("--output-dir", type=Path, default=Path("results"))
    parser.add_argument(
        "--target",
        choices=(
            "all",
            "coverage",
            "measurement-domain",
            "h-panel",
            "h-to-hn",
            "hn",
            "ira-pairs",
        ),
        default="all",
    )
    root = Path(__file__).resolve().parents[1]
    parser.add_argument(
        "--weather-file",
        type=Path,
        default=root / "data/weather/MAIN_climate_hourly_2015_2024.csv",
    )
    parser.add_argument(
        "--bounds-file",
        type=Path,
        default=root / "data/equilibrium/MAIN_material_support_bounds.csv",
    )
    parser.add_argument(
        "--equilibrium-file",
        type=Path,
        default=root / "data/equilibrium/MAIN_equilibrium_dataset_master.xlsx",
    )
    parser.add_argument("--atol", type=float, default=1e-9)
    parser.add_argument("--permutations", type=int, default=3000)
    parser.add_argument("--seed", type=int, default=0)
    args = parser.parse_args()
    args.output_dir.mkdir(parents=True, exist_ok=True)
    if args.target in {"all", "coverage", "measurement-domain"}:
        reproduce_measurement_domain(
            args.input_dir,
            args.output_dir,
            args.atol,
            args.weather_file,
            args.bounds_file,
            args.equilibrium_file,
        )
    h_panel_source = args.input_dir / "MAIN_climate_H_scores.csv"
    if args.target in {"all", "h-panel", "h-to-hn"}:
        h_panel_source = reproduce_h_panel(
            args.weather_file,
            args.equilibrium_file,
            args.bounds_file,
            args.input_dir / "MAIN_climate_H_scores.csv",
            args.output_dir,
            args.atol,
        )
    if args.target in {"all", "h-to-hn", "hn"}:
        reproduce_hn(h_panel_source, args.output_dir, args.permutations, args.seed)
    if args.target in {"all", "ira-pairs"}:
        reproduce_ira_pairs(args.input_dir, args.output_dir, args.atol)


if __name__ == "__main__":
    main()

