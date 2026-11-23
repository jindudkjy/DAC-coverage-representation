# Numerical validation status

Validation date: 2026-11-23

Scope: numerical reproducibility of the latest submission manuscript `20261123j` and Supporting Information `20261123g`. This validation does not establish new experimental validity for the physical models.

## Overall conclusion

The coverage-centered results and the principal equilibrium and modeled-release calculations reproduce within floating-point or stated numerical tolerance. No discrepancy that reverses a central manuscript conclusion was found.

The full publication-scale PADAC thermal integration remains a separately tracked computational closure item. Fourteen cities have completed or been recovered from cache; the remaining cities require completion in the restartable two-worker batch. Frozen PADAC climate scores are used only where explicitly labeled.

## Independent raw-input calculations

| Calculation | Scope | Maximum discrepancy | Status |
| --- | ---: | ---: | --- |
| Equilibrium H panel | 2,826 rows | 4.55e-13 for H; 1.46e-11 for H_RH | pass |
| H/N and partial-Kendall analysis | 108 material panels; 12 Table S6 medians | exact to displayed precision | pass |
| H/N random reassignment | 108 panels x 3,000 seeded reassignments | main-text 10.14%, 12.91%, 8 and 10 reproduced | pass |
| Figure 3 panel summary | 12 rows | 3.44e-13 | pass |
| Native-hour boundary extension | 72 rows | 3.55e-15 percentage points | pass |
| IRA hourly LDF Y | 140 frozen-cohort rows | 2.27e-13 mmol g-1 | pass |
| IRA strict H/Y pair classes | 2,380 pairs | zero class mismatches | pass |
| ImCOF whole-range H | 72 rows | 1.14e-13 | pass |
| ImCOF fixed-80 degC Y | 72 rows | 2.22e-16 | pass |
| Temperature-correction pair flags | 39,151 pairs | zero reversal/margin mismatches | pass |
| SI Figure S6 source values | 3 rows | 1.78e-15 | pass |
| SI Figure S7 source values | 4 rows | exact | pass |

## Final coverage manuscript checks

- Hourly weather rows: 3,156,192 across 36 locations.
- Lower-temperature 5 degC-bin RH medians and ice-supersaturation fractions reproduce SI Table S13 after rounding.
- Immediate upper-RH-band state counts reproduce 7,918, 30,112 and 46,792.
- Immediate colder-band state counts reproduce 337, 337 and 1,092.
- Ice-capped relative coverage gains reproduce 36.34%, 30.04% and 33.72% for the three upper-RH extensions and 1.66%, 0.35% and 1.99% for the corresponding cold extensions.
- The core boundary-extension regression passed at absolute tolerance 1e-9; the observed maximum error was 3.55e-15.

## H to H/N end-to-end path

- `scripts/reproduce_tables.py --target h-panel` reconstructs all 2,826 location rows directly from the hourly weather, equilibrium workbook and material-domain bounds; it does not read the retained H panel as calculation input. The `h-to-hn` target continues through the H/N and permutation analysis in the same run.
- The reconstructed `H_single` and `H_tensor` agree with the retained reference within 4.55e-13, `H_RH` within 1.46e-11, and `N` exactly.
- The `hn` target then consumes that reconstructed panel and performs 3,000 seeded relative-change reassignments per material, branch and temporal case.
- The main-text permutation aggregates reproduce 10.14% and 12.91%; 8 and 10 material cases fall below their corresponding 2.5th percentiles.
- Ten of the 12 per-mode random medians reproduce the displayed SI Table S6 values. The seeded rerun differs by 0.16 and 0.21 percentage points in lower-branch 6 h and 24 h subsampling, respectively; all 12 below-percentile counts reproduce. These small differences are Monte Carlo sampling variation and do not alter any reported classification or conclusion.

## Code and figure execution

- Unit tests: 22 passed, including raw temporal alignment, seeded reassignment, H/N and partial-Kendall tests.
- Main numerical figure reconstructions: Figures 2-7 generated and visually inspected; Figure 3b is recomputed from the complete 2,826-row H/N panel.
- SI numerical figure reconstructions: current Figures S3 and S5-S7 generated from the retained sources.
- Figure 1 is conceptual artwork and is not treated as a computed output.
- Latest submission artwork audit: Figures 2-7 and SI Figures S5-S7 were extracted from the embedded DOCX media streams.
- Figure 3 was refreshed from manuscript `20261123j`; the other eight tracked PNG streams were unchanged.
- Exact artwork regression: 9/9 latest-submission PNG streams match the canonical references by SHA-256. Byte identity implies zero differing decoded pixels.
- Numerical replots remain separate from the exact-artwork regression because extraction verifies submission fidelity while recalculation verifies scientific values.

## PADAC split-run status

The 10-year, 36-city, `nz=20` PADAC integration is restartable by city. At the packaged checkpoint:

- 14 cities completed or recovered from cache;
- supported-cycle counts matched the frozen reference for every completed city;
- maximum absolute Y discrepancy among finite completed-city comparisons was 6.30e-5 mmol g-1;
- all retained completed-city supported-cycle counts match the frozen reference;
- the lower-memory two-worker runner is restartable and skips all completed city JSON files.

See `validation/padac_partial/PADAC_STATUS.md` and `batch_status_nz20.csv`. Until all 36 city jobs close, this portion must be described as partial rather than fully independently regenerated.

## Evidence files

- `validation/evidence/`: machine-readable core calculation status.
- `validation/tables/`: newly regenerated coverage, H/N Table S6 summary, and pairwise outputs.
- `validation/figures/` and `validation/si_figures/`: executable numerical verification plots.
- `validation/reference_artwork/`: canonical final PNG artwork, dimensions, source-media mapping, and SHA-256 hashes.
- `validation/input_sha256.csv`: hashes for the final manuscript, SI, raw inputs, and frozen source tables used in this run.
