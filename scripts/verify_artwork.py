#!/usr/bin/env python
"""Require byte-identical and pixel-identical final manuscript artwork."""

from __future__ import annotations

import argparse
import hashlib
import sys
from pathlib import Path

import numpy as np
from PIL import Image


FILENAMES = [
    "Fig2_final.png",
    "Fig3_final.png",
    "Fig4_final.png",
    "Fig5_final.png",
    "Fig6_final.png",
    "Fig7_final.png",
    "FigS5_final.png",
    "FigS6_final.png",
    "FigS7_final.png",
]


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def compare(reference: Path, candidate: Path) -> dict[str, object]:
    with Image.open(reference) as ref_image, Image.open(candidate) as candidate_image:
        ref = np.asarray(ref_image.convert("RGBA"))
        got = np.asarray(candidate_image.convert("RGBA"))
    same_shape = ref.shape == got.shape
    pixel_identical = bool(same_shape and np.array_equal(ref, got))
    differing_pixels = int(np.any(ref != got, axis=2).sum()) if same_shape else None
    return {
        "same_dimensions": same_shape,
        "pixel_identical": pixel_identical,
        "differing_pixels": differing_pixels,
        "byte_identical": _sha256(reference) == _sha256(candidate),
    }


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--reference-dir", type=Path, default=Path("validation/reference_artwork"))
    parser.add_argument("--candidate-dir", type=Path, required=True)
    args = parser.parse_args()

    failed = False
    for filename in FILENAMES:
        reference = args.reference_dir / filename
        candidate = args.candidate_dir / filename
        if not reference.exists() or not candidate.exists():
            print(f"FAIL {filename}: missing reference or candidate")
            failed = True
            continue
        result = compare(reference, candidate)
        passed = result["byte_identical"] and result["pixel_identical"]
        print(
            f"{'PASS' if passed else 'FAIL'} {filename}: "
            f"bytes={result['byte_identical']} pixels={result['pixel_identical']} "
            f"different_pixels={result['differing_pixels']}"
        )
        failed = failed or not passed
    if failed:
        sys.exit(1)


if __name__ == "__main__":
    main()
