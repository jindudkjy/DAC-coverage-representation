#!/usr/bin/env python
"""Reintegrate the 2015-2024 PADAC solar-regeneration model for one city."""

from __future__ import annotations

import argparse
import json
import pickle
import time
from pathlib import Path

import numpy as np
import pandas as pd

from dac_equilibrium import padac_core


ROOT = Path(__file__).resolve().parents[1]


def load_weather(city: str, weather_file: Path, solar_wind_dir: Path, config: dict) -> pd.DataFrame:
    pieces = []
    use = ["city", "timestamp_utc", "temperature_C", "RH_pct"]
    for chunk in pd.read_csv(weather_file, usecols=use, chunksize=200_000):
        selected = chunk[chunk.city == city]
        if len(selected):
            pieces.append(selected)
    if not pieces:
        raise ValueError(f"Unknown city: {city}")
    weather = pd.concat(pieces, ignore_index=True)
    weather["timestamp"] = pd.to_datetime(weather.pop("timestamp_utc"), utc=True)
    weather = weather.rename(columns={"temperature_C": "T_C"})
    forcing = []
    for year in range(2015, 2025):
        item = pd.read_csv(solar_wind_dir / f"{city}_{year}_POWER_G_WS10M.csv", usecols=["timestamp", "G_Wm2", "v_ms"])
        item["timestamp"] = pd.to_datetime(item.timestamp, utc=True)
        forcing.append(item)
    weather = weather.merge(pd.concat(forcing, ignore_index=True), on="timestamp", how="left", validate="one_to_one")
    if weather[["G_Wm2", "v_ms"]].isna().any().any():
        raise AssertionError("Missing solar or wind forcing after timestamp join")
    weather = weather.sort_values("timestamp").reset_index(drop=True)
    weather["local"] = weather.timestamp.dt.tz_convert(config["WEATHER_CITY_TIMEZONES"][city]).dt.tz_localize(None)
    return weather


def q_function(equilibrium_file: Path):
    data = pd.read_excel(equilibrium_file, sheet_name="07_ANALYSIS_EXPORT", header=2)
    data = data[data.material == "ImCOF-TAEA"].copy()
    for column in ["T_C", "RH_pct", "q_mmol_g"]:
        data[column] = pd.to_numeric(data[column])
    temperatures = sorted(data.T_C.unique())
    curves = {
        float(temperature): (group.RH_pct.to_numpy(float), group.q_mmol_g.to_numpy(float))
        for temperature, group in data.sort_values("RH_pct").groupby("T_C")
    }

    def calculate(temperature, rh, representation):
        temperature = np.asarray(temperature, float)
        rh = np.asarray(rh, float)
        loading = np.full(temperature.shape, np.nan)
        valid = np.isfinite(temperature) & np.isfinite(rh) & (temperature >= -20) & (temperature <= 25) & (rh >= 0) & (rh <= 70)
        if representation == "single":
            x, y = curves[5.0]
            loading[valid] = np.interp(rh[valid], x, y)
            return loading
        for index, (low, high) in enumerate(zip(temperatures[:-1], temperatures[1:])):
            mask = valid & (temperature >= low) & (temperature < high if index < len(temperatures) - 2 else temperature <= high)
            if not mask.any():
                continue
            x0, y0 = curves[float(low)]
            x1, y1 = curves[float(high)]
            q0 = np.interp(rh[mask], x0, y0)
            q1 = np.interp(rh[mask], x1, y1)
            weight = (temperature[mask] - low) / (high - low)
            loading[mask] = (1 - weight) * q0 + weight * q1
        return loading

    return calculate


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("city")
    parser.add_argument("--nz", type=int, default=20)
    parser.add_argument("--weather-file", type=Path, default=ROOT / "data/weather/MAIN_climate_hourly_2015_2024.csv")
    parser.add_argument("--solar-wind-dir", type=Path, default=ROOT / "data/padac/nasa_chunks")
    parser.add_argument("--equilibrium-file", type=Path, default=ROOT / "data/equilibrium/MAIN_equilibrium_dataset_master.xlsx")
    parser.add_argument("--config", type=Path, default=ROOT / "data/padac/frozen_config.json")
    parser.add_argument("--tpd-kernel", type=Path, default=ROOT / "data/padac/ImCOF_TPD_kernel.csv")
    parser.add_argument("--sorbent", type=Path, default=ROOT / "data/padac/padac_sorbent_13X.pkl.bin")
    parser.add_argument("--reference-scores", type=Path, default=ROOT / "data/frozen/ImCOF_wholeH_wholeY_aligned_climate_scores.csv")
    parser.add_argument("--output-dir", type=Path, default=ROOT / "results/padac")
    args = parser.parse_args()
    args.output_dir.mkdir(parents=True, exist_ok=True)
    result_path = args.output_dir / f"{args.city}_primary_nz{args.nz}.json"
    if result_path.exists():
        print(result_path.read_text(encoding="utf-8"))
        return

    config = json.loads(args.config.read_text(encoding="utf-8"))
    weather = load_weather(args.city, args.weather_file, args.solar_wind_dir, config)
    setting = next(value for value in config["THERMAL_VARIANTS"] if value["id"] == "primary")
    sorbent = pickle.loads(args.sorbent.read_bytes())
    parameters = padac_core.padac_params(config, sorbent, setting)
    elapsed = (weather.timestamp - weather.timestamp.iloc[0]).dt.total_seconds().to_numpy(float)
    flow, _ = padac_core.cycle_labels(weather.local, 18, 8)
    forcing = padac_core.Forcing(elapsed, weather.T_C.to_numpy(float) + 273.15, weather.G_Wm2.to_numpy(float), weather.v_ms.to_numpy(float), flow)
    started = time.monotonic()
    thermal = padac_core.PadacModel(parameters, nz=args.nz).run_optimized(forcing, chunk_hours=744)
    solver_seconds = time.monotonic() - started

    cycles = padac_core.imcof_cycles(weather.local.values, weather.T_C.to_numpy(float), weather.RH_pct.to_numpy(float), 18, 8, "end_of_window")
    calculate_q = q_function(args.equilibrium_file)
    q_single = calculate_q(cycles.T_ads, cycles.RH_ads, "single")
    q_tensor = calculate_q(cycles.T_ads, cycles.RH_ads, "tensor")
    common = np.isfinite(q_single) & np.isfinite(q_tensor)
    kernel = pd.read_csv(args.tpd_kernel)
    metadata = kernel[["curve_id", "T_ads_C", "RH_ads_pct"]].drop_duplicates().reset_index(drop=True)
    by_id = {key: group.sort_values("T_C") for key, group in kernel.groupby("curve_id")}
    curve_ids = []
    for temperature, rh in zip(cycles.T_ads, cycles.RH_ads):
        distance = np.sqrt(((metadata.T_ads_C - temperature) / config["TPD_T_SCALE_C"]) ** 2 + ((metadata.RH_ads_pct - rh) / config["TPD_RH_SCALE_PCT"]) ** 2)
        curve_ids.append(metadata.loc[int(np.argmin(distance)), "curve_id"])
    bed_temperature = thermal.T_s_mean_C.to_numpy(float)
    regeneration_temperature = np.array([bed_temperature[index].max() for index in cycles.reg_idx], float)
    release_fraction = np.array([
        np.interp(value, by_id[curve_id].T_C, by_id[curve_id].F_R, left=0, right=by_id[curve_id].F_R.iloc[-1])
        for curve_id, value in zip(curve_ids, regeneration_temperature)
    ])
    common &= np.isfinite(release_fraction)
    y_single = float(np.mean(q_single[common] * release_fraction[common])) if common.any() else np.nan
    y_tensor = float(np.mean(q_tensor[common] * release_fraction[common])) if common.any() else np.nan
    reference = pd.read_csv(args.reference_scores)
    reference = reference[(reference.climate == args.city) & (reference.operating_mode == "environmental_PADAC13X")].set_index("representation")
    output = {
        "city": args.city,
        "nz": args.nz,
        "hours": len(weather),
        "cycles": len(cycles),
        "supported_cycles": int(common.sum()),
        "Y_single": y_single,
        "Y_tensor": y_tensor,
        "peak_Ts_C": float(bed_temperature.max()),
        "solver_seconds": solver_seconds,
        "reference_available": len(reference) == 2,
    }
    if len(reference) == 2:
        output.update({
            "Y_single_reference": float(reference.loc["single", "Y"]),
            "Y_tensor_reference": float(reference.loc["tensor", "Y"]),
            "Y_single_error": y_single - float(reference.loc["single", "Y"]),
            "Y_tensor_error": y_tensor - float(reference.loc["tensor", "Y"]),
            "supported_cycles_reference": int(reference.loc["single", "n_supported_cycles"]),
        })
    result_path.write_text(json.dumps(output, indent=2), encoding="utf-8")
    print(json.dumps(output, indent=2))


if __name__ == "__main__":
    main()
