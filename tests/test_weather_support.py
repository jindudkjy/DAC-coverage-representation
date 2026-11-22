import numpy as np
import pandas as pd

from dac_equilibrium.weather_support import (
    cap_subzero_rh_at_ice_saturation,
    ice_saturation_rh_percent,
    immediate_boundary_state_counts,
    measurement_domain_extensions,
)


def test_ice_saturation_limits_match_reported_values():
    result = ice_saturation_rh_percent([-5, -10, -15, -20, -25])
    np.testing.assert_allclose(result, [95.3, 90.7, 86.4, 82.3, 78.3], atol=0.08)


def test_subzero_rh_cap_leaves_warm_values_unchanged():
    result = cap_subzero_rh_at_ice_saturation(np.array([-20.0, 5.0]), np.array([90.0, 90.0]))
    assert result[0] < 83
    assert result[1] == 90


def test_immediate_boundary_state_counts():
    weather = pd.DataFrame(
        {
            "temperature_C": [-22, -10, -10, -10],
            "RH_pct": [60, 72, 76, 60],
        }
    )
    result = immediate_boundary_state_counts(weather)
    row = result.query("T_high == -5 and RH_high == 70").iloc[0]
    assert row.states_upper_RH_5pp_band == 1
    assert row.states_colder_5C_band == 1


def test_boundary_extension_increases_or_preserves_coverage():
    weather = pd.DataFrame(
        {
            "city": ["A"] * 4 + ["B"] * 4,
            "timestamp_utc": list(pd.date_range("2020-01-01", periods=4, freq="h", tz="UTC")) * 2,
            "temperature_C": [0, 5, 10, 15, 0, 5, 10, 15],
            "RH_pct": [10, 20, 30, 40, 10, 20, 30, 40],
        }
    )
    bounds = pd.DataFrame(
        {"material": ["M"], "Tlow": [0], "Tref": [10], "Thigh": [20], "Rmin": [10], "Rmax": [90]}
    )
    raw = pd.DataFrame(
        {
            "material": ["M"] * 6,
            "T_C": [0, 0, 10, 10, 20, 20],
            "RH_pct": [10, 90, 10, 90, 10, 90],
            "q_mmol_g": [0, 1, 0, 2, 0, 3],
        }
    )
    table, stats = measurement_domain_extensions(weather, bounds, raw)
    assert len(table) == 8
    assert stats["locations"] == 2
    assert (table.candidate_transition_coverage >= table.baseline_transition_coverage).all()
