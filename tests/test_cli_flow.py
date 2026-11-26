import json
from pathlib import Path

from PIL import Image
from photometaclean.cli.app import main


def test_cli_batch_integrity(tmp_path):
    source = tmp_path / "in"
    source.mkdir()
    picture = source / "foto ä 東京 🌙.jpg"
    Image.new("RGB", (24, 16), "teal").save(picture, comment=b"test")
    original = picture.read_bytes()
    output = source / "nested output"
    report = tmp_path / "audit.jsonl"
    args = ["edit", str(source), "--changes", '{"JPEG:Comment":null}']
    assert main(args + ["--report", str(tmp_path / "preview.jsonl")]) == 0
    assert not output.exists()
    assert main(args + ["--output", str(output), "--apply", "--report", str(report)]) == 0
    assert picture.read_bytes() == original
    audit = [json.loads(s) for s in report.read_text(encoding="utf8").splitlines()]
    assert audit[-1]["result"]["audit"]["integrity_after"] == audit[-1]["result"]["audit"]["integrity_before"]
    check = audit[-1]["result"]["postcheck"]
    assert check["state"] == "clear", check["issue"]
    assert (output / picture.name).exists()
    assert not (output / output.name).exists()
    from pathlib import Path
    journal = Path(audit[-1]["result"]["journal"])
    assert journal.is_file() and not journal.is_relative_to(output)
    assert list(output.rglob("*.jsonl")) == []
    assert [json.loads(s)["state"] for s in journal.read_text(encoding="utf8").splitlines()] == ["approved", "verified"]


def test_changed_source_rejected(tmp_path):
    from photometaclean.core.review import apply_reviewed, review
    import pytest
    picture = tmp_path / "a.jpg"
    Image.new("RGB", (16, 16)).save(picture, comment=b"first")
    approved = review(picture, {"JPEG:Comment": None})
    Image.new("RGB", (16, 16)).save(picture, comment=b"other")
    with pytest.raises(ValueError):
        apply_reviewed(approved, tmp_path / "out.jpg")
    assert not (tmp_path / "out.jpg").exists()
