from pathlib import Path
import shutil

from PIL import Image
import pytest

from photometaclean.core.batch import analyze_one
from photometaclean.metadata import analysis
from photometaclean.metadata.classification import interpret


def test_oversize_before_extraction(tmp_path, monkeypatch):
    path = tmp_path / "large.bin"
    path.write_bytes(b"1234")
    monkeypatch.setattr(analysis, "MAX_INPUT", 3)
    result = analyze_one(path)
    assert result["classification"] == interpret({})
    assert "regular file" in result["error"]


def test_extra_jpeg_pixel_budget(tmp_path, monkeypatch):
    path = tmp_path / "two.jpg"
    first = tmp_path / "first.jpg"
    Image.new("RGB", (4, 4)).save(first)
    path.write_bytes(first.read_bytes() * 2)
    monkeypatch.setattr(analysis, "MAX_STREAM_PIXELS", 20)
    monkeypatch.setattr(analysis, "exif_metadata", lambda p: ({}, ""))
    with pytest.raises(ValueError, match="codestream pixel"):
        analysis.analyze(path)


def test_analysis_classification(tmp_path, monkeypatch):
    path = tmp_path / "ordinary.png"
    im = Image.new("RGB", (17, 21), "green")
    im.save(path)
    tags = {"XMP-iptcExt:DigitalSourceType":
            "http://cv.iptc.org/newscodes/digitalsourcetype/digitalCapture"}
    monkeypatch.setattr(analysis, "exif_metadata", lambda p: (tags, ""))
    result = analysis.analyze(path)
    assert result["classification"] == interpret(tags)
    assert result["frames"][0]["pixels"] == analysis.digest(im.tobytes())


@pytest.mark.skipif(not shutil.which("exiftool"), reason="requires ExifTool")
def test_exiftool_unknown(tmp_path):
    path = tmp_path / "unknown.bin"
    path.write_bytes(bytes(range(128)))
    assert "error" in analyze_one(path)
