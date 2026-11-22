import numpy as np
import pandas as pd
import pytest

from dac_equilibrium.metrics import (
    partial_kendall_tau,
    rank_agreement,
    summarize_transition_normalized_scores,
    transition_normalized_scores,
)


def test_partial_kendall_uses_declared_three_tau_formula():
    x = np.array([1.0, 4.0, 2.0, 3.0, 6.0])
    y = np.array([2.0, 3.0, 1.0, 5.0, 4.0])
    n = np.array([5.0, 1.0, 3.0, 2.0, 4.0])
    xy = rank_agreement(x, y)["kendall_tau"]
    xn = rank_agreement(x, n)["kendall_tau"]
    yn = rank_agreement(y, n)["kendall_tau"]
    expected = (xy - xn * yn) / np.sqrt((1 - xn**2) * (1 - yn**2))
    assert partial_kendall_tau(x, y, n) == pytest.approx(expected)


def test_h_over_n_panel_and_summary_are_recomputed():
    frame = pd.DataFrame(
        {
            "material": ["A"] * 4,
            "branch": ["lower"] * 4,
            "temporal_mode": ["subsample_1h"] * 4,
            "climate_class": ["test"] * 4,
            "city": ["a", "b", "c", "d"],
            "H_single": [2.0, 6.0, 12.0, 20.0],
            "H_tensor": [3.0, 4.0, 15.0, 18.0],
            "H_RH": [8.0, 9.0, 10.0, 11.0],
            "N": [1, 2, 3, 4],
        }
    )
    normalized = transition_normalized_scores(frame)
    assert normalized["H_single_per_transition"].tolist() == [2.0, 3.0, 4.0, 5.0]
    panel, by_material, summary = summarize_transition_normalized_scores(frame)
    assert len(panel) == 4
    assert len(by_material) == 1
    assert len(summary) == 1
    assert summary.loc[0, "n_materials"] == 1


def test_h_over_n_rejects_nonpositive_transition_counts():
    frame = pd.DataFrame(
        {
            "material": ["A"],
            "branch": ["lower"],
            "temporal_mode": ["subsample_1h"],
            "city": ["a"],
            "H_single": [1.0],
            "H_tensor": [1.0],
            "H_RH": [1.0],
            "N": [0],
        }
    )
    with pytest.raises(ValueError, match="positive"):
        transition_normalized_scores(frame)
