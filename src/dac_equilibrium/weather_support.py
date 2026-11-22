"""Measured-domain weather support and one-boundary extension calculations."""

from __future__ import annotations

import re

import numpy as np
import pandas as pd

EXTENSIONS = (
    "T_low_minus_5C",
    "T_high_plus_5C",
    "RH_low_minus_5pp",
    "RH_high_plus_5pp",
)


def ice_saturation_rh_percent(temperature_c: np.ndarray | pd.Series | float) -> np.ndarray:
    """Water-referenced RH at ice saturation using Murphy and Koop (2005).

    NASA POWER RH2M is referenced to saturation over liquid water.  Below
    0 degC, ``100 * e_si / e_sw`` is therefore the water-referenced RH that
    corresponds to ice saturation.
    """
    temperature_k = np.asarray(temperature_c, dtype=float) + 273.15
    log_water = (
        54.842763
        - 6763.22 / temperature_k
        - 4.210 * np.log(temperature_k)
        + 0.000367 * temperature_k
        + np.tanh(0.0415 * (temperature_k - 218.8))
        * (
            53.878
            - 1331.22 / temperature_k
            - 9.44523 * np.log(temperature_k)
            + 0.014025 * temperature_k
        )
    )
    log_ice = (
        9.550426
        - 5723.265 / temperature_k
        + 3.53068 * np.log(temperature_k)
        - 0.00728332 * temperature_k
    )
    return 100.0 * np.exp(log_ice - log_water)


def cap_subzero_rh_at_ice_saturation(
    temperature_c: np.ndarray | pd.Series,
    rh_percent: np.ndarray | pd.Series,
) -> np.ndarray:
    """Return RH with subzero values capped at water-referenced ice saturation."""
    temperature = np.asarray(temperature_c, dtype=float)
    rh = np.asarray(rh_percent, dtype=float).copy()
    mask = np.isfinite(temperature) & np.isfinite(rh) & (temperature < 0)
    rh[mask] = np.minimum(rh[mask], ice_saturation_rh_percent(temperature[mask]))
    return rh


def lower_temperature_weather_summary(weather: pd.DataFrame) -> pd.DataFrame:
    """Reproduce the pooled lower-temperature distribution used in SI Table S16."""
    temperature = weather["temperature_C"].to_numpy(float)
    rh = weather["RH_pct"].to_numpy(float)
    finite = np.isfinite(temperature) & np.isfinite(rh)
    rows: list[dict[str, float | int | str]] = []
    for low, high in [(-25, -20), (-20, -15), (-15, -10), (-10, -5), (-5, 0)]:
        mask = finite & (temperature >= low) & (temperature < high)
        limit = ice_saturation_rh_percent(temperature[mask])
        rows.append(
            {
                "temperature_range_C": f"{low} to {high}",
                "n_states": int(mask.sum()),
                "median_RH_pct": float(np.median(rh[mask])),
                "fraction_RH_above_70": float(np.mean(rh[mask] > 70)),
                "fraction_ice_supersaturated": float(np.mean(rh[mask] > limit)),
            }
        )
    subzero = finite & (temperature < 0)
    rows.append(
        {
            "temperature_range_C": "all subzero",
            "n_states": int(subzero.sum()),
            "median_RH_pct": float(np.median(rh[subzero])),
            "fraction_RH_above_70": float(np.mean(rh[subzero] > 70)),
            "fraction_ice_supersaturated": float(
                np.mean(rh[subzero] > ice_saturation_rh_percent(temperature[subzero]))
            ),
        }
    )
    return pd.DataFrame(rows)


def immediate_boundary_state_counts(weather: pd.DataFrame) -> pd.DataFrame:
    """Count states in the two extension bands shown in main Figure 2/SI Table S17."""
    temperature = weather["temperature_C"].to_numpy(float)
    rh = weather["RH_pct"].to_numpy(float)
    finite = np.isfinite(temperature) & np.isfinite(rh)
    rows = []
    for low, high, rh_high in [(-20, -5, 70), (-20, 5, 70), (-20, 5, 80)]:
        rh_band = finite & (temperature >= low) & (temperature <= high) & (rh > rh_high) & (rh <= rh_high + 5)
        cold_band = finite & (temperature >= low - 5) & (temperature < low) & (rh >= 0) & (rh <= rh_high)
        cold_count = int(cold_band.sum())
        rows.append(
            {
                "T_low": low,
                "T_high": high,
                "RH_low": 0,
                "RH_high": rh_high,
                "states_upper_RH_5pp_band": int(rh_band.sum()),
                "states_colder_5C_band": cold_count,
                "state_count_ratio": float(rh_band.sum() / cold_count),
            }
        )
    return pd.DataFrame(rows)


def _normalise_material(value: object) -> str:
    return re.sub(r"[^a-z0-9]+", "", str(value).lower())


def measurement_domain_extensions(
    weather: pd.DataFrame,
    bounds: pd.DataFrame,
    equilibrium_raw: pd.DataFrame,
) -> tuple[pd.DataFrame, dict[str, int]]:
    """Recompute native-hour support gains for each single-boundary extension."""
    raw = equilibrium_raw.copy()
    raw["_key"] = raw["material"].map(_normalise_material)
    rh_by_temperature = {
        (key, float(temperature)): (float(group.RH_pct.min()), float(group.RH_pct.max()))
        for (key, temperature), group in raw.groupby(["_key", "T_C"])
    }

    weather = weather.sort_values(["city", "timestamp_utc"], kind="stable").reset_index(drop=True)
    cities, city_index = np.unique(weather.city.to_numpy(), return_inverse=True)
    temperature = weather.temperature_C.to_numpy(float)
    rh = weather.RH_pct.to_numpy(float)
    timestamp = pd.to_datetime(weather.timestamp_utc, utc=True).to_numpy()
    eligible = (city_index[1:] == city_index[:-1]) & (
        (timestamp[1:] - timestamp[:-1]) == np.timedelta64(1, "h")
    )
    eligible &= (
        np.isfinite(temperature[1:])
        & np.isfinite(temperature[:-1])
        & np.isfinite(rh[1:])
        & np.isfinite(rh[:-1])
    )
    transition_city = city_index[1:]
    total_by_city = np.bincount(transition_city[eligible], minlength=len(cities))
    if not (total_by_city > 0).all():
        raise ValueError("At least one location has no eligible consecutive-hour transition")
    total = int(total_by_city.sum())

    def coverage(t_low: float, t_high: float, rh_low: float, rh_high: float):
        states = (
            (temperature >= t_low)
            & (temperature <= t_high)
            & (rh >= rh_low)
            & (rh <= rh_high)
        )
        transitions = states[1:] & states[:-1] & eligible
        by_city = np.bincount(transition_city[transitions], minlength=len(cities))
        return float(by_city.sum() / total), by_city / total_by_city

    rows = []
    for bound in bounds.itertuples(index=False):
        low, reference, high = float(bound.Tlow), float(bound.Tref), float(bound.Thigh)
        for branch, t_low, t_high in (
            ("lower", low, reference),
            ("upper", reference, high),
        ):
            first = rh_by_temperature[(_normalise_material(bound.material), t_low)]
            second = rh_by_temperature[(_normalise_material(bound.material), t_high)]
            rh_low = max(first[0], second[0])
            rh_high = min(first[1], second[1])
            if rh_low >= rh_high:
                raise ValueError(f"Empty endpoint RH intersection for {bound.material} {branch}")
            baseline, baseline_by_city = coverage(t_low, t_high, rh_low, rh_high)
            for direction in EXTENSIONS:
                candidates = {
                    "T_low_minus_5C": (t_low - 5, t_high, rh_low, rh_high),
                    "T_high_plus_5C": (t_low, t_high + 5, rh_low, rh_high),
                    "RH_low_minus_5pp": (t_low, t_high, max(0, rh_low - 5), rh_high),
                    "RH_high_plus_5pp": (t_low, t_high, rh_low, min(100, rh_high + 5)),
                }
                candidate, candidate_by_city = coverage(*candidates[direction])
                location_gain = (candidate_by_city - baseline_by_city) * 100
                rows.append(
                    {
                        "material": bound.material,
                        "branch": branch,
                        "T_low": t_low,
                        "T_high": t_high,
                        "RH_low": rh_low,
                        "RH_high": rh_high,
                        "extension": direction,
                        "baseline_transition_coverage": baseline,
                        "candidate_transition_coverage": candidate,
                        "gain_percentage_points": (candidate - baseline) * 100,
                        "median_location_gain_pp": float(np.median(location_gain)),
                        "max_location_gain_pp": float(np.max(location_gain)),
                    }
                )
    return pd.DataFrame(rows), {
        "weather_rows": int(len(weather)),
        "locations": int(len(cities)),
        "eligible_transitions": total,
    }

