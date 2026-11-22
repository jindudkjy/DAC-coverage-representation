# DAC manuscript and SI: reconstruction package (2026-11-19)

## Source-derived scope and non-claims

This is newly authored reconstruction code, **not** recovered original execution code. It never overwrites canonical inputs. Frozen/source output comparisons are kept separate from independently regenerated calculations.

1. **measurement_domain_extension_reproduction.py**: independent native-hour calculation from `MAIN_climate_hourly_2015_2024.csv`, `MAIN_material_support_bounds.csv`, and the per-isotherm RH limits of `MAIN_equilibrium_dataset_master.xlsx`, `06_RAW_QRHT`. Checks the 72 material x branch x boundary-extension entries and five reported numeric quantities against `immediate_boundary_extension_coverage_native1h.csv`. Independent calculation **PASS**. 3,156,192 weather rows / 36 locations / 3,156,156 valid transitions. Largest absolute discrepancy among gain percentage-point columns 3.553e-15, including max-location gain. Important: simple `MAIN_material_support_bounds.csv` has a material-wide IRA RH lower bound of 19.8%; the upper 25-35 C branch has an *intersection* lower bound of 21.8% (35 C minimum). Using 19.8 for the upper branch fails regression. The script derives the 21.8 from the raw master, not from the expected output.

2. **IRA_shared_support_score_regression.py**: independently reconstructs H-only, Y-only, both, and neither pair classifications and Kendall/Spearman correlations from **frozen climate-level** `IRA_environmental_common_support_climate_scores.csv`. Four comparisons x 595 pairs = 2,380 pair records, all 4 summary rows and 10 checked quantities matched at <1e-9. Y-only H-safe pairs: original lower/upper 186/146 and common-hour lower/upper 17/9. This **does not regenerate the hourly kinetic Y trajectories or independently verify their physical model**. That deeper reproducibility gap remains open.

3. **manuscript_figures_reproduction.py**: produces six *source-data re-plots* corresponding to the analytical topics in Fig. 2-7. Current figure labels and underlying CSV are documented in `figure_reconstruction_manifest.csv`. These PNGs are **not** final submission artwork, have not passed a pixel-matching regression, and intentionally do not claim original manuscript panel or statistical equivalence. Figure 3 is the reported class-C subset, Figure 5 uses the family summary only, and Figure 6 uses an aggregated kinetic sensitivity (not all original continuous-memory panels). Figure 7 is based on saved classification counts, not on new process simulations. Fig. 1 is excluded as requested.

## Files and paths

The notebook wrappers are located in this same folder and call `run_package.py`. `run_package.py` stages symlinks to files in the parent package's `01_canonical_inputs`, `03_equilibrium_H_results`, `04_process_HY_results`, and `05_SI_figures_and_data` without copying the weather database into memory twice.

Run in Colab after mounting Google Drive:

```
python /content/drive/MyDrive/REPOSITORY/DAC_manuscript_SI_complete_reproducibility_package_20261119/08_reproduction_code_and_outputs/run_package.py --root /content/drive/MyDrive/REPOSITORY/DAC_manuscript_SI_complete_reproducibility_package_20261119 --target all
```

Output goes to `08_reproduction_code_and_outputs/reproduced_outputs/` and is *not* substituted into the original manuscript/SI. For local execution the same script accepts any local root with this folder structure.

Packages: Python 3.11+, NumPy, pandas, scipy, openpyxl, matplotlib; Google Colab optional. No internet/API call within the numerical analysis.

## Data provenance and cautions

The project uses literature-reported/digitized q(RH,T), documented hourly weather and model-derived Y. The IRA climate-pair regression conditions on saved H and Y from the frozen process run. This is not an independent process validation and does not isolate coverage from kinetic-history changes.

Sources: original and copied files in Google Drive REPOSITORY/DAC_manuscript_SI_complete_reproducibility_package_20261119/; original common-hour output folder `process_fidelity_runs/20261115_192400_v1.6.5-climate-cache-key-fix/HY_process_common_hour_and_kinetic_audit_v2`.

## Remaining gaps

- IRA **hourly** `Y` generation using frozen process equations and shared support remains unexecuted in this newly written package. Pairwise regression is already passing but is conditional on frozen `Y` values.
- Plot style/layout and figure contents are not identical to manuscript figures. Final acceptance needs explicit per-panel and image comparisons, including full Fig. 3, 5, and 6 analyses.
- No new independent experimental validation, error-model calibration or broader generalization is claimed.
