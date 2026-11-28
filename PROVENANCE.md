# Code and data provenance

## Source assets

- Final submission manuscript `Manuscript_20261128_revised_v6.docx`, Supporting Information `Supporting_Information_20261128_revised_v3.docx`, cover letter `Cover_Letter_Coverage_Representation_DAC_submission_20261123l.docx`, and highlights `Highlights_Coverage_Representation_DAC_submission_20261123d.docx`.
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
- exact-artwork hashes from the latest submission files; conceptual Figure 1 is excluded, and all 13/13 tracked PNG streams match the latest DOCX media by SHA-256.

## Regeneration levels

- **Independent raw-input calculation:** coverage extensions, weather-state summaries, equilibrium H, IRA hourly LDF Y, ImCOF whole-range H, and fixed-80 degC ImCOF Y.
- **Validated intermediate regression:** pairwise H/Y classification from climate-level scores and some sensitivity summaries.
- **Publication-scale calculation in progress:** the complete 10-year PADAC thermal ODE panel is restartable by city; the exact packaged checkpoint and limitations are reported in `validation/padac_partial/PADAC_STATUS.md`.
- **Frozen stochastic summaries:** selected bootstrap sensitivity repeats are retained as labeled intermediates.

Every public command writes new files under `results/`; canonical input files are never overwritten.
