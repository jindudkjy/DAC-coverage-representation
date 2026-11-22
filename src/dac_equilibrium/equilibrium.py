"""Equilibrium representations used by the manuscript calculations.

The implementation intentionally performs no extrapolation. Temperature-resolved
values use piecewise-linear interpolation between every measured temperature
slice in the requested branch. RH interpolation is linear within each slice.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Literal

import numpy as np
import pandas as pd

Branch = Literal["lower", "upper"]


@dataclass(frozen=True)
class DomainBounds:
    temperature_low_c: float
    temperature_reference_c: float
    temperature_high_c: float
    rh_low_pct: float
    rh_high_pct: float

    def temperature_limits(self, branch: Branch | None = None) -> tuple[float, float]:
        if branch == "lower":
            return self.temperature_low_c, self.temperature_reference_c
        if branch == "upper":
            return self.temperature_reference_c, self.temperature_high_c
        if branch is None:
            return self.temperature_low_c, self.temperature_high_c
        raise ValueError(f"Unknown branch: {branch}")


class EquilibriumSurface:
    """Single-isotherm and temperature-resolved views of one material."""

    def __init__(
        self,
        equilibrium: pd.DataFrame,
        bounds: DomainBounds,
        *,
        temperature_column: str = "T_C",
        rh_column: str = "RH_pct",
        loading_column: str = "q_mmol_g",
    ) -> None:
        required = {temperature_column, rh_column, loading_column}
        missing = required.difference(equilibrium.columns)
        if missing:
            raise ValueError(f"Missing equilibrium columns: {sorted(missing)}")

        frame = equilibrium[[temperature_column, rh_column, loading_column]].copy()
        frame.columns = ["temperature_c", "rh_pct", "loading"]
        for column in frame:
            frame[column] = pd.to_numeric(frame[column], errors="coerce")
        frame = frame.dropna().sort_values(["temperature_c", "rh_pct"])
        if frame.duplicated(["temperature_c", "rh_pct"], keep=False).any():
            duplicate = frame[frame.duplicated(["temperature_c", "rh_pct"], keep=False)]
            raise ValueError(f"Duplicate equilibrium knots are ambiguous:\n{duplicate}")

        self.frame = frame.reset_index(drop=True)
        self.bounds = bounds
        lo, hi = bounds.temperature_limits()
        self.temperatures = np.array(
            sorted(t for t in frame.temperature_c.unique() if lo <= t <= hi), dtype=float
        )
        if not np.any(np.isclose(self.temperatures, bounds.temperature_reference_c)):
            raise ValueError("Reference-temperature isotherm is missing")

    def _slice(self, temperature_c: float) -> tuple[np.ndarray, np.ndarray]:
        selected = self.frame[
            np.isclose(self.frame.temperature_c.to_numpy(float), temperature_c, atol=1e-9, rtol=0)
        ]
        if selected.empty:
            raise ValueError(f"No equilibrium slice at {temperature_c:g} degC")
        return selected.rh_pct.to_numpy(float), selected.loading.to_numpy(float)

    @staticmethod
    def _interpolate_rh(
        rh_pct: np.ndarray, knots_rh: np.ndarray, knots_loading: np.ndarray
    ) -> np.ndarray:
        rh_pct = np.asarray(rh_pct, dtype=float)
        output = np.full(rh_pct.shape, np.nan, dtype=float)
        valid = (
            np.isfinite(rh_pct)
            & (rh_pct >= knots_rh.min())
            & (rh_pct <= knots_rh.max())
        )
        output[valid] = np.interp(rh_pct[valid], knots_rh, knots_loading)
        return output

    def single_isotherm(
        self,
        rh_pct: np.ndarray,
        temperature_c: np.ndarray | None = None,
        *,
        branch: Branch | None = None,
    ) -> np.ndarray:
        """Evaluate the reference-temperature isotherm without extrapolation."""
        rh_pct = np.asarray(rh_pct, dtype=float)
        knots_rh, knots_loading = self._slice(self.bounds.temperature_reference_c)
        output = self._interpolate_rh(rh_pct, knots_rh, knots_loading)
        output[(rh_pct < self.bounds.rh_low_pct) | (rh_pct > self.bounds.rh_high_pct)] = np.nan
        if temperature_c is not None:
            temperature_c = np.asarray(temperature_c, dtype=float)
            if temperature_c.shape != rh_pct.shape:
                raise ValueError("temperature_c and rh_pct must have the same shape")
            lo, hi = self.bounds.temperature_limits(branch)
            output[(temperature_c < lo) | (temperature_c > hi)] = np.nan
        return output

    def temperature_resolved(
        self,
        temperature_c: np.ndarray,
        rh_pct: np.ndarray,
        *,
        branch: Branch | None = None,
    ) -> np.ndarray:
        """Interpolate q(RH,T) between adjacent measured temperature slices."""
        temperature_c = np.asarray(temperature_c, dtype=float)
        rh_pct = np.asarray(rh_pct, dtype=float)
        if temperature_c.shape != rh_pct.shape:
            raise ValueError("temperature_c and rh_pct must have the same shape")

        lo, hi = self.bounds.temperature_limits(branch)
        temperatures = self.temperatures[
            (self.temperatures >= lo) & (self.temperatures <= hi)
        ]
        if len(temperatures) < 2 or not np.isclose(temperatures[[0, -1]], [lo, hi]).all():
            raise ValueError(
                f"Measured temperature slices do not span {branch or 'full'} domain: {temperatures}"
            )

        output = np.full(temperature_c.shape, np.nan, dtype=float)
        for index, (t0, t1) in enumerate(zip(temperatures[:-1], temperatures[1:])):
            rh0, q0 = self._slice(float(t0))
            rh1, q1 = self._slice(float(t1))
            q0_at_rh = self._interpolate_rh(rh_pct, rh0, q0)
            q1_at_rh = self._interpolate_rh(rh_pct, rh1, q1)
            in_temperature = (temperature_c >= t0) & (
                (temperature_c < t1)
                if index < len(temperatures) - 2
                else (temperature_c <= t1)
            )
            valid = (
                in_temperature
                & np.isfinite(temperature_c)
                & np.isfinite(rh_pct)
                & np.isfinite(q0_at_rh)
                & np.isfinite(q1_at_rh)
                & (rh_pct >= self.bounds.rh_low_pct)
                & (rh_pct <= self.bounds.rh_high_pct)
            )
            weight = (temperature_c[valid] - t0) / (t1 - t0)
            output[valid] = (1.0 - weight) * q0_at_rh[valid] + weight * q1_at_rh[valid]
        return output

