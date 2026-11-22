# Equilibrium Data Coverage and Representation in Weather-Resolved DAC Analysis

This repository is the Python-first reproduction package for the manuscript **Equilibrium Data Coverage and Representation in Weather-Resolved Direct Air Capture Analysis** and its Supporting Information (final closed version, 2026-11-23).

The repository separates four evidence levels:

1. calculations regenerated from hourly weather and equilibrium inputs;
2. regression checks reconstructed from frozen climate-level scores;
3. numerical source-data verification plots;
4. byte- and pixel-identical preservation of the final closed-manuscript artwork.

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
│   ├── reproduce_hn_analysis.py
│   ├── reproduce_figures.py
│   ├── extract_final_artwork.py
│   ├── verify_artwork.py
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

## Materialize the bundled data

The repository contains the complete compressed weather, equilibrium, frozen-summary,
solar/wind and PADAC parameter inputs needed by the public scripts. No private Drive
folder or unpublished archive is required. After cloning, materialize the compressed
weather archives:

```bash
python scripts/materialize_data.py
```

The principal inputs are:

- `MAIN_climate_hourly_2015_2024.csv` (3,156,192 hourly rows; 36 locations);
- `MAIN_material_support_bounds.csv`;
- `MAIN_climate_H_scores.csv` (2,826 location-level H, H/N and N rows);
- `MAIN_equilibrium_dataset_master.xlsx`;
- 360 NASA POWER solar-irradiance and wind files used by the PADAC calculation;
- the ImCOF-TAEA TPD kernel, frozen PADAC configuration and human-readable 13X thermal-property JSON.

Compressed and materialized-file hashes are documented in `data/README.md`,
`config/data_manifest.csv` and `validation/input_sha256.csv`. Frozen summary
tables are retained only where a calculation starts from a validated intermediate, and
each case is labeled in the manifest and output metadata.

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

The H/N target recomputes the 2,826 location-level ratios, all 108 material-panel
Kendall coefficients, the manuscript partial-Kendall statistic controlling for N, and
the 12 medians reported in SI Table S6. The IRA target reconstructs all strict H/Y
location-pair classes from saved climate-level scores.

The H/N calculation can also be run independently:

```bash
python scripts/reproduce_hn_analysis.py \
  --input-file data/frozen/MAIN_climate_H_scores.csv \
  --output-dir results/tables
```

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

These commands create numerical verification plots for final manuscript Figures 2-7 and current SI Figures S3 and S5-S7. Figure 1 is a conceptual analysis diagram and is not a numerical output. Numerical plots are deliberately kept separate from the final submission artwork.

## Reproduce the PADAC solar-regeneration calculation

The publication-scale PADAC calculation is restartable by city. It uses two workers by
default because each `nz=20` city integration is memory- and CPU-intensive:

```bash
python scripts/reproduce_padac_all.py --workers 2 --nz 20
python scripts/verify_padac_solar.py
```

Individual cities can be run with `scripts/reproduce_padac_city.py CITY --nz 20`.
The final verifier requires all 36 city JSON files, retains the 30 evaluable modeled
locations, reconstructs all 435 strict location pairs, and tests the manuscript's
solar-regeneration result of 13 Y-only reversals and zero joint H/Y reversals.

## Preserve and verify the final artwork exactly

The canonical PNG byte streams embedded in the final closed DOCX files are retained in
`validation/reference_artwork`. Re-extract them from the submitted documents and require
both SHA-256 and every RGBA pixel to match:

```bash
python scripts/extract_final_artwork.py \
  --manuscript Manuscript_Coverage_Representation_DAC_submission_20261123j.docx \
  --supporting-information Supporting_Information_Coverage_Representation_DAC_final_20261123g.docx \
  --output-dir results/final_artwork

python scripts/verify_artwork.py \
  --candidate-dir results/final_artwork
```

For the latest submission files, all nine tracked artwork PNG streams match the canonical
reference files by SHA-256. Figure 3 was refreshed from the latest manuscript DOCX; the
other eight streams were unchanged. Byte identity also implies zero differing decoded
pixels for the stored PNG artwork.

This is an artwork-preservation check, not a substitute for scientific recalculation.
The independent calculation path remains the table and numerical-figure workflow above.

## Test and verify

```bash
pytest
python scripts/verify_frozen.py --input-dir data/frozen --output-dir results/verification
```

Synthetic unit tests cover interpolation support, H definitions, pairwise reversal classes, LDF propagation, material-specific release endpoints, ice-saturation RH limits, and boundary-state counting. Full-data regression results and tolerances are summarized in `VALIDATION.md`.

## Reproducibility boundary

Core H, coverage, IRA Y, whole-range ImCOF H, fixed-80 degC ImCOF Y, and pair classifications were independently regenerated to numerical tolerance. The 10-year, `nz=20` PADAC thermal rerun is computationally expensive and is reported separately with city-level status. Frozen PADAC scores are used only where explicitly labeled.

## Citation and license

Citation metadata are provided in `CITATION.cff` and `.zenodo.json`. The code is released under the MIT
License; source-data attribution and reuse notes are recorded in `data/README.md` and
`PROVENANCE.md`. Add the final article DOI to `CITATION.cff` after publication.
