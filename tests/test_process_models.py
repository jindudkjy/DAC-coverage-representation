import numpy as np

from dac_equilibrium.process_models import imcof_modeled_release, ira_modeled_release


def test_ira_y_accumulates_only_loading_decreases():
    release = ira_modeled_release(np.array([1.0, 0.0, 1.0]), tau_h=1e-6)
    np.testing.assert_allclose(release, 1.0, atol=1e-9)


def test_imcof_y_is_common_supported_cycle_mean():
    rich = np.array([1.0, 2.0, 3.0])
    fraction = np.array([0.5, 0.5, 1.0])
    common = np.array([True, False, True])
    assert imcof_modeled_release(rich, fraction, common_supported_cycles=common) == 1.75

