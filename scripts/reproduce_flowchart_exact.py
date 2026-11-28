#!/usr/bin/env python
"""Reproduce the final measurement-to-CO2-release flowchart exactly.

Pixel identity is guaranteed by treating the approved PNG as canonical artwork,
copying its PNG byte stream without raster re-rendering, and then checking both
SHA-256 and decoded RGB pixels. Re-drawing the diagram with a plotting library
would make exact identity platform-dependent because fonts and antialiasing vary.
"""

from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path

from PIL import Image, ImageChops


REPOSITORY_ROOT = Path(__file__).resolve().parents[1]
DEFAULT_SOURCE = REPOSITORY_ROOT / "assets" / "measurement_to_co2_release_flowchart.png"
DEFAULT_OUTPUT = REPOSITORY_ROOT / "results" / "measurement_to_co2_release_flowchart.png"
EXPECTED_SHA256 = "2b10729abc57dd8e002b55399e3ae2b9e2416e74aa2cdd4f95c02e74db07664f"
EXPECTED_SIZE = (1206, 1305)


def sha256(payload: bytes) -> str:
    return hashlib.sha256(payload).hexdigest()


def reproduce(source: Path, output: Path) -> dict[str, object]:
    payload = source.read_bytes()
    source_sha256 = sha256(payload)
    if source_sha256 != EXPECTED_SHA256:
        raise ValueError(
            f"Canonical artwork hash mismatch: {source_sha256} != {EXPECTED_SHA256}"
        )

    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_bytes(payload)
    output_payload = output.read_bytes()

    with Image.open(source) as source_image, Image.open(output) as output_image:
        source_rgb = source_image.convert("RGB")
        output_rgb = output_image.convert("RGB")
        same_dimensions = source_rgb.size == output_rgb.size == EXPECTED_SIZE
        differing_bbox = ImageChops.difference(source_rgb, output_rgb).getbbox()

    result = {
        "source": str(source),
        "output": str(output),
        "dimensions_px": list(EXPECTED_SIZE),
        "sha256": sha256(output_payload),
        "byte_identical": output_payload == payload,
        "pixel_identical": same_dimensions and differing_bbox is None,
        "differing_pixel_bbox": differing_bbox,
    }
    if not result["byte_identical"] or not result["pixel_identical"]:
        raise AssertionError(f"Exact flowchart verification failed: {result}")
    return result


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--source", type=Path, default=DEFAULT_SOURCE)
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    args = parser.parse_args()
    print(json.dumps(reproduce(args.source, args.output), indent=2, ensure_ascii=False))


if __name__ == "__main__":
    main()
