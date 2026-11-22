# PADAC publication-scale rerun checkpoint

Checkpoint date: 2026-11-23

The full 10-year, 36-city, `nz=20` thermal integration is computationally expensive and is executed as restartable city jobs.

At this checkpoint, Adelaide, Amsterdam, Athens, Auckland, Beijing, Belem, Dalian and Helsinki have result JSON files. Their supported-cycle counts match the frozen reference exactly. The largest finite Y discrepancy among these cities is 2.57e-5 mmol g-1.

The original six-worker batch recorded a failed Dubai subprocess and stopped before closing the full panel. A two-worker resume was started to reduce memory pressure. Completed JSON files are detected and skipped automatically.

The frozen PADAC location-pair table can reproduce the manuscript's pair-classification summary, but it is not a substitute for completing every city-level thermal integration. This directory is therefore labeled `padac_partial`.
