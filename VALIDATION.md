# Numerical validation status

Validation date: 2026-11-23

Scope: numerical reproducibility of the final closed manuscript and Supporting Information. This validation does not establish new experimental validity for the physical models.

## Overall conclusion

The coverage-centered results and the principal equilibrium and modeled-release calculations reproduce within floating-point or stated numerical tolerance. No discrepancy that reverses a central manuscript conclusion was found.

The full publication-scale PADAC thermal integration remains a separately tracked computational closure item. Eight cities have completed or been recovered from cache; the remaining cities are running in a restartable two-worker batch. Frozen PADAC climate scores are used only where explicitly labeled.

## Independent raw-input calculations

| Calculation | Scope | Maximum discrepancy | Status |
| --- | ---: | ---: | --- |
| Equilibrium H panel | 2,826 rows | 4.55e-13 for H; 1.46e-11 for H_RH | pass |
| Figure 3 panel summary | 12 rows | 3.44e-13 | pass |
| Native-hour boundary extension | 72 rows | 3.55e-15 percentage points | pass |
| IRA hourly LDF Y | 140 frozen-cohort rows | 2.27e-13 mmol g-1 | pass |
| IRA strict H/Y pair classes | 2,380 pairs | zero class mismatches | pass |
| ImCOF whole-range H | 72 rows | 1.14e-13 | pass |
| ImCOF fixed-80 degC Y | 72 rows | 2.22e-16 | pass |
| Temperature-correction pair flags | 39,151 pairs | zero reversal/margin mismatches | pass |
| SI Figure S5 source values | 3 rows | 1.78e-15 | pass |
| SI Figure S6 source values | 4 rows | exact | pass |

## Final coverage manuscript checks

- Hourly weather rows: 3,156,192 across 36 locations.
- Lower-temperature 5 degC-bin RH medians and ice-supersaturation fractions reproduce SI Table S16 after rounding.
- Immediate upper-RH-band state counts reproduce 7,918, 30,112 and 46,792.
- Immediate colder-band state counts reproduce 337, 337 and 1,092.
- Ice-capped relative coverage gains reproduce 36.34%, 30.04% and 33.72% for the three upper-RH extensions and 1.66%, 0.35% and 1.99% for the corresponding cold extensions.
- The core boundary-extension regression passed at absolute tolerance 1e-9; the observed maximum error was 3.55e-15.

## Code and figure execution

- Unit tests: 15 passed.
- Main numerical figure reconstructions: Figures 2-7 generated and visually inspected.
- SI numerical figure reconstructions: Figures S5-S7 generated and visually inspected.
- Figure 1 is conceptual artwork and is not treated as a computed output.
- Generated plots validate source values and trends; they are not pixel-identical journal-artwork regressions.

## PADAC split-run status

The 10-year, 36-city, `nz=20` PADAC integration is restartable by city. At the packaged checkpoint:

- 8 cities completed or recovered from cache;
- supported-cycle counts matched the frozen reference for every completed city;
- maximum absolute Y discrepancy among finite completed-city comparisons was 2.57e-5 mmol g-1;
- one Dubai process exited before writing a result during the original six-worker run;
- a lower-memory two-worker resume was started and skips all completed city JSON files.

See `validation/padac_partial/PADAC_STATUS.md` and `batch_status_nz20.csv`. Until all 36 city jobs close, this portion must be described as partial rather than fully independently regenerated.

## Evidence files

- `validation/evidence/`: machine-readable core calculation status.
- `validation/tables/`: newly regenerated coverage and pairwise outputs.
- `validation/figures/` and `validation/si_figures/`: executable numerical verification plots.
- `validation/input_sha256.csv`: hashes for the final manuscript, SI, raw inputs, and frozen source tables used in this run.
