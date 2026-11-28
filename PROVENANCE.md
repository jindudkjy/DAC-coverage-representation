# Code and data provenance

## Source assets

- Final submission manuscript and Supporting Information for Jin-young Kang's *Equilibrium Data Coverage and Representation in Weather-Resolved Direct Air Capture Analysis*.
- Google Drive analysis-code archive `02_analysis_code`.
- Google Drive reproduction-code and output archive `08_reproduction_code_and_outputs`.
- Frozen reproducibility package dated 2026-11-19.

## Maintained implementation

The importable code under `src/dac_equilibrium/` preserves the manuscript conventions for measured-domain coverage, interval-specific RH intersections, H, strict pairwise classes, LDF propagation, IRA modeled release, and ImCOF modeled release.

Version 1.0 provides the self-contained coverage-centered execution path:

- Murphy-Koop water/ice saturation ratio;
- subzero RH ice-saturation capping;
- lower-temperature weather-distribution summaries;
- immediate RH-ceiling and cold-boundary state counts;
- final Figure 2-7 numbering and source-table mapping;
- explicit distinction between source-data replots and final artwork;
- bundled canonical hourly temperature/RH and solar/wind forcing;
- portable, restartable PADAC city and all-city runners;
- exact-artwork hashes from the submitted files; all 14/14 main-text and Supporting Information PNG streams, including the Python-generated conceptual Figure 1, match the submitted DOCX media by SHA-256.

## Regeneration levels

- **Independent raw-input calculation:** coverage extensions, weather-state summaries, equilibrium H, IRA hourly LDF Y, ImCOF whole-range H, and fixed-80 degC ImCOF Y.
- **Validated intermediate regression:** pairwise H/Y classification from climate-level scores and some sensitivity summaries.
- **Completed publication-scale calculation:** the complete 10-year, 36-city PADAC thermal ODE panel reproduces 13 Y-only reversals among 435 eligible pairs and zero joint H/Y reversals; evidence is retained under `validation/padac_partial/`.
- **Frozen stochastic summaries:** selected bootstrap sensitivity repeats are retained as labeled intermediates.

Every public command writes new files under `results/`; canonical input files are never overwritten.

The archived v1.0.0 software release is identified by https://doi.org/10.5281/zenodo.24617626.
