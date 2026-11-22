import numpy as np

from dac_equilibrium.kinetics import propagate_ldf, simulate_two_pass_ldf


def test_one_hour_ldf_update_is_exact_exponential():
    target = np.array([0.0, 1.0, 1.0])
    trajectory = propagate_ldf(target, tau_h=1.0)
    alpha = 1.0 - np.exp(-1.0)
    np.testing.assert_allclose(trajectory, [0.0, alpha, alpha + alpha * (1 - alpha)])


def test_hold_mode_preserves_state_outside_support():
    target = np.array([0.0, 1.0, np.nan, 0.0])
    supported = np.array([True, True, False, True])
    trajectory = propagate_ldf(target, tau_h=1.0, supported=supported, gap_mode="hold")
    assert trajectory[2] == trajectory[1]


def test_two_pass_scores_only_supported_endpoint_pairs():
    temperature = np.full(4, 25.0)
    tensor = np.array([0.0, 1.0, 0.0, 1.0])
    single = np.array([0.0, 0.5, 0.0, 0.5])
    supported = np.array([True, True, False, True])
    result = simulate_two_pass_ldf(
        temperature,
        tensor,
        single,
        supported,
        tau_h=1.0,
    )
    assert result.n_scored == 1
    assert result.H_tensor_equilibrium == 0.5
    assert result.H_single_equilibrium == 0.25

