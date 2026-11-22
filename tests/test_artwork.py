import importlib.util
from pathlib import Path
from tempfile import TemporaryDirectory

from PIL import Image

SCRIPT = Path(__file__).resolve().parents[1] / "scripts" / "verify_artwork.py"
SPEC = importlib.util.spec_from_file_location("verify_artwork", SCRIPT)
assert SPEC is not None and SPEC.loader is not None
VERIFY_ARTWORK = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(VERIFY_ARTWORK)
compare = VERIFY_ARTWORK.compare


def test_artwork_compare_accepts_exact_copy() -> None:
    with TemporaryDirectory() as directory:
        tmp_path = Path(directory)
        reference = tmp_path / "reference.png"
        candidate = tmp_path / "candidate.png"
        Image.new("RGBA", (4, 3), (10, 20, 30, 255)).save(reference)
        candidate.write_bytes(reference.read_bytes())

        result = compare(reference, candidate)

        assert result["byte_identical"] is True
        assert result["pixel_identical"] is True
        assert result["differing_pixels"] == 0


def test_artwork_compare_rejects_changed_pixel() -> None:
    with TemporaryDirectory() as directory:
        tmp_path = Path(directory)
        reference = tmp_path / "reference.png"
        candidate = tmp_path / "candidate.png"
        Image.new("RGBA", (4, 3), (10, 20, 30, 255)).save(reference)
        changed = Image.new("RGBA", (4, 3), (10, 20, 30, 255))
        changed.putpixel((2, 1), (11, 20, 30, 255))
        changed.save(candidate)

        result = compare(reference, candidate)

        assert result["byte_identical"] is False
        assert result["pixel_identical"] is False
        assert result["differing_pixels"] == 1
