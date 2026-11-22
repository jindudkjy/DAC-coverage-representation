#!/usr/bin/env python
"""Restartable two-worker PADAC reproduction for all 36 cities."""

from __future__ import annotations

import argparse
import json
import os
import subprocess
import sys
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path

import pandas as pd


ROOT = Path(__file__).resolve().parents[1]


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--workers", type=int, default=2)
    parser.add_argument("--nz", type=int, default=20)
    parser.add_argument("--output-dir", type=Path, default=ROOT / "results/padac")
    args = parser.parse_args()
    args.output_dir.mkdir(parents=True, exist_ok=True)
    logs = args.output_dir / "logs"
    logs.mkdir(exist_ok=True)
    reference = pd.read_csv(ROOT / "data/frozen/ImCOF_wholeH_wholeY_aligned_climate_scores.csv")
    cities = sorted(reference.query("operating_mode == 'environmental_PADAC13X'").climate.unique())

    def run(city: str) -> dict:
        result = args.output_dir / f"{city}_primary_nz{args.nz}.json"
        if result.exists():
            return {"status": "cached", **json.loads(result.read_text(encoding="utf-8"))}
        environment = os.environ.copy()
        environment["OPENBLAS_NUM_THREADS"] = "1"
        command = [sys.executable, str(ROOT / "scripts/reproduce_padac_city.py"), city, "--nz", str(args.nz), "--output-dir", str(args.output_dir)]
        started = time.monotonic()
        completed = subprocess.run(command, cwd=ROOT, env=environment, capture_output=True, text=True)
        (logs / f"{city}.stdout.txt").write_text(completed.stdout, encoding="utf-8")
        (logs / f"{city}.stderr.txt").write_text(completed.stderr, encoding="utf-8")
        if completed.returncode:
            return {"city": city, "status": "failed", "returncode": completed.returncode, "elapsed_seconds": time.monotonic() - started}
        return {"status": "completed", "elapsed_seconds": time.monotonic() - started, **json.loads(result.read_text(encoding="utf-8"))}

    records = []
    with ThreadPoolExecutor(max_workers=args.workers) as pool:
        futures = {pool.submit(run, city): city for city in cities}
        for future in as_completed(futures):
            record = future.result()
            records.append(record)
            pd.DataFrame(records).to_csv(args.output_dir / "batch_status.csv", index=False)
            print(json.dumps({key: record.get(key) for key in ["city", "status", "Y_single_error", "Y_tensor_error"]}), flush=True)
    failed = [record for record in records if record["status"] == "failed"]
    summary = {"expected_cities": len(cities), "finished_records": len(records), "failed": len(failed), "nz": args.nz, "workers": args.workers}
    (args.output_dir / "batch_summary.json").write_text(json.dumps(summary, indent=2), encoding="utf-8")
    print(json.dumps(summary))


if __name__ == "__main__":
    main()
