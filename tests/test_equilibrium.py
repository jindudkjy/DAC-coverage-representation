import numpy as np
import pandas as pd

from dac_equilibrium.equilibrium import DomainBounds, EquilibriumSurface


def surface():
    frame = pd.DataFrame(
        {
            "T_C": [0, 0, 10, 10, 20, 20],
            "RH_pct": [0, 100, 0, 100, 0, 100],
            "q_mmol_g": [0, 1, 0, 2, 0, 3],
        }
    )
    return EquilibriumSurface(frame, DomainBounds(0, 10, 20, 0, 100))


def test_single_isotherm_uses_reference_slice():
    values = surface().single_isotherm(np.array([25.0, 50.0, 75.0]))
    np.testing.assert_allclose(values, [0.5, 1.0, 1.5])


def test_temperature_resolved_interpolates_adjacent_slices():
    values = surface().temperature_resolved(
        np.array([5.0, 15.0]), np.array([50.0, 50.0])
    )
    np.testing.assert_allclose(values, [0.75, 1.25])


def test_no_extrapolation():
    values = surface().temperature_resolved(
        np.array([-1.0, 10.0, 21.0]), np.array([50.0, 101.0, 50.0])
    )
    assert np.isnan(values).all()

