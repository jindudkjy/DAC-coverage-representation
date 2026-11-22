# PADAC publication-scale rerun status

Snapshot date: 2026-11-23

The restartable 2015-2024, 36-city, `nz=20` PADAC thermal integration has
`14` completed or recovered city result files. Supported-cycle counts match
the frozen reference in `14/14` completed cities. The maximum finite absolute
city-level Y discrepancy is `0.00006294726158539987` mmol g-1.

The final solar-regeneration claim (13 Y-only reversals among 435 eligible location
pairs) is not marked independently reproduced until all 36 city jobs finish and
`scripts/verify_padac_solar.py` passes. The run is restartable and skips every existing
city JSON.
