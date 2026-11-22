#!/usr/bin/env python
"""Create numerical verification plots for SI Figures S5-S7."""

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
        figure.savefig(args.output_dir / filename, dpi=200, bbox_inches="tight")
        plt.close(figure)
        manifest.append({"figure": label, "output": filename, "source_files": "; ".join(sources), "note": note})

    s5 = read(args.input_dir, "SI_Fig_S5_source_data.csv")
    figure, axis = plt.subplots(figsize=(7.2, 4.2))
    positions = np.arange(len(s5))
    width = 0.36
    axis.bar(positions - width / 2, s5.temperature_extension_gain_pp, width, label="5 degC temperature extension")
    axis.bar(positions + width / 2, s5.upper_RH_extension_gain_pp, width, label="5 pp upper-RH extension")
    axis.set_xticks(positions, s5.group)
    axis.set(ylabel="Pooled transition-coverage gain (pp)", title="SI Figure S5 numerical reconstruction")
    axis.legend()
    figure.tight_layout()
    save("S5", figure, ["SI_Fig_S5_source_data.csv"], "Selected independently regenerated boundary-extension values.")

    s6 = read(args.input_dir, "SI_Fig_S6_source_data.csv")
    figure, axis = plt.subplots(figsize=(7.2, 4.2))
    s6["label"] = s6.branch + "\n" + s6.support_treatment.str.replace("_", " ")
    positions = np.arange(len(s6))
    axis.bar(positions, s6.n_Hsafe_Yrev / s6.n_pairs, color="#4e79a7")
    axis.set_xticks(positions, s6.label)
    axis.set(ylabel="Fraction with H preserved and Y reversed", title="SI Figure S6 numerical reconstruction")
    figure.tight_layout()
    save("S6", figure, ["SI_Fig_S6_source_data.csv"], "Shared-hour and representation-specific IRA classifications.")

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
    figure.suptitle("SI Figure S7 numerical reconstruction")
    figure.tight_layout()
    save("S7", figure, ["SI_added_temperature_held_interior.csv", "Mg_LWT_analogue_delta_tau_bootstrap.csv"], "LWT observed values and Mg paired-location percentile ranges.")

    pd.DataFrame(manifest).to_csv(args.output_dir / "si_figure_reconstruction_manifest.csv", index=False)
    print(f"Created {len(manifest)} SI figure reconstructions")


if __name__ == "__main__":
    main()
