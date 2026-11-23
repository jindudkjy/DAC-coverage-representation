"""End-to-end reconstruction of the location-level equilibrium H panel."""

from __future__ import annotations

from pathlib import Path

import numpy as np
import pandas as pd

from .equilibrium import DomainBounds, EquilibriumSurface
from .metrics import trajectory_scores


MATERIAL_NAME_MAP = {
    "Al2O3-TEPA(20)": "Al2O3_TEPA(20)",
    "MIL-101(Cr)-TEPA(30)": "MIL-101(Cr)_TEPA(30)",
    "Mg0.55Al-CO3-PEI(30)": "Mg0.55Al-CO3_PEI(30)",
}

TEMPORAL_MODES: dict[str, tuple[str, int]] = {
    "subsample_1h": ("subsample", 1),
    "subsample_3h": ("subsample", 3),
    "subsample_6h": ("subsample", 6),
    "subsample_24h": ("subsample", 24),
    "average_6h": ("average", 6),
    "average_24h": ("average", 24),
}


def load_equilibrium_export(path: Path) -> pd.DataFrame:
    """Locate and read the canonical material/T/RH/q worksheet."""
    required = {"material", "T_C", "RH_pct", "q_mmol_g"}
    workbook = pd.ExcelFile(path)
    selected_sheet: str | None = None
    selected_header: int | None = None
    for sheet in workbook.sheet_names:
        preview = pd.read_excel(path, sheet_name=sheet, header=None, nrows=20)
        for index in range(len(preview)):
            values = {str(value).strip() for value in preview.iloc[index] if pd.notna(value)}
            if required.issubset(values):
                selected_sheet = sheet
                selected_header = index
                break
        if selected_sheet is not None:
            break
    if selected_sheet is None or selected_header is None:
        raise ValueError(f"Could not locate equilibrium export columns: {sorted(required)}")
    frame = pd.read_excel(path, sheet_name=selected_sheet, header=selected_header)
    frame = frame.dropna(axis=1, how="all").dropna(axis=0, how="all").copy()
    frame.columns = [str(column).strip() for column in frame.columns]
    missing = required.difference(frame.columns)
    if missing:
        raise ValueError(f"Missing equilibrium columns: {sorted(missing)}")
    frame["material"] = frame["material"].replace(MATERIAL_NAME_MAP)
    for column in ("T_C", "RH_pct", "q_mmol_g"):
        frame[column] = pd.to_numeric(frame[column], errors="coerce")
    if frame[["material", "T_C", "RH_pct", "q_mmol_g"]].isna().any().any():
        raise ValueError("Equilibrium export contains missing required values")
    return frame


def build_surfaces(
    equilibrium: pd.DataFrame, bounds: pd.DataFrame
) -> dict[str, EquilibriumSurface]:
    """Build the manuscript single-isotherm and measured-slice surfaces."""
    required = {"material", "Tlow", "Tref", "Thigh", "Rmin", "Rmax"}
    missing = required.difference(bounds.columns)
    if missing:
        raise ValueError(f"Missing material-bound columns: {sorted(missing)}")
    surfaces: dict[str, EquilibriumSurface] = {}
    for row in bounds.itertuples(index=False):
        material = str(row.material)
        selected = equilibrium[equilibrium["material"] == material]
        if selected.empty:
            raise ValueError(f"No equilibrium rows for {material}")
        surfaces[material] = EquilibriumSurface(
            selected,
            DomainBounds(
                temperature_low_c=float(row.Tlow),
                temperature_reference_c=float(row.Tref),
                temperature_high_c=float(row.Thigh),
                rh_low_pct=float(row.Rmin),
                rh_high_pct=float(row.Rmax),
            ),
        )
    extra = set(equilibrium["material"].unique()).difference(surfaces)
    if extra:
        raise ValueError(f"Equilibrium materials missing from bounds: {sorted(extra)}")
    return surfaces


def temporal_trajectory(city_weather: pd.DataFrame, mode: str) -> pd.DataFrame:
    """Apply the frozen positional-subsampling or UTC-block-average convention."""
    kind, hours = TEMPORAL_MODES[mode]
    group = city_weather.sort_values("timestamp_utc", kind="mergesort").copy()
    if kind == "subsample":
        return group.iloc[::hours][["temperature_C", "RH_pct"]].reset_index(drop=True)
    return (
        group.set_index("timestamp_utc")[["temperature_C", "RH_pct"]]
        .resample(f"{hours}h")
        .mean()
        .dropna()
        .reset_index(drop=True)
    )


def reconstruct_h_panel(
    weather_file: Path,
    equilibrium_file: Path,
    bounds_file: Path,
) -> pd.DataFrame:
    """Recreate all location-level H, H_RH and common-transition N values."""
    equilibrium = load_equilibrium_export(equilibrium_file)
    bounds = pd.read_csv(bounds_file)
    surfaces = build_surfaces(equilibrium, bounds)

    columns = ["climate_class", "city", "timestamp_utc", "temperature_C", "RH_pct"]
    weather = pd.read_csv(weather_file, usecols=columns, parse_dates=["timestamp_utc"])
    for column in ("temperature_C", "RH_pct"):
        weather[column] = pd.to_numeric(weather[column], errors="coerce")
    city_order = weather["city"].drop_duplicates().tolist()
    class_counts = weather.groupby("city", sort=False)["climate_class"].nunique(dropna=False)
    if not (class_counts == 1).all():
        raise ValueError("climate_class must be unique within each city")

    records: list[dict[str, float | int | str]] = []
    for city in city_order:
        city_weather = weather[weather["city"] == city]
        climate_class = str(city_weather["climate_class"].iloc[0])
        for mode in TEMPORAL_MODES:
            trajectory = temporal_trajectory(city_weather, mode)
            temperature = trajectory["temperature_C"].to_numpy(float)
            rh = trajectory["RH_pct"].to_numpy(float)
            for material, surface in surfaces.items():
                single = surface.single_isotherm(rh)
                for branch in ("lower", "upper"):
                    resolved = surface.temperature_resolved(temperature, rh, branch=branch)
                    score = trajectory_scores(single, resolved, rh)
                    if int(score["N"]) == 0:
                        continue
                    records.append(
                        {
                            "material": material,
                            "branch": branch,
                            "temporal_mode": mode,
                            "climate_class": climate_class,
                            "city": city,
                            "H_single": score["H_single"],
                            "H_tensor": score["H_tensor"],
                            "H_RH": score["H_RH"],
                            "N": score["N"],
                        }
                    )

    panel = pd.DataFrame(records)
    material_order = {name: index for index, name in enumerate(bounds["material"])}
    temporal_order = {name: index for index, name in enumerate(TEMPORAL_MODES)}
    climate_order = {name: index for index, name in enumerate(city_order)}
    panel["_material_order"] = panel["material"].map(material_order)
    panel["_branch_order"] = panel["branch"].map({"lower": 0, "upper": 1})
    panel["_temporal_order"] = panel["temporal_mode"].map(temporal_order)
    panel["_climate_order"] = panel["city"].map(climate_order)
    panel = panel.sort_values(
        ["_material_order", "_branch_order", "_temporal_order", "_climate_order"],
        kind="mergesort",
    ).drop(columns=["_material_order", "_branch_order", "_temporal_order", "_climate_order"])
    return panel.reset_index(drop=True)
