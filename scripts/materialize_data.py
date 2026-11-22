#!/usr/bin/env python
"""Materialize the self-contained compressed inputs shipped with the repository."""

from __future__ import annotations

import argparse
import gzip
import hashlib
import shutil
import zipfile
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--root", type=Path, default=ROOT)
    parser.add_argument("--force", action="store_true")
    args = parser.parse_args()

    archives = args.root / "data" / "archives"
    weather_out = args.root / "data" / "weather" / "MAIN_climate_hourly_2015_2024.csv"
    solar_out = args.root / "data" / "padac" / "nasa_chunks"
    weather_out.parent.mkdir(parents=True, exist_ok=True)
    solar_out.mkdir(parents=True, exist_ok=True)

    if args.force or not weather_out.exists():
        with gzip.open(archives / "MAIN_climate_hourly_2015_2024.csv.gz", "rb") as source:
            with weather_out.open("wb") as destination:
                shutil.copyfileobj(source, destination, 1024 * 1024)
    with zipfile.ZipFile(archives / "NASA_POWER_solar_wind_2015_2024_36cities.zip") as archive:
        if args.force or len(list(solar_out.glob("*_POWER_G_WS10M.csv"))) != 360:
            archive.extractall(solar_out)

    print(f"weather={weather_out} bytes={weather_out.stat().st_size} sha256={sha256(weather_out)}")
    print(f"solar_wind_files={len(list(solar_out.glob('*_POWER_G_WS10M.csv')))}")


if __name__ == "__main__":
    main()
