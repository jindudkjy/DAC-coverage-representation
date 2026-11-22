"""Definitions of H, relative H difference, rank statistics, and H-Y reversals."""

from __future__ import annotations

from itertools import combinations

import numpy as np
import pandas as pd


def common_transition_mask(
    *state_values: np.ndarray,
    adjacent: np.ndarray | None = None,
) -> np.ndarray:
    """Return transitions whose two endpoints are finite in every representation."""
    if not state_values:
        raise ValueError("At least one state array is required")
    arrays = [np.asarray(values, dtype=float) for values in state_values]
    if len({array.shape for array in arrays}) != 1:
        raise ValueError("All state arrays must have the same shape")
    states = np.logical_and.reduce([np.isfinite(array) for array in arrays])
    transitions = states[:-1] & states[1:]
    if adjacent is not None:
        adjacent = np.asarray(adjacent, dtype=bool)
        if adjacent.shape != transitions.shape:
            raise ValueError("adjacent must have length len(states) - 1")
        transitions &= adjacent
    return transitions


def half_total_variation(values: np.ndarray, transitions: np.ndarray) -> float:
    """Compute H = 0.5 * sum(|q[t+1] - q[t]|) on selected transitions."""
    values = np.asarray(values, dtype=float)
    transitions = np.asarray(transitions, dtype=bool)
    if transitions.shape != (max(len(values) - 1, 0),):
        raise ValueError("transitions must have length len(values) - 1")
    if not transitions.any():
        return float("nan")
    return float(0.5 * np.abs(np.diff(values)[transitions]).sum())


def trajectory_scores(
    single_loading: np.ndarray,
    resolved_loading: np.ndarray,
    rh_pct: np.ndarray | None = None,
    *,
    adjacent: np.ndarray | None = None,
) -> dict[str, float | int]:
    """Score single/resolved H on their exact common transition support."""
    arrays = [single_loading, resolved_loading]
    if rh_pct is not None:
        arrays.append(rh_pct)
    transitions = common_transition_mask(*arrays, adjacent=adjacent)
    result: dict[str, float | int] = {
        "H_single": half_total_variation(single_loading, transitions),
        "H_tensor": half_total_variation(resolved_loading, transitions),
        "N": int(transitions.sum()),
    }
    if rh_pct is not None:
        result["H_RH"] = half_total_variation(rh_pct, transitions)
    return result


def relative_h_difference(h_single: np.ndarray, h_tensor: np.ndarray) -> np.ndarray:
    """Return |H_single - H_tensor| / |H_tensor|, the manuscript convention."""
    h_single = np.asarray(h_single, dtype=float)
    h_tensor = np.asarray(h_tensor, dtype=float)
    with np.errstate(divide="ignore", invalid="ignore"):
        output = np.abs(h_single - h_tensor) / np.abs(h_tensor)
    return np.where(np.isfinite(output), output, np.nan)


def rank_agreement(x: np.ndarray, y: np.ndarray) -> dict[str, float]:
    finite = np.isfinite(x) & np.isfinite(y)
    x, y = np.asarray(x)[finite], np.asarray(y)[finite]
    if len(x) < 3 or len(np.unique(x)) < 2 or len(np.unique(y)) < 2:
        return {"kendall_tau": np.nan, "spearman_rho": np.nan}
    concordant = discordant = ties_x = ties_y = 0
    for left, right in combinations(range(len(x)), 2):
        dx = np.sign(x[left] - x[right])
        dy = np.sign(y[left] - y[right])
        if dx == 0 and dy == 0:
            continue
        if dx == 0:
            ties_x += 1
        elif dy == 0:
            ties_y += 1
        elif dx == dy:
            concordant += 1
        else:
            discordant += 1
    denominator = np.sqrt(
        (concordant + discordant + ties_x) * (concordant + discordant + ties_y)
    )
    tau = (concordant - discordant) / denominator if denominator else np.nan
    rank_x = pd.Series(x).rank(method="average").to_numpy(float)
    rank_y = pd.Series(y).rank(method="average").to_numpy(float)
    rho = float(np.corrcoef(rank_x, rank_y)[0, 1])
    return {
        "kendall_tau": float(tau),
        "spearman_rho": rho,
    }


def pairwise_reversal_table(
    scores: pd.DataFrame,
    *,
    climate_column: str = "climate",
) -> tuple[pd.DataFrame, dict[str, float | int]]:
    """Classify every strict location pair as neither, H-only, Y-only, or both."""
    required = {climate_column, "H_single", "H_tensor", "Y_single", "Y_tensor"}
    missing = required.difference(scores.columns)
    if missing:
        raise ValueError(f"Missing score columns: {sorted(missing)}")
    frame = scores[list(required)].copy()
    if frame[climate_column].duplicated().any():
        raise ValueError("Climate identifiers must be unique")
    for column in required - {climate_column}:
        frame[column] = pd.to_numeric(frame[column], errors="coerce")
    frame = frame.replace([np.inf, -np.inf], np.nan).dropna().sort_values(climate_column)

    details = []
    counts = {"Hsafe_Ysafe": 0, "Hsafe_Yrev": 0, "Hrev_Ysafe": 0, "Hrev_Yrev": 0}
    h_ties = y_ties = 0
    for left, right in combinations(frame.to_dict("records"), 2):
        delta = {
            key: float(left[key] - right[key])
            for key in ("H_single", "H_tensor", "Y_single", "Y_tensor")
        }
        signs = {key: np.sign(value) for key, value in delta.items()}
        h_tie = signs["H_single"] == 0 or signs["H_tensor"] == 0
        y_tie = signs["Y_single"] == 0 or signs["Y_tensor"] == 0
        h_reversed = not h_tie and signs["H_single"] != signs["H_tensor"]
        y_reversed = not y_tie and signs["Y_single"] != signs["Y_tensor"]
        if h_tie:
            h_ties += 1
        if y_tie:
            y_ties += 1
        joint_class = "EXCLUDED_TIE"
        if not (h_tie or y_tie):
            joint_class = ("Hrev" if h_reversed else "Hsafe") + "_" + (
                "Yrev" if y_reversed else "Ysafe"
            )
            counts[joint_class] += 1
        details.append(
            {
                "climate_a": left[climate_column],
                "climate_b": right[climate_column],
                **{f"delta_{key}": value for key, value in delta.items()},
                "H_tie": h_tie,
                "Y_tie": y_tie,
                "H_reversed": h_reversed,
                "Y_reversed": y_reversed,
                "joint_class": joint_class,
            }
        )

    n_strict = sum(counts.values())
    summary: dict[str, float | int] = {
        "n_common_finite_climates": int(len(frame)),
        "n_pairs": int(len(details)),
        "n_joint_strict_pairs": int(n_strict),
        "n_H_tie_pairs": int(h_ties),
        "n_Y_tie_pairs": int(y_ties),
        **{f"n_{key}": int(value) for key, value in counts.items()},
        **{
            f"tau_{axis}_single_tensor": rank_agreement(
                frame[f"{axis}_single"].to_numpy(float),
                frame[f"{axis}_tensor"].to_numpy(float),
            )["kendall_tau"]
            for axis in ("H", "Y")
        },
        **{
            f"rho_{axis}_single_tensor": rank_agreement(
                frame[f"{axis}_single"].to_numpy(float),
                frame[f"{axis}_tensor"].to_numpy(float),
            )["spearman_rho"]
            for axis in ("H", "Y")
        },
    }
    return pd.DataFrame(details), summary



def partial_kendall_tau(x: np.ndarray, y: np.ndarray, control: np.ndarray) -> float:
    """Partial Kendall coefficient using the manuscript's three-tau formula."""
    x = np.asarray(x, dtype=float)
    y = np.asarray(y, dtype=float)
    control = np.asarray(control, dtype=float)
    finite = np.isfinite(x) & np.isfinite(y) & np.isfinite(control)
    x, y, control = x[finite], y[finite], control[finite]
    tau_xy = rank_agreement(x, y)["kendall_tau"]
    tau_xc = rank_agreement(x, control)["kendall_tau"]
    tau_yc = rank_agreement(y, control)["kendall_tau"]
    denominator = np.sqrt((1.0 - tau_xc**2) * (1.0 - tau_yc**2))
    if not denominator or not np.isfinite(denominator):
        return float("nan")
    return float((tau_xy - tau_xc * tau_yc) / denominator)


def transition_normalized_scores(scores: pd.DataFrame) -> pd.DataFrame:
    """Validate a location-level H panel and add H/N columns."""
    required = {
        "material", "branch", "temporal_mode", "city",
        "H_single", "H_tensor", "H_RH", "N",
    }
    missing = required.difference(scores.columns)
    if missing:
        raise ValueError(f"Missing H/N panel columns: {sorted(missing)}")
    frame = scores.copy()
    for column in ("H_single", "H_tensor", "H_RH", "N"):
        frame[column] = pd.to_numeric(frame[column], errors="coerce")
    if frame[["H_single", "H_tensor", "H_RH", "N"]].isna().any().any():
        raise ValueError("H/N panel contains non-numeric or missing score values")
    if (frame["N"] <= 0).any():
        raise ValueError("Transition count N must be positive")
    if frame.duplicated(["material", "branch", "temporal_mode", "city"]).any():
        raise ValueError("H/N panel contains duplicate location keys")
    frame["H_single_per_transition"] = frame["H_single"] / frame["N"]
    frame["H_tensor_per_transition"] = frame["H_tensor"] / frame["N"]
    frame["H_RH_per_transition"] = frame["H_RH"] / frame["N"]
    return frame


def _strict_reversal_fraction(x: np.ndarray, y: np.ndarray) -> tuple[int, int, float]:
    reversed_pairs = comparable_pairs = 0
    for left, right in combinations(range(len(x)), 2):
        dx = np.sign(x[left] - x[right])
        dy = np.sign(y[left] - y[right])
        if dx == 0 or dy == 0:
            continue
        comparable_pairs += 1
        reversed_pairs += int(dx != dy)
    fraction = reversed_pairs / comparable_pairs if comparable_pairs else np.nan
    return reversed_pairs, comparable_pairs, float(fraction)


def summarize_transition_normalized_scores(
    scores: pd.DataFrame,
) -> tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame]:
    """Reproduce the location panel, material statistics, and SI Table S6 medians."""
    frame = transition_normalized_scores(scores)
    records: list[dict[str, float | int | str]] = []
    keys = ["material", "branch", "temporal_mode"]
    for (material, branch, temporal_mode), group in frame.groupby(keys, sort=True):
        single = group["H_single"].to_numpy(float)
        tensor = group["H_tensor"].to_numpy(float)
        transitions = group["N"].to_numpy(float)
        single_per_n = group["H_single_per_transition"].to_numpy(float)
        tensor_per_n = group["H_tensor_per_transition"].to_numpy(float)
        tau_h = rank_agreement(single, tensor)["kendall_tau"]
        tau_hn = rank_agreement(single_per_n, tensor_per_n)["kendall_tau"]
        tau_single_n = rank_agreement(single, transitions)["kendall_tau"]
        tau_tensor_n = rank_agreement(tensor, transitions)["kendall_tau"]
        partial = partial_kendall_tau(single, tensor, transitions)
        n_reversed, n_comparable, reversal_fraction = _strict_reversal_fraction(
            single_per_n, tensor_per_n
        )
        records.append(
            {
                "material": material,
                "branch": branch,
                "temporal_mode": temporal_mode,
                "n_locations": len(group),
                "tau_H_single_tensor": tau_h,
                "tau_H_over_N_single_tensor": tau_hn,
                "partial_tau_H_single_tensor_given_N": partial,
                "tau_H_single_N": tau_single_n,
                "tau_H_tensor_N": tau_tensor_n,
                "n_H_over_N_reversed_pairs": n_reversed,
                "n_H_over_N_comparable_pairs": n_comparable,
                "H_over_N_reversal_fraction": reversal_fraction,
            }
        )
    by_material = pd.DataFrame(records)
    summary = (
        by_material.groupby(["branch", "temporal_mode"], sort=False)
        .agg(
            n_materials=("material", "nunique"),
            median_tau_H_single_tensor=("tau_H_single_tensor", "median"),
            median_tau_H_over_N_single_tensor=("tau_H_over_N_single_tensor", "median"),
            median_partial_tau_H_single_tensor_given_N=(
                "partial_tau_H_single_tensor_given_N", "median"
            ),
            median_tau_H_single_N=("tau_H_single_N", "median"),
            median_tau_H_tensor_N=("tau_H_tensor_N", "median"),
            median_H_over_N_reversal_fraction=(
                "H_over_N_reversal_fraction", "median"
            ),
        )
        .reset_index()
    )
    temporal_order = {
        name: index for index, name in enumerate(
            ["subsample_1h", "subsample_3h", "subsample_6h",
             "subsample_24h", "average_6h", "average_24h"]
        )
    }
    summary["_branch_order"] = summary["branch"].map({"lower": 0, "upper": 1})
    summary["_temporal_order"] = summary["temporal_mode"].map(temporal_order)
    summary = summary.sort_values(["_branch_order", "_temporal_order"]).drop(
        columns=["_branch_order", "_temporal_order"]
    ).reset_index(drop=True)
    return frame, by_material, summary
