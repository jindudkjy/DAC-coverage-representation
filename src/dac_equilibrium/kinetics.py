"""Linear-driving-force propagation used in the kinetic sensitivity analyses."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Literal

import numpy as np

GapMode = Literal["hold", "boundary_capped"]


@dataclass(frozen=True)
class LDFResult:
    H_tensor_ldf: float
    H_single_ldf: float
    H_tensor_equilibrium: float
    H_single_equilibrium: float
    n_scored: int


def _rate_per_hour(
    temperature_c: float,
    tau_h: float,
    activation_energy_kj_mol: float,
    reference_temperature_c: float,
) -> float:
    if tau_h <= 0:
        raise ValueError("tau_h must be positive")
    reference_rate = 1.0 / tau_h
    if activation_energy_kj_mol == 0:
        return reference_rate
    gas_constant = 8.314462618
    energy = activation_energy_kj_mol * 1000.0
    temperature_k = temperature_c + 273.15
    reference_k = reference_temperature_c + 273.15
    return float(reference_rate * np.exp(-(energy / gas_constant) * (1 / temperature_k - 1 / reference_k)))


def propagate_ldf(
    target: np.ndarray,
    *,
    tau_h: float = 1.0,
    temperature_c: np.ndarray | None = None,
    activation_energy_kj_mol: float = 0.0,
    reference_temperature_c: float = 25.0,
    supported: np.ndarray | None = None,
    gap_mode: GapMode = "hold",
) -> np.ndarray:
    """Propagate q toward q* using exact exponential integration over 1 h steps."""
    target = np.asarray(target, dtype=float)
    if temperature_c is None:
        temperature_c = np.full(target.shape, reference_temperature_c, dtype=float)
    else:
        temperature_c = np.asarray(temperature_c, dtype=float)
    if supported is None:
        supported = np.isfinite(target)
    else:
        supported = np.asarray(supported, dtype=bool)
    if target.shape != temperature_c.shape or target.shape != supported.shape:
        raise ValueError("target, temperature_c, and supported must have the same shape")
    if gap_mode not in {"hold", "boundary_capped"}:
        raise ValueError(f"Unknown gap_mode: {gap_mode}")

    output = np.full(target.shape, np.nan, dtype=float)
    first = np.flatnonzero(supported & np.isfinite(target))
    if not len(first):
        return output
    start = int(first[0])
    output[start] = target[start]
    for index in range(start + 1, len(target)):
        output[index] = output[index - 1]
        active = supported[index] or gap_mode == "boundary_capped"
        if active and np.isfinite(target[index]):
            rate = _rate_per_hour(
                temperature_c[index], tau_h, activation_energy_kj_mol, reference_temperature_c
            )
            alpha = 1.0 - np.exp(-rate)
            output[index] += alpha * (target[index] - output[index])
    return output


def simulate_two_pass_ldf(
    temperature_c: np.ndarray,
    target_tensor: np.ndarray,
    target_single: np.ndarray,
    supported: np.ndarray,
    *,
    tau_h: float,
    activation_energy_kj_mol: float = 0.0,
    reference_temperature_c: float = 25.0,
    gap_mode: GapMode = "hold",
) -> LDFResult:
    """Replay a trajectory twice, using the first pass as periodic spin-up.

    The second pass scores only transitions whose two observed endpoints lie in
    the original supported domain. This matches the frozen LDF implementation.
    """
    temperature_c = np.asarray(temperature_c, dtype=float)
    target_tensor = np.asarray(target_tensor, dtype=float)
    target_single = np.asarray(target_single, dtype=float)
    supported = np.asarray(supported, dtype=bool)
    shape = temperature_c.shape
    if any(array.shape != shape for array in (target_tensor, target_single, supported)):
        raise ValueError("All input arrays must have the same shape")
    if not len(temperature_c):
        return LDFResult(np.nan, np.nan, np.nan, np.nan, 0)

    boundary = gap_mode == "boundary_capped"
    q_tensor = float(target_tensor[0])
    q_single = float(target_single[0])

    def update(index: int, q: float, target: np.ndarray) -> float:
        if supported[index] or boundary:
            rate = _rate_per_hour(
                temperature_c[index], tau_h, activation_energy_kj_mol, reference_temperature_c
            )
            return float(q + (1.0 - np.exp(-rate)) * (target[index] - q))
        return q

    for index in range(1, len(temperature_c)):
        q_tensor = update(index, q_tensor, target_tensor)
        q_single = update(index, q_single, target_single)

    q_tensor = update(0, q_tensor, target_tensor)
    q_single = update(0, q_single, target_single)
    h_tensor = h_single = h_tensor_eq = h_single_eq = 0.0
    n_scored = 0
    for index in range(1, len(temperature_c)):
        old_tensor, old_single = q_tensor, q_single
        q_tensor = update(index, q_tensor, target_tensor)
        q_single = update(index, q_single, target_single)
        if supported[index - 1] and supported[index]:
            h_tensor += 0.5 * abs(q_tensor - old_tensor)
            h_single += 0.5 * abs(q_single - old_single)
            h_tensor_eq += 0.5 * abs(target_tensor[index] - target_tensor[index - 1])
            h_single_eq += 0.5 * abs(target_single[index] - target_single[index - 1])
            n_scored += 1
    return LDFResult(h_tensor, h_single, h_tensor_eq, h_single_eq, n_scored)

