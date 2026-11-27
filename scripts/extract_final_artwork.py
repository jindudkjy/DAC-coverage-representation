#!/usr/bin/env python
"""Extract final manuscript artwork from the submitted DOCX files.

This script preserves the exact PNG byte streams embedded in the closed
manuscript and Supporting Information. It does not recalculate scientific
results; the numerical calculation path remains in reproduce_figures.py and
reproduce_si_figures.py.
"""

from __future__ import annotations

import argparse
import hashlib
import re
import zipfile
from pathlib import Path
from xml.etree import ElementTree as ET


WORD_NS = "http://schemas.openxmlformats.org/wordprocessingml/2006/main"
DRAWING_NS = "http://schemas.openxmlformats.org/drawingml/2006/main"
REL_NS = "http://schemas.openxmlformats.org/officeDocument/2006/relationships"
PACKAGE_REL_NS = "http://schemas.openxmlformats.org/package/2006/relationships"
FIGURE_RE = re.compile(r"^Fig(?:ure)?\.?\s*(S?\d+)\b", re.IGNORECASE)


def _paragraph_text(paragraph: ET.Element) -> str:
    return "".join(node.text or "" for node in paragraph.iter(f"{{{WORD_NS}}}t")).strip()


def _relationship_targets(archive: zipfile.ZipFile) -> dict[str, str]:
    root = ET.fromstring(archive.read("word/_rels/document.xml.rels"))
    return {
        relationship.attrib["Id"]: relationship.attrib["Target"].replace("\\", "/")
        for relationship in root.findall(f"{{{PACKAGE_REL_NS}}}Relationship")
    }


def extract_figures(docx: Path, wanted: set[str]) -> dict[str, tuple[bytes, str]]:
    """Return requested figure labels mapped to embedded bytes and media path."""

    found: dict[str, tuple[bytes, str]] = {}
    with zipfile.ZipFile(docx) as archive:
        relationships = _relationship_targets(archive)
        document = ET.fromstring(archive.read("word/document.xml"))
        pending_targets: list[str] = []

        for paragraph in document.iter(f"{{{WORD_NS}}}p"):
            embeds = [
                node.attrib.get(f"{{{REL_NS}}}embed")
                for node in paragraph.iter(f"{{{DRAWING_NS}}}blip")
            ]
            embeds = [embed for embed in embeds if embed]
            if embeds:
                pending_targets = [relationships[embed] for embed in embeds]

            match = FIGURE_RE.match(_paragraph_text(paragraph))
            if not match or not pending_targets:
                continue
            label = match.group(1).upper()
            if label not in wanted:
                pending_targets = []
                continue
            if len(pending_targets) != 1:
                raise RuntimeError(f"Expected one image before Fig. {label}; found {pending_targets}")
            target = pending_targets[0]
            member = f"word/{target.lstrip('/')}"
            found[label] = (archive.read(member), target)
            pending_targets = []

    missing = wanted.difference(found)
    if missing:
        raise RuntimeError(f"Figures not found in {docx}: {sorted(missing)}")
    return found


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--manuscript", type=Path, required=True)
    parser.add_argument("--supporting-information", type=Path, required=True)
    parser.add_argument("--output-dir", type=Path, default=Path("results/final_artwork"))
    args = parser.parse_args()

    requested_main = {str(number) for number in range(1, 8)}
    requested_si = {f"S{number}" for number in range(1, 8)}
    figures = extract_figures(args.manuscript, requested_main)
    figures.update(extract_figures(args.supporting_information, requested_si))

    args.output_dir.mkdir(parents=True, exist_ok=True)
    rows = ["figure,output,source_document,source_media,bytes,sha256"]
    labels = [str(number) for number in range(1, 8)]
    labels.extend(f"S{number}" for number in range(1, 8))
    for label in labels:
        payload, media_path = figures[label]
        output = args.output_dir / f"Fig{label}_final.png"
        output.write_bytes(payload)
        source = args.manuscript if not label.startswith("S") else args.supporting_information
        rows.append(
            f"Fig{label},{output.name},{source.name},{media_path},{len(payload)},"
            f"{hashlib.sha256(payload).hexdigest()}"
        )
    (args.output_dir / "final_artwork_manifest.csv").write_text("\n".join(rows) + "\n", encoding="utf-8")
    print(f"Extracted {len(figures)} final artwork files to {args.output_dir}")


if __name__ == "__main__":
    main()
