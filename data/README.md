# Data placement and integrity

Large scientific inputs are not committed to Git. Preserve the canonical filenames and do not edit source files in place.

Use these locations:

- `data/weather/`: `MAIN_climate_hourly_2015_2024.csv`;
- `data/equilibrium/`: equilibrium master workbook and material bounds;
- `data/frozen/`: validated regression comparators and summary tables;
- `data/reference/`: small manuscript-level reference values committed with the code.

For the simple command lines in the root README, links or copies may be placed together in `data/frozen/`. The complete inventory and regeneration level are in `config/data_manifest.csv`.

Before a full run, compare input SHA-256 values against `validation/input_sha256.csv`. The reproduction commands never overwrite canonical inputs.
