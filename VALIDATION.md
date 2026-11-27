# Numerical validation status

Validation date: 2026-11-28

Scope: numerical reproducibility of Jin-young Kang's manuscript and Supporting Information titled *Equilibrium Data Coverage and Representation in Weather-Resolved Direct Air Capture Analysis*. This validation does not establish new experimental validity for the physical models.

## Overall conclusion

The coverage-centered results and the principal equilibrium and modeled-release calculations reproduce within floating-point or stated numerical tolerance. No discrepancy that reverses a central manuscript conclusion was found.

The full publication-scale PADAC thermal integration is complete for all 36 cities. The independent rerun retains 30 evaluable climates and reproduces the manuscript result of 13 Y-only reversals among 435 eligible pairs, with zero joint H/Y reversals.

## Independent raw-input calculations

| Calculation | Scope | Maximum discrepancy | Status |
| --- | ---: | ---: | --- |
| Equilibrium H panel | 2,826 rows | 4.55e-13 for H; 1.46e-11 for H_RH | pass |
| H/N and partial-Kendall analysis | 108 material panels; 12 Table S6 medians | exact to displayed precision | pass |
| H/N random reassignment | 108 panels × 3,000 seeded reassignments | all SI Table S6 random-reassignment medians and counts reproduced | pass |
| Figure 3 panel summary | 12 rows | 3.44e-13 | pass |
| Native-hour boundary extension | 72 rows | 3.55e-15 percentage points | pass |
| IRA hourly LDF Y | 140 frozen-cohort rows | 2.27e-13 mmol g-1 | pass |
| IRA strict H/Y pair classes | 2,380 pairs | zero class mismatches | pass |
| ImCOF whole-range H | 72 rows | 1.14e-13 | pass |
| ImCOF fixed-80 degC Y | 72 rows | 2.22e-16 | pass |
| Temperature-correction pair flags | 39,151 pairs | zero reversal/margin mismatches | pass |
| PADAC solar regeneration | 36 cities; 30 evaluable climates; 435 pairs | 13 Y-only; 0 joint H/Y reversals | pass |
| SI Figure S6 source values | 3 rows | 1.78e-15 | pass |
| SI Figure S7 source values | 4 rows | exact | pass |

## Final coverage manuscript checks

- Hourly weather rows: 3,156,192 across 36 locations.
- Lower-temperature 5 degC-bin RH medians and ice-supersaturation fractions reproduce SI Table S13 after rounding.
- Immediate upper-RH-band state counts reproduce 7,918, 30,112 and 46,792.
- Immediate colder-band state counts reproduce 337, 337 and 1,092.
- Ice-capped relative coverage gains reproduce 36.34%, 30.04% and 33.72% for the three upper-RH extensions and 1.66%, 0.35% and 1.99% for the corresponding cold extensions.
- The core boundary-extension regression passed at absolute tolerance 1e-9; the observed maximum error was 3.55e-15.

### SI Table S6 (N-controlled ordering agreement)

`scripts/n_controlled_ordering.py` regenerates every cell of SI Table S6, the H/N values in Section 3.2, and the source data for Fig. 3b from `MAIN_climate_H_scores.csv`. Running it reproduces all 108 printed cells exactly, including the random-reassignment medians and the counts below the 2.5th percentile.

The random-reassignment test uses one generator, `numpy.random.default_rng(0)`, shared across comparison cases in a fixed order. The script docstring documents this order. An implementation that seeds each case separately or processes cases in a different order draws different reassignments. Such an implementation shifts the random-reassignment medians by up to about 0.2 percentage points, and the conclusions and classifications are unchanged.

## Code and figure execution

- Unit tests: 22 passed, including raw temporal alignment, seeded reassignment, H/N and partial-Kendall tests.
- Main numerical figure reconstructions: Figures 2-7 generated and visually inspected; Figure 3b is recomputed from the complete 2,826-row H/N panel.
- SI numerical figure reconstructions: current Figures S3 and S5-S7 generated from the retained sources.
- Figure 1 is conceptual artwork and is not treated as a computed output.
- Latest submission artwork audit: Figures 1-7 and SI Figures S1-S7 were extracted from the embedded DOCX media streams.
- The high-resolution source streams for Figures 3-5 and SI Figure S2 were restored without changing their displayed size; automatic Word image compression is disabled in both submission documents.
- Exact artwork regression: 14/14 latest-submission PNG streams match the canonical references by SHA-256. Byte identity implies zero differing decoded pixels.
- Numerical replots remain separate from the exact-artwork regression because extraction verifies submission fidelity while recalculation verifies scientific values.

## PADAC publication-scale rerun

The restartable 10-year, 36-city, `nz=20` PADAC integration completed with no failed city jobs:

- all 36 city result files completed or were recovered from the validated cache;
- supported-cycle counts match the frozen reference in 36/36 cities;
- the maximum finite absolute city-level Y discrepancy is 6.30e-5 mmol g-1;
- 30 climates are evaluable in both representations, producing 435 strict location pairs;
- the recomputed classification is 397 neither, 25 H-only, 13 Y-only and 0 joint H/Y reversals;
- `scripts/verify_padac_solar.py` returns `claim_13_of_435_reproduced: true`.

See `validation/padac_partial/PADAC_STATUS.md`, `batch_status_nz20.csv` and `solar_pair_verification.json`. The historical directory name `padac_partial` is retained to avoid breaking published paths; its contents now record the completed rerun.

## Evidence files

- `validation/evidence/`: machine-readable core calculation status.
- `validation/tables/`: newly regenerated coverage, H/N Table S6 summary, and pairwise outputs.
- `validation/figures/` and `validation/si_figures/`: executable numerical verification plots.
- `validation/reference_artwork/`: canonical final PNG artwork, dimensions, source-media mapping, and SHA-256 hashes.
- `validation/input_sha256.csv`: hashes for the final manuscript, SI, raw inputs, and frozen source tables used in this run.
