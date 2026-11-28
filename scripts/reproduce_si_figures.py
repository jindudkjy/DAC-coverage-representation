#!/usr/bin/env python
"""Create numerical verification plots for current SI Figures S1-S7."""

from __future__ import annotations

import argparse
from pathlib import Path

import numpy as np
import pandas as pd


def read(input_dir: Path, name: str) -> pd.DataFrame:
    path = input_dir / name
    if not path.exists():
        raise FileNotFoundError(path)
    return pd.read_csv(path)


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--input-dir", type=Path, required=True)
    parser.add_argument("--output-dir", type=Path, default=Path("results/si_figures"))
    args = parser.parse_args()

    import matplotlib

    matplotlib.use("Agg")
    import matplotlib.pyplot as plt

    args.output_dir.mkdir(parents=True, exist_ok=True)
    manifest = []

    def save(label: str, figure, sources: list[str], note: str) -> None:
        filename = f"Fig{label}_numerical_reconstruction.png"
        figure.savefig(args.output_dir / filename, dpi=600, bbox_inches="tight")
        plt.close(figure)
        manifest.append({"figure": label, "output": filename, "source_files": "; ".join(sources), "note": note})

    # Current SI Figure S1: LWT-bPPI5 protocol substitution.
    s1 = read(args.input_dir, "SI_Fig_S1_source_data.csv")
    positions = np.arange(len(s1))
    figure, axis = plt.subplots(figsize=(8.2, 4.2))
    for position, left, right in zip(
        positions, s1.pre_saturated_delta_tau, s1.dry_start_delta_tau
    ):
        axis.plot([left, right], [position, position], color="0.7", lw=1)
    axis.scatter(s1.pre_saturated_delta_tau, positions, label="Pre-saturated humid series")
    axis.scatter(s1.dry_start_delta_tau, positions, marker="s", label="Dry-start co-adsorption substitution")
    axis.axvline(0, color="black", lw=0.8)
    axis.set_yticks(positions, s1.label)
    axis.invert_yaxis()
    axis.set(xlabel="Change in Kendall tau (Delta tau)", title="LWT-bPPI5 protocol substitution")
    axis.legend(frameon=False)
    figure.tight_layout()
    save("S1", figure, ["SI_Fig_S1_source_data.csv"], "Published SI Table S7 values.")

    # Current SI Figure S2: bounded temperature-specific capacity perturbations.
    s2 = read(args.input_dir, "SI_Fig_S2_source_data.csv")
    positions = np.arange(len(s2))
    width = 0.29
    figure, axis = plt.subplots(figsize=(8.2, 4.2))
    axis.bar(positions - width / 2, s2.median_of_median_delta_tau, width, label="Median of median Delta tau")
    axis.bar(positions + width / 2, s2.worst_median_delta_tau, width, label="Worst median Delta tau")
    axis.axhline(0, color="0.25", lw=0.8)
    axis.set_xticks(positions, [f"+/- {value:g}%" for value in s2.perturbation_magnitude_pct])
    axis.set(ylabel="Delta tau", title="Temperature-specific capacity perturbations")
    axis.text(
        0.02,
        0.95,
        f"All six temporal treatments positive in {s2.fraction_all_six_positive_pct.iloc[0]:.1f}% of trials at each bound",
        transform=axis.transAxes,
        va="top",
    )
    axis.legend(frameon=False)
    figure.tight_layout()
    save("S2", figure, ["SI_Fig_S2_source_data.csv"], "Published SI Table S8 values.")

    # Current SI Figure S6: measured-domain boundary-extension gains.
    s6 = read(args.input_dir, "SI_Fig_S6_source_data.csv")
    figure, axis = plt.subplots(figsize=(7.2, 4.2))
    positions = np.arange(len(s6))
    width = 0.36
    axis.bar(positions - width / 2, s6.temperature_extension_gain_pp, width, label="5 degC temperature extension")
    axis.bar(positions + width / 2, s6.upper_RH_extension_gain_pp, width, label="5 pp upper-RH extension")
    axis.set_xticks(positions, s6.group)
    axis.set(ylabel="Pooled transition-coverage gain (pp)", title="SI Figure S6 numerical reconstruction")
    axis.legend()
    figure.tight_layout()
    save("S6", figure, ["SI_Fig_S6_source_data.csv"], "Selected independently regenerated boundary-extension values.")

    # Current SI Figure S7: IRA shared-hour and representation-specific support.
    s7 = read(args.input_dir, "SI_Fig_S7_source_data.csv")
    figure, axis = plt.subplots(figsize=(7.2, 4.2))
    s7["label"] = s7.branch + "\n" + s7.support_treatment.str.replace("_", " ")
    positions = np.arange(len(s7))
    axis.bar(positions, s7.n_Hsafe_Yrev / s7.n_pairs, color="#4e79a7")
    axis.set_xticks(positions, s7.label)
    axis.set(ylabel="Fraction with H preserved and Y reversed", title="SI Figure S7 numerical reconstruction")
    figure.tight_layout()
    save("S7", figure, ["SI_Fig_S7_source_data.csv"], "Shared-hour and representation-specific IRA classifications.")

    # Current SI Figure S3: held-interior added-temperature sensitivity.
    lwt = read(args.input_dir, "SI_added_temperature_held_interior.csv")
    lwt = lwt.query("material == 'LWT-bPPI5' and branch == 'upper' and support_mode == 'matched'").copy()
    mg = read(args.input_dir, "Mg_LWT_analogue_delta_tau_bootstrap.csv")
    modes = ["subsample_1h", "subsample_3h", "subsample_6h", "subsample_24h", "average_6h", "average_24h"]
    lwt = lwt.set_index("temporal_mode").loc[modes].reset_index()
    mg = mg.set_index("temporal_mode").loc[modes].reset_index()
    figure, axes = plt.subplots(1, 2, figsize=(10.5, 4.2), sharey=True)
    axes[0].plot(np.arange(len(lwt)), lwt.delta_tau, "o-", color="#4e79a7")
    axes[0].axhline(0, color="0.4", lw=0.8)
    axes[0].set(title="(a) LWT-bPPI5", ylabel="Delta Kendall tau")
    yerr = np.vstack([mg.observed_delta_tau - mg.bootstrap_q025, mg.bootstrap_q975 - mg.observed_delta_tau])
    axes[1].errorbar(np.arange(len(mg)), mg.observed_delta_tau, yerr=yerr, fmt="o-", color="#f28e2b", ecolor="0.6", capsize=2)
    axes[1].axhline(0, color="0.4", lw=0.8)
    axes[1].set(title="(b) MgAl-PEI")
    labels = [mode.replace("subsample_", "").replace("average_", "avg ") for mode in modes]
    for axis in axes:
        axis.set_xticks(np.arange(len(modes)), labels, rotation=35, ha="right")
    figure.suptitle("SI Figure S3 numerical reconstruction")
    figure.tight_layout()
    save("S3", figure, ["SI_added_temperature_held_interior.csv", "Mg_LWT_analogue_delta_tau_bootstrap.csv"], "LWT observed values and Mg paired-location percentile ranges.")

    # Current SI Figure S4: structured capacity-bias sensitivity.
    s4 = read(args.input_dir, "SI_Fig_S4_source_data.csv").sort_values("structured_capacity_bias")
    figure, axes = plt.subplots(1, 2, figsize=(10.5, 4.2))
    axes[0].plot(s4.structured_capacity_bias, s4.mg_median_C_rel, "o-", label="MgAl-PEI")
    axes[0].plot(s4.structured_capacity_bias, s4.ira_median_C_rel, "s-", label="IRA-900-C")
    axes[0].set(title="Correction magnitude", xlabel="Structured capacity bias", ylabel="Median C_rel")
    axes[0].legend(frameon=False)
    axes[1].plot(s4.structured_capacity_bias, s4.mg_reversal_fraction_pct, "o-", label="MgAl-PEI")
    axes[1].plot(s4.structured_capacity_bias, s4.ira_reversal_fraction_pct, "s-", label="IRA-900-C")
    axes[1].set(title="Ordinal consequence", xlabel="Structured capacity bias", ylabel="Reversal fraction (%)")
    figure.tight_layout()
    save(
        "S4",
        figure,
        ["SI_Fig_S4_source_data.csv"],
        "Point values digitized from final SI artwork and constrained to the published SI Table S10 ranges.",
    )

    # Current SI Figure S5: continuous-state kinetic sensitivity for IRA-900-C.
    kinetic = read(args.input_dir, "SI_kinetic_rank_summary.csv")
    kinetic = kinetic.query("material == 'IRA-900-C' and Ea_kJmol == 0").copy()
    figure, axes = plt.subplots(2, 2, figsize=(10.5, 8.0))
    for branch, color in [("lower", "#2ca02c"), ("upper", "#d62728")]:
        for scenario, linestyle in [("state_hold", "-"), ("boundary_capped", "--")]:
            group = kinetic.query("branch == @branch and scenario == @scenario").sort_values("tau_h")
            if len(group):
                axes[0, 0].plot(group.tau_h, group.kendall_equilibrium_full_vs_fullLDF, marker="o", color=color, linestyle=linestyle, label=f"{branch} {scenario}")
        hold = kinetic.query("branch == @branch and scenario == 'state_hold'").sort_values("tau_h")
        axes[0, 1].plot(hold.tau_h, hold.kendall_equilibrium_full_vs_fullLDF, marker="o", color=color, label=branch)
    hold = kinetic.query("scenario == 'state_hold'")
    coverage = hold.query("tau_h == 1").groupby("branch").median_supported_hour_fraction.median() * 100
    axes[1, 0].barh(np.arange(len(coverage)), coverage.values)
    axes[1, 0].set_yticks(np.arange(len(coverage)), coverage.index)
    gap = kinetic.groupby(["branch", "tau_h"]).kendall_equilibrium_full_vs_fullLDF.agg(lambda values: values.max() - values.min()).reset_index()
    for branch, group in gap.groupby("branch"):
        axes[1, 1].plot(group.tau_h, group.kendall_equilibrium_full_vs_fullLDF, "o-", label=branch)
    axes[0, 0].set(title="(a) IRA equilibrium vs kinetic ordering", xlabel="LDF time constant (h)", ylabel="Kendall tau")
    axes[0, 1].set(title="(b) State-hold sensitivity", xlabel="LDF time constant (h)", ylabel="Kendall tau")
    axes[1, 0].set(title="(c) Measured-domain coverage", xlabel="Supported hours (%)")
    axes[1, 1].set(title="(d) Out-of-domain treatment gap", xlabel="LDF time constant (h)", ylabel="Maximum tau gap")
    for axis in axes.ravel():
        if axis.lines:
            axis.legend(fontsize=7)
    figure.tight_layout()
    save("S5", figure, ["SI_kinetic_rank_summary.csv"], "IRA lower/upper continuous-state kinetic sensitivity.")

    pd.DataFrame(manifest).to_csv(args.output_dir / "si_figure_reconstruction_manifest.csv", index=False)
    print(f"Created {len(manifest)} SI figure reconstructions")


if __name__ == "__main__":
    main()
