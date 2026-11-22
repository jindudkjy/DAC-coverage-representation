import numpy as np
import pandas as pd

from dac_equilibrium.metrics import (
    pairwise_reversal_table,
    relative_h_difference,
    trajectory_scores,
)


def test_h_is_half_total_variation_on_common_support():
    single = np.array([0.0, 2.0, 1.0, np.nan, 3.0])
    tensor = np.array([0.0, 1.0, 3.0, np.nan, 4.0])
    scores = trajectory_scores(single, tensor)
    assert scores["N"] == 2
    assert scores["H_single"] == 1.5
    assert scores["H_tensor"] == 1.5


def test_relative_h_uses_tensor_denominator():
    result = relative_h_difference(np.array([8.0]), np.array([10.0]))
    np.testing.assert_allclose(result, [0.2])


def test_pairwise_reversal_classes():
    scores = pd.DataFrame(
        {
            "climate": ["A", "B", "C"],
            "H_single": [3.0, 2.0, 1.0],
            "H_tensor": [1.0, 2.0, 3.0],
            "Y_single": [3.0, 2.0, 1.0],
            "Y_tensor": [3.0, 1.0, 2.0],
        }
    )
    pairs, summary = pairwise_reversal_table(scores)
    assert len(pairs) == 3
    assert summary["n_pairs"] == 3
    assert summary["n_joint_strict_pairs"] == 3
    assert summary["n_Hrev_Ysafe"] == 2
    assert summary["n_Hrev_Yrev"] == 1

