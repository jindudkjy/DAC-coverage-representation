# Equilibrium Data Coverage and Representation in Weather-Resolved DAC Analysis

This repository is the Python-first reproduction package for the manuscript **Equilibrium Data Coverage and Representation in Weather-Resolved Direct Air Capture Analysis** and its Supporting Information (final closed version, 2026-11-23).

The repository separates three evidence levels:

1. calculations regenerated from hourly weather and equilibrium inputs;
2. regression checks reconstructed from frozen climate-level scores;
3. source-data verification plots that are not pixel-identical copies of journal artwork.

## Main questions reproduced

- What fraction of hourly weather states and transitions lies inside each measured `q(RH,T)` domain?
- How do 5 degC temperature-boundary and 5 percentage-point RH-boundary extensions change coverage?
- Does the lower-temperature RH-extension advantage remain when subzero RH is capped at ice saturation?
- How does replacing a single isotherm with a temperature-resolved representation change cumulative equilibrium-loading variation `H` and location ordering?
- Do equilibrium-ordering changes carry through prescribed LDF response times and modeled-release scores for IRA-900-C and ImCOF-TAEA?

## Scientific definitions retained

- A weather state is covered only when temperature and RH are inside the measured interval-specific domain.
- A transition is covered only when both consecutive states are covered and separated by one hour for native-hour calculations.
- `H = 0.5 * sum(abs(delta q*))` over covered transitions.
- The relative H difference is `abs(H_single - H_TR) / H_TR`.
- Temperature-resolved loading is interpolated within the measured RH-temperature domain without silent extrapolation.
- NASA POWER RH2M is treated as water-referenced. The conservative subzero sensitivity uses `RH_cap = min(RH, 100 e_si/e_sw)` with Murphy-Koop saturation-vapor-pressure expressions.
- IRA and ImCOF modeled-release scores use different definitions and are never pooled.

## Repository layout

```text
DAC-coverage-representation/
├── README.md
├── VALIDATION.md
├── pyproject.toml
├── requirements.txt
├── config/data_manifest.csv
├── data/
│   ├── README.md
│   ├── reference/
│   ├── equilibrium/
│   ├── weather/
│   └── frozen/
├── src/dac_equilibrium/
├── scripts/
│   ├── reproduce_tables.py
│   ├── reproduce_figures.py
│   └── verify_frozen.py
├── notebooks/reproduce_manuscript.ipynb
├── tests/
└── validation/
```

## Installation

Python 3.11 or later is recommended.

```bash
python -m venv .venv
source .venv/bin/activate  # Windows: .venv\Scripts\activate
python -m pip install --upgrade pip
python -m pip install -e ".[dev]"
```

## Required data

Large hourly weather and source-controlled scientific inputs are not duplicated in Git. Obtain them from the archived manuscript reproducibility package, verify their SHA-256 values, and place them as described in `data/README.md` and `config/data_manifest.csv`.

The principal raw inputs are:

- `MAIN_climate_hourly_2015_2024.csv` (3,156,192 hourly rows; 36 locations);
- `MAIN_material_support_bounds.csv`;
- `MAIN_equilibrium_dataset_master.xlsx`.

Frozen summary tables are retained only where a full calculation starts from a validated intermediate. Each such case is labeled in the manifest and output metadata.

## Reproduce tables

```bash
python scripts/reproduce_tables.py \
  --input-dir data/frozen \
  --output-dir results/tables \
  --target all
```

The coverage target regenerates:

- native-hour single-boundary coverage extensions;
- pooled lower-temperature RH distributions;
- immediate RH and cold-boundary state counts;
- the ice-saturation-capped coverage sensitivity.

The IRA target reconstructs all strict H/Y location-pair classes from saved climate-level scores.

## Reproduce numerical figure content

```bash
python scripts/reproduce_figures.py \
  --input-dir data/frozen \
  --weather-file data/weather/MAIN_climate_hourly_2015_2024.csv \
  --output-dir results/figures

python scripts/reproduce_si_figures.py \
  --input-dir data/frozen \
  --output-dir results/si_figures
```

These commands create numerical verification plots for final manuscript Figures 2-7 and SI Figures S5-S7. Figure 1 is a conceptual analysis diagram and is not a numerical output. The generated plots preserve source values and trends but do not claim pixel-identical typography, annotation placement, or panel styling.

## Test and verify

```bash
pytest
python scripts/verify_frozen.py --input-dir data/frozen --output-dir results/verification
```

Synthetic unit tests cover interpolation support, H definitions, pairwise reversal classes, LDF propagation, material-specific release endpoints, ice-saturation RH limits, and boundary-state counting. Full-data regression results and tolerances are summarized in `VALIDATION.md`.

## Reproducibility boundary

Core H, coverage, IRA Y, whole-range ImCOF H, fixed-80 degC ImCOF Y, and pair classifications were independently regenerated to numerical tolerance. The 10-year, `nz=20` PADAC thermal rerun is computationally expensive and is reported separately with city-level status. Frozen PADAC scores are used only where explicitly labeled.

## Citation and license

Add the final article citation and repository DOI after publication. No software license has been selected; the repository owner should add the intended license before third-party reuse.
