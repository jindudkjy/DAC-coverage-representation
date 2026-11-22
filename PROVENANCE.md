# Code and data provenance

## Source assets

- Final closed manuscript and Supporting Information dated 2026-11-23.
- Google Drive analysis-code archive `02_analysis_code`.
- Google Drive reproduction-code and output archive `08_reproduction_code_and_outputs`.
- Frozen reproducibility package dated 2026-11-19.

## Maintained implementation

The importable code under `src/dac_equilibrium/` preserves the manuscript conventions for measured-domain coverage, interval-specific RH intersections, H, strict pairwise classes, LDF propagation, IRA modeled release, and ImCOF modeled release.

Version 0.2 adds the final manuscript's coverage-centered execution path:

- Murphy-Koop water/ice saturation ratio;
- subzero RH ice-saturation capping;
- lower-temperature weather-distribution summaries;
- immediate RH-ceiling and cold-boundary state counts;
- final Figure 2-7 numbering and source-table mapping;
- explicit distinction between source-data replots and final artwork.

## Regeneration levels

- **Independent raw-input calculation:** coverage extensions, weather-state summaries, equilibrium H, IRA hourly LDF Y, ImCOF whole-range H, and fixed-80 degC ImCOF Y.
- **Validated intermediate regression:** pairwise H/Y classification from climate-level scores and some sensitivity summaries.
- **Frozen-only or partially closed:** the complete 10-year PADAC thermal ODE panel and selected stochastic sensitivity repeats.

Every public command writes new files under `results/`; canonical input files are never overwritten.
