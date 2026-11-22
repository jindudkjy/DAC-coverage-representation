"""Material-specific modeled-release endpoints used in the manuscript."""

from __future__ import annotations

import numpy as np

from .kinetics import propagate_ldf


def ira_modeled_release(
    equilibrium_target: np.ndarray,
    *,
    tau_h: float = 1.0,
    supported: np.ndarray | None = None,
) -> float:
    """IRA-900-C Y: cumulative loading decrease along the 1 h LDF trajectory.

    Unsupported states hold the current loading. The result is modeled moisture-
    driven loading release, not recovered CO2 or process productivity.
    """
    target = np.asarray(equilibrium_target, dtype=float)
    if supported is None:
        supported = np.isfinite(target)
    trajectory = propagate_ldf(target, tau_h=tau_h, supported=supported, gap_mode="hold")
    return float(np.nansum(np.maximum(-np.diff(trajectory), 0.0)))


def imcof_modeled_release(
    rich_loading: np.ndarray,
    release_fraction: np.ndarray,
    *,
    common_supported_cycles: np.ndarray | None = None,
    aggregation: str = "mean",
) -> float:
    """ImCOF-TAEA Y from q_rich times the cycle-specific release fraction.

    Fixed 80 degC and solar-regeneration scenarios differ only in how the release
    fraction is supplied. Both use the same common-support aggregation rule.
    """
    rich_loading = np.asarray(rich_loading, dtype=float)
    release_fraction = np.asarray(release_fraction, dtype=float)
    if rich_loading.shape != release_fraction.shape:
        raise ValueError("rich_loading and release_fraction must have the same shape")
    finite = np.isfinite(rich_loading) & np.isfinite(release_fraction)
    if common_supported_cycles is not None:
        common_supported_cycles = np.asarray(common_supported_cycles, dtype=bool)
        if common_supported_cycles.shape != finite.shape:
            raise ValueError("common_supported_cycles must have the same shape")
        finite &= common_supported_cycles
    values = rich_loading[finite] * release_fraction[finite]
    if not len(values):
        return float("nan")
    if aggregation == "mean":
        return float(np.mean(values))
    if aggregation == "sum":
        return float(np.sum(values))
    raise ValueError("aggregation must be 'mean' or 'sum'")

