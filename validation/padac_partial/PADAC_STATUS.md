# PADAC publication-scale rerun status

Snapshot date: 2026-11-25

The restartable 2015-2024, 36-city, `nz=20` PADAC thermal integration completed
all `36` city result files with zero failed jobs. Supported-cycle counts match
the frozen reference in `36/36` cities. The maximum finite absolute city-level
Y discrepancy is `0.00006294726158539987` mmol g-1.

`scripts/verify_padac_solar.py` retained `30` evaluable climates and reconstructed
all `435` strict location pairs: `397` neither, `25` H-only, `13` Y-only and `0`
joint H/Y reversals. The manuscript claim of 13 Y-only reversals among 435 eligible
pairs is independently reproduced. The run remains restartable and skips every
existing city JSON.
