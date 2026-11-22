# Data placement integrity and reuse

The repository is self-contained. Run `python scripts/materialize_data.py` after cloning.
It expands the bundled archives without modifying their canonical contents.

- `data/archives/MAIN_climate_hourly_2015_2024.csv.gz` contains the canonical 36-location temperature/RH record. The materialized CSV has 249,118,498 bytes and SHA-256 `e69557396811e1a82264e41b1932e91c4cc06332bb00dcaa20232248e8618124`.
- `data/archives/NASA_POWER_solar_wind_2015_2024_36cities.zip` contains 360 annual solar-irradiance and wind files for the PADAC calculation.
- `data/equilibrium/` contains the equilibrium master workbook and material-support bounds.
- `data/frozen/` contains validated regression comparators and climate-level panels, including the complete 2,826-row H/H-N/N panel used for SI Table S6 and Figure 3b.
- `data/padac/` contains the frozen PADAC configuration, ImCOF-TAEA TPD release kernel and human-readable `padac_sorbent_13X.json` thermal-property object.
- `data/reference/` contains small manuscript-level reference values.

NASA POWER meteorological data are redistributed with source attribution to the NASA
Langley Research Center POWER project. Equilibrium and TPD values retain the literature
provenance recorded in `PROVENANCE.md`; the repository's MIT license applies to software
and does not replace the terms of the cited source publications.

Before a full run, compare input hashes against `validation/input_sha256.csv` and the
archive manifest. Reproduction commands write only to `results/`.
