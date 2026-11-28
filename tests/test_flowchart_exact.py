from pathlib import Path
from tempfile import TemporaryDirectory

from scripts.reproduce_flowchart_exact import EXPECTED_SHA256, reproduce


def test_flowchart_reproduction_is_byte_and_pixel_identical() -> None:
    with TemporaryDirectory() as directory:
        output = Path(directory) / "flowchart.png"
        result = reproduce(
            Path(__file__).resolve().parents[1]
            / "assets"
            / "measurement_to_co2_release_flowchart.png",
            output,
        )
        assert result["sha256"] == EXPECTED_SHA256
        assert result["byte_identical"] is True
        assert result["pixel_identical"] is True
