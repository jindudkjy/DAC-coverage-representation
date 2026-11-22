"""Numeric regression helpers for frozen CSV outputs."""

from __future__ import annotations

import numpy as np
import pandas as pd


def compare_frames(
    actual: pd.DataFrame,
    expected: pd.DataFrame,
    *,
    keys: list[str],
    atol: float = 1e-9,
    rtol: float = 1e-9,
) -> pd.DataFrame:
    """Compare two tables by stable keys and report per-column discrepancies."""
    if actual.duplicated(keys).any() or expected.duplicated(keys).any():
        raise ValueError("Comparison keys must be unique in both tables")
    joined = actual.merge(expected, on=keys, how="outer", suffixes=("_actual", "_expected"), indicator=True)
    if not (joined._merge == "both").all():
        missing = joined.loc[joined._merge != "both", keys + ["_merge"]]
        raise AssertionError(f"Row-key mismatch:\n{missing}")
    rows = []
    shared = sorted((set(actual.columns) & set(expected.columns)) - set(keys))
    for column in shared:
        left, right = joined[f"{column}_actual"], joined[f"{column}_expected"]
        if pd.api.types.is_numeric_dtype(left) and pd.api.types.is_numeric_dtype(right):
            difference = np.abs(left.to_numpy(float) - right.to_numpy(float))
            finite = np.isfinite(difference)
            max_abs_error = float(difference[finite].max()) if finite.any() else 0.0
            passed = bool(np.allclose(left, right, atol=atol, rtol=rtol, equal_nan=True))
            kind = "numeric"
        else:
            max_abs_error = np.nan
            passed = bool(left.fillna("<NA>").astype(str).equals(right.fillna("<NA>").astype(str)))
            kind = "exact"
        rows.append(
            {"column": column, "comparison": kind, "max_abs_error": max_abs_error, "passed": passed}
        )
    return pd.DataFrame(rows)

