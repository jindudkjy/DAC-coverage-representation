#!/usr/bin/env python
"""Create source-data verification plots for final manuscript Figures 2-7."""

from __future__ import annotations

import argparse
from pathlib import Path

import numpy as np
import pandas as pd

from dac_equilibrium.metrics import summarize_transition_normalized_scores
from dac_equilibrium.weather_support import ice_saturation_rh_percent


def _read(input_dir: Path, stem: str) -> pd.DataFrame:
    path = input_dir / f"{stem}.csv"
    if not path.exists():
        fallback = Path(__file__).resolve().parents[1] / "data" / "reference" / path.name
        if fallback.exists():
            path = fallback
        else:
            raise FileNotFoundError(path)
    return pd.read_csv(path)


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--input-dir", type=Path, required=True)
    parser.add_argument("--output-dir", type=Path, default=Path("results/figures"))
    parser.add_argument(
        "--weather-file",
        type=Path,
        help="Hourly weather CSV for Figure 2; defaults to INPUT_DIR/MAIN_climate_hourly_2015_2024.csv",
    )
    args = parser.parse_args()

    import matplotlib

    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    from matplotlib.colors import LogNorm
    from matplotlib.patches import Rectangle

    args.output_dir.mkdir(parents=True, exist_ok=True)
    plt.rcParams.update(
        {
            "font.size": 9,
            "axes.spines.top": False,
            "axes.spines.right": False,
            "figure.dpi": 150,
            "savefig.dpi": 200,
        }
    )
    manifest: list[dict[str, object]] = []

    def save(number: int, figure, sources: list[str], note: str) -> None:
        filename = f"Fig{number}_numerical_reconstruction.png"
        figure.savefig(args.output_dir / filename, bbox_inches="tight")
        plt.close(figure)
        manifest.append(
            {
                "figure": number,
                "output": filename,
                "source_files": "; ".join(sources),
                "status": "NUMERICAL_REPLOT_NOT_PIXEL_IDENTICAL_ARTWORK",
                "note": note,
            }
        )

    # Figure 2: pooled weather-state distribution and lower measured domains.
    weather_path = args.weather_file or args.input_dir / "MAIN_climate_hourly_2015_2024.csv"
    weather = pd.read_csv(weather_path, usecols=["temperature_C", "RH_pct"])
    weather = weather.replace([np.inf, -np.inf], np.nan).dropna()
    domains = [(-20, -5, 70), (-20, 5, 70), (-20, 5, 80)]
    figure, axes = plt.subplots(1, 3, figsize=(12.3, 3.8), sharex=True, sharey=True)
    for label, axis, (low, high, rh_high) in zip("abc", axes, domains):
        axis.hist2d(
            weather.temperature_C,
            weather.RH_pct,
            bins=(150, 100),
            range=((-30, 15), (0, 100)),
            norm=LogNorm(vmin=1),
            cmap="Greys",
        )
        axis.add_patch(Rectangle((low, 0), high - low, rh_high, fill=False, ec="#1f77b4", lw=1.6))
        axis.add_patch(Rectangle((low, rh_high), high - low, 5, fc="#1f77b4", alpha=0.25, ec="none"))
        axis.add_patch(Rectangle((low - 5, 0), 5, rh_high, fill=False, hatch="////", ec="#e07a1f", lw=1.0))
        temperature = np.linspace(-30, 0, 200)
        axis.plot(temperature, ice_saturation_rh_percent(temperature), "--", color="0.2", lw=1)
        axis.set(title=f"({label}) {low} to {high} degC, 0-{rh_high}% RH", xlabel="Temperature (degC)")
    axes[0].set_ylabel("Water-referenced RH (%)")
    figure.suptitle("Figure 2 numerical reconstruction: pooled lower-temperature weather states")
    figure.tight_layout()
    save(2, figure, [weather_path.name], "Density map with measured domains and extension bands.")

    # Figure 3: representation effect on H magnitude, ordering, and H/N.
    data = _read(args.input_dir, "MAIN_magnitude_rank_fidelity_panel_summary")
    hn_panel = _read(args.input_dir, "MAIN_climate_H_scores")
    _, _, hn_summary = summarize_transition_normalized_scores(hn_panel)
    hn_summary.to_csv(
        args.output_dir / "Fig3b_HN_summary_recomputed.csv",
        index=False,
        float_format="%.16g",
    )
    figure, axes = plt.subplots(1, 2, figsize=(12.2, 4.5))
    axis = axes[0]
    for branch, group in data.groupby("branch"):
        axis.scatter(
            group.median_relative_H_error,
            group.median_kendall_tau,
            label=branch,
            marker={"lower": "o", "upper": "s"}[branch],
            s=60,
        )
        for row in group.itertuples():
            label = row.temporal_mode.replace("subsample_", "").replace("average_", "avg")
            axis.annotate(label, (row.median_relative_H_error, row.median_kendall_tau), fontsize=7, xytext=(3, 3), textcoords="offset points")
    lower_native = data.query("branch == 'lower' and temporal_mode == 'subsample_1h'").iloc[0]
    axis.axvline(lower_native.median_relative_H_error, color="0.5", ls="--", lw=0.8)
    axis.axhline(lower_native.median_kendall_tau, color="0.5", ls="--", lw=0.8)
    axis.set(
        xlabel="Median relative H difference",
        ylabel="Median Kendall tau",
        title="(a) H magnitude and ordering",
    )
    axis.legend()

    temporal_modes = [
        "subsample_1h", "subsample_3h", "subsample_6h",
        "subsample_24h", "average_6h", "average_24h",
    ]
    labels = ["1 h", "3 h", "6 h", "24 h", "6 h avg", "24 h avg"]
    positions = np.arange(len(temporal_modes))
    colors = {"lower": "#1f77b4", "upper": "#d62728"}
    for branch in ("lower", "upper"):
        group = hn_summary.query("branch == @branch").set_index("temporal_mode").loc[temporal_modes]
        axes[1].plot(
            positions,
            group["median_tau_H_single_tensor"],
            marker="o",
            color=colors[branch],
            label=f"{branch}: H",
        )
        axes[1].plot(
            positions,
            group["median_tau_H_over_N_single_tensor"],
            marker="s",
            linestyle="--",
            color=colors[branch],
            label=f"{branch}: H/N",
        )
    axes[1].set_xticks(positions, labels, rotation=30, ha="right")
    axes[1].set(
        ylabel="Median Kendall tau",
        title="(b) Ordering before and after transition normalization",
        ylim=(0.5, 1.01),
    )
    axes[1].legend(fontsize=7, ncol=2)
    figure.suptitle("Figure 3 numerical reconstruction")
    figure.tight_layout()
    save(
        3,
        figure,
        ["MAIN_magnitude_rank_fidelity_panel_summary.csv", "MAIN_climate_H_scores.csv"],
        "Panel (b) is independently recomputed from all 2,826 location-level H and N rows.",
    )

    # Figure 4: correction size and pairwise ordering consequences.
    correction = _read(args.input_dir, "SI_temperature_correction_family_summary")
    baseline = correction.query("margin_filter == 0").sort_values("family_primary")
    filtered = correction.query("margin_filter == 0.05").set_index("family_primary")
    figure, axes = plt.subplots(1, 2, figsize=(11.0, 4.5))
    axes[0].bar(baseline.family_primary, baseline.median_C_rel_Hbar, color="#4c78a8")
    axes[0].set(ylabel="Median |C| / pair-mean H", title="(a) Correction magnitude")
    positions = np.arange(len(baseline))
    width = 0.25
    axes[1].bar(positions - width, baseline.frac_margin_threat, width, label="|C| exceeds separation")
    axes[1].bar(positions, baseline.reversal_fraction, width, label="Reversal")
    axes[1].bar(
        positions + width,
        [filtered.loc[name, "reversal_fraction"] for name in baseline.family_primary],
        width,
        label="Reversal after 5% near-tie filter",
    )
    axes[0].tick_params(axis="x", rotation=55)
    axes[1].set_xticks(positions, baseline.family_primary, rotation=55, ha="right")
    axes[1].set(ylabel="Fraction of location pairs", title="(b) Ordering consequence")
    axes[1].legend(fontsize=7)
    figure.suptitle("Figure 4 numerical reconstruction")
    figure.tight_layout()
    save(4, figure, ["SI_temperature_correction_family_summary.csv"], "Family-level pairwise summaries.")

    # Figure 5: RH-response categories and category-C delta-rho.
    counts = _read(args.input_dir, "MAIN_rh_response_category_counts")
    bootstrap = _read(args.input_dir, "SI_rh_null_classC_bootstrap").sort_values("delta_rho_tensor").reset_index(drop=True)
    figure, axes = plt.subplots(1, 2, figsize=(11.2, 4.4))
    axes[0].bar(counts.category, counts.n_cases, color=["#4c78a8", "#f2cf5b", "#e45756"])
    axes[0].set(xlabel="Mechanism category", ylabel="Comparison cases", title="(a) A/B/C classification")
    x = np.arange(len(bootstrap))
    yerr = np.vstack(
        [bootstrap.delta_rho_tensor - bootstrap.delta_rho_lo, bootstrap.delta_rho_hi - bootstrap.delta_rho_tensor]
    )
    axes[1].errorbar(x, bootstrap.delta_rho_tensor, yerr=yerr, fmt="o", ms=2.5, lw=0.6, color="#4c78a8", ecolor="0.65")
    axes[1].axhline(0, color="0.3", lw=0.8)
    axes[1].set(xlabel="Category-C cases sorted by delta rho", ylabel="delta rho", title="(b) Material-specific RH information")
    figure.suptitle("Figure 5 numerical reconstruction")
    figure.tight_layout()
    save(5, figure, ["MAIN_rh_response_category_counts.csv", "SI_rh_null_classC_bootstrap.csv"], "Observed values and percentile ranges.")

    # Figure 6: prescribed LDF response-time sensitivity.
    kinetic = _read(args.input_dir, "SI_kinetic_rank_summary").query("Ea_kJmol == 0")
    figure, axes = plt.subplots(2, 2, figsize=(10.8, 7.2))
    for (material, branch, scenario), group in kinetic.groupby(["material", "branch", "scenario"]):
        group = group.sort_values("tau_h")
        linestyle = "-" if scenario == "state_hold" else "--"
        axes[0, 0].plot(group.tau_h, group.kendall_equilibrium_full_vs_fullLDF, linestyle, marker="o", ms=3, label=f"{material} {branch} {scenario}")
    hold = kinetic.query("scenario == 'state_hold'")
    regime = hold.assign(regime=np.where(hold.tau_h <= 1, "0.25-1 h", "3-12 h")).groupby("regime").kendall_equilibrium_full_vs_fullLDF.agg(["median", "min"])
    xpos = np.arange(len(regime))
    axes[0, 1].bar(xpos, regime["median"], color="#4c78a8")
    axes[0, 1].scatter(xpos, regime["min"], color="#e45756", zorder=3, label="minimum")
    axes[0, 1].set_xticks(xpos, regime.index)
    axes[0, 1].legend(fontsize=7)
    disagreement = kinetic.groupby(["material", "branch", "tau_h"]).kendall_equilibrium_full_vs_fullLDF.agg(lambda values: values.max() - values.min()).reset_index()
    for (material, branch), group in disagreement.groupby(["material", "branch"]):
        axes[1, 0].plot(group.tau_h, group.kendall_equilibrium_full_vs_fullLDF, "o-", ms=3, label=f"{material} {branch}")
    support = hold.query("tau_h == 1").groupby(["material", "branch"]).median_supported_hour_fraction.median()
    labels = [f"{material}\n{branch}" for material, branch in support.index]
    axes[1, 1].bar(np.arange(len(support)), support.values, color="#72b7b2")
    axes[1, 1].set_xticks(np.arange(len(support)), labels, rotation=30, ha="right")
    axes[0, 0].set(title="(a) Equilibrium vs finite-rate ordering", xlabel="tau_k (h)", ylabel="Kendall tau")
    axes[0, 1].set(title="(b) Fast and slow regimes", ylabel="Kendall tau")
    axes[1, 0].set(title="(c) Out-of-domain assumption gap", xlabel="tau_k (h)", ylabel="Maximum tau gap")
    axes[1, 1].set(title="(d) Supported weather fraction", ylabel="Median fraction")
    axes[0, 0].legend(fontsize=5, ncol=2)
    axes[1, 0].legend(fontsize=6)
    figure.suptitle("Figure 6 numerical reconstruction")
    figure.tight_layout()
    save(6, figure, ["SI_kinetic_rank_summary.csv"], "Ea=0 prescribed-time-constant sensitivity.")

    # Figure 7: H-only and Y-only reversals in the final four conditions.
    ira = _read(args.input_dir, "IRA_environmental_common_support_transfer_summary").query("support_treatment == 'common_hour'")
    imcof = _read(args.input_dir, "ImCOF_wholeH_wholeY_transfer_summary")
    rows = []
    for row in ira.itertuples():
        rows.append({"label": f"IRA {row.branch}", "N": row.n_pairs, "Y_only": row.n_Hsafe_Yrev, "H_only": row.n_Hrev_Ysafe})
    label_map = {"active_80C": "ImCOF 80 degC", "environmental_PADAC13X": "ImCOF solar"}
    for row in imcof.itertuples():
        rows.append({"label": label_map[row.operating_mode], "N": row.n_all_pairs, "Y_only": row.n_Hsafe_Yrev, "H_only": row.n_Hrev_Ysafe})
    table = pd.DataFrame(rows)
    table.to_csv(args.output_dir / "Fig7_source_data_reconstructed.csv", index=False)
    figure, axis = plt.subplots(figsize=(8.5, 4.6))
    positions = np.arange(len(table))
    width = 0.35
    axis.bar(positions - width / 2, table.H_only / table.N, width=width, color="#f28e2b", label="H reversed; Y preserved")
    axis.bar(positions + width / 2, table.Y_only / table.N, width=width, color="#4e79a7", label="H preserved; Y reversed")
    axis.set_xticks(positions, table.label)
    axis.set(ylabel="Fraction of eligible location pairs", title="Figure 7 numerical reconstruction")
    axis.legend(fontsize=8)
    figure.tight_layout()
    save(7, figure, ["IRA_environmental_common_support_transfer_summary.csv", "ImCOF_wholeH_wholeY_transfer_summary.csv"], "Common-hour IRA and both ImCOF conditions.")

    pd.DataFrame(manifest).to_csv(args.output_dir / "figure_reconstruction_manifest.csv", index=False)
    print(f"Created {len(manifest)} numerical figure reconstructions")


if __name__ == "__main__":
    main()
