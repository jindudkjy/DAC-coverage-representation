#!/usr/bin/env python
"""Reproduce Section 3.2, Figure 3b, and SI Table S6.

Usage:
    python scripts/n_controlled_ordering.py \
        MAIN_climate_H_scores.csv \
        N_controlled_ordering_by_case.csv \
        SI_Table_S6_N_controlled_summary.csv \
        Fig3_source_data.csv

The random-reassignment test uses one ``numpy.random.default_rng(0)``
generator shared by every comparison case. Cases are processed in sorted
``(material, branch, temporal_mode)`` order. Within each case, 3,000 H
reassignments are drawn first and 3,000 H/N reassignments second. Changing
that order, the draw count, or seeding each case separately changes the
published Monte Carlo medians.
"""

from __future__ import annotations

import argparse
from pathlib import Path

import numpy as np
import pandas as pd
from scipy.stats import kendalltau


TOTAL_TRANSITIONS = {
    "subsample_1h": 87647,
    "subsample_3h": 87647 / 3,
    "subsample_6h": 87647 / 6,
    "subsample_24h": 87647 / 24,
    "average_6h": 87647 / 6,
    "average_24h": 87647 / 24,
}


def reversal_fraction(a: np.ndarray, b: np.ndarray) -> float:
    """Return the strict reversal count divided by all location pairs."""
    left, right = np.triu_indices(len(a), 1)
    delta_a = a[left] - a[right]
    delta_b = b[left] - b[right]
    return float(np.mean(np.sign(delta_a) * np.sign(delta_b) < 0))


def partial_tau(x: np.ndarray, y: np.ndarray, control: np.ndarray) -> float:
    """Return the manuscript's three-tau partial-Kendall coefficient."""
    tau_xy = kendalltau(x, y)[0]
    tau_xc = kendalltau(x, control)[0]
    tau_yc = kendalltau(y, control)[0]
    return float(
        (tau_xy - tau_xc * tau_yc)
        / np.sqrt((1 - tau_xc**2) * (1 - tau_yc**2))
    )


def analyze_scores(
    scores: pd.DataFrame,
    *,
    n_reassignments: int = 3000,
    seed: int = 0,
) -> tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame]:
    """Return case results, SI Table S6, and Figure 3b source data."""
    required = {
        "material",
        "branch",
        "temporal_mode",
        "H_single",
        "H_tensor",
        "N",
    }
    missing = required.difference(scores.columns)
    if missing:
        raise ValueError(f"Missing H-panel columns: {sorted(missing)}")
    if n_reassignments < 1:
        raise ValueError("n_reassignments must be positive")

    rng = np.random.default_rng(seed)
    rows: list[dict[str, float | int | bool | str]] = []
    figure_rows: list[dict[str, float | str]] = []

    for (material, branch, temporal_mode), group in scores.groupby(
        ["material", "branch", "temporal_mode"], sort=True
    ):
        single = group["H_single"].to_numpy(float)
        tensor = group["H_tensor"].to_numpy(float)
        transitions = group["N"].to_numpy(float)
        relative_change = tensor / single
        output: dict[str, float | int | bool | str] = {
            "m": material,
            "br": branch,
            "tm": temporal_mode,
            "n": len(group),
        }

        for label, (a, b) in {
            "H": (single, tensor),
            "HN": (single / transitions, tensor / transitions),
        }.items():
            output[f"tau_{label}"] = float(kendalltau(a, b)[0])
            output[f"rev_{label}"] = reversal_fraction(a, b)
            permutation = np.array(
                [
                    reversal_fraction(
                        a,
                        a * relative_change[rng.permutation(len(relative_change))],
                    )
                    for _ in range(n_reassignments)
                ]
            )
            output[f"perm_{label}"] = float(np.median(permutation))
            output[f"below_{label}"] = bool(
                output[f"rev_{label}"] < np.percentile(permutation, 2.5)
            )

        output["tauN"] = float(kendalltau(single, transitions)[0])
        output["ptau"] = (
            partial_tau(single, tensor, transitions) if len(group) > 2 else np.nan
        )
        output["relH"] = float(np.median(np.abs(tensor - single) / single))
        keep = transitions / TOTAL_TRANSITIONS[temporal_mode] >= 0.05
        for label, (a, b) in {
            "H": (single, tensor),
            "HN": (single / transitions, tensor / transitions),
        }.items():
            output[f"tau5_{label}"] = (
                float(kendalltau(a[keep], b[keep])[0])
                if int(keep.sum()) >= 3
                else np.nan
            )

        rows.append(output)
        figure_rows.append(
            {
                "br": branch,
                "tm": temporal_mode,
                "rel": float(np.median(np.abs(tensor - single) / tensor)),
                "tH": float(output["tau_H"]),
                "tHN": float(output["tau_HN"]),
            }
        )

    by_case = pd.DataFrame(rows)
    summary = (
        by_case.groupby(["br", "tm"])
        .agg(
            tau_H=("tau_H", "median"),
            tau_HN=("tau_HN", "median"),
            ptau=("ptau", "median"),
            tauN=("tauN", "median"),
            rev_HN=("rev_HN", "median"),
            perm_HN=("perm_HN", "median"),
            below_HN=("below_HN", "sum"),
        )
        .reset_index()
    )
    temporal_order = list(TOTAL_TRANSITIONS)
    summary["_order"] = summary["tm"].map(temporal_order.index)
    summary = summary.sort_values(["br", "_order"]).drop(columns="_order")
    return by_case, summary, pd.DataFrame(figure_rows)


def write_outputs(
    scores: pd.DataFrame,
    by_case_path: Path,
    summary_path: Path,
    figure_path: Path,
    *,
    n_reassignments: int = 3000,
    seed: int = 0,
) -> tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame]:
    """Run the analysis and write all three public reproduction outputs."""
    by_case, summary, figure = analyze_scores(
        scores,
        n_reassignments=n_reassignments,
        seed=seed,
    )
    for path in (by_case_path, summary_path, figure_path):
        path.parent.mkdir(parents=True, exist_ok=True)
    by_case.to_csv(by_case_path, index=False)
    summary.to_csv(summary_path, index=False)
    figure.to_csv(figure_path, index=False)
    return by_case, summary, figure


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("input_file", type=Path)
    parser.add_argument(
        "by_case_output",
        type=Path,
        nargs="?",
        default=Path("N_controlled_ordering_by_case.csv"),
    )
    parser.add_argument(
        "summary_output",
        type=Path,
        nargs="?",
        default=Path("SI_Table_S6_N_controlled_summary.csv"),
    )
    parser.add_argument(
        "figure_output",
        type=Path,
        nargs="?",
        default=Path("Fig3_source_data.csv"),
    )
    parser.add_argument("--permutations", type=int, default=3000)
    parser.add_argument("--seed", type=int, default=0)
    args = parser.parse_args()

    by_case, _, _ = write_outputs(
        pd.read_csv(args.input_file),
        args.by_case_output,
        args.summary_output,
        args.figure_output,
        n_reassignments=args.permutations,
        seed=args.seed,
    )

    pd.set_option("display.width", 250)
    native = by_case[by_case.tm == "subsample_1h"]
    print(
        "native medians\n",
        native.groupby("br")[
            ["relH", "tau_H", "tau_HN", "ptau", "rev_H", "rev_HN"]
        ].median().round(4),
    )
    average_24h = by_case[by_case.tm == "average_24h"]
    print(
        "24h avg\n",
        average_24h.groupby("br")[["relH", "tau_H", "tau_HN", "ptau"]]
        .median()
        .round(4),
    )
    print(
        "all cases\n",
        by_case.groupby("br")[
            [
                "rev_H",
                "rev_HN",
                "perm_H",
                "perm_HN",
                "tau5_H",
                "tau5_HN",
                "tau_H",
                "tau_HN",
            ]
        ].median().round(4),
    )
    print(
        by_case.groupby("br")[["below_H", "below_HN"]].sum(),
        by_case.groupby("br").size(),
    )
    print("5%filter n cases with >=3:", by_case.groupby("br").tau5_H.count())


if __name__ == "__main__":
    main()
