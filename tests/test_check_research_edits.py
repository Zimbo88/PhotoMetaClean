"""Public synthetic fixtures for the local-only acceptance harness."""
import io
import json
from pathlib import Path
import shutil
import sys

from PIL import Image
import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))
import check_research_edits as check


def jpeg(path, with_field=True):
    data = io.BytesIO()
    Image.new("RGB", (13, 7), "blue").save(data, "JPEG")
    packet = (b"http://ns.adobe.com/xap/1.0/\0"
              b'<r:RDF xmlns:r="http://www.w3.org/1999/02/22-rdf-syntax-ns#">'
              b'<r:Description xmlns:a="http://ns.adobe.com/exif/1.0/aux/" '
              + (b'a:SerialNumber' + b'="synthetic"' if with_field else b'') +
              b'/></r:RDF>')
    segment = b"\xff\xe1" + (2 + len(packet)).to_bytes(2, "big") + packet
    path.write_bytes(data.getvalue()[:2] + segment + data.getvalue()[2:])
    return path


@pytest.fixture
def layout(tmp_path):
    for folder in check.FOLDERS:
        (tmp_path / folder).mkdir()
    run_dir = tmp_path / "research/private/run"
    run_dir.mkdir(parents=True)
    return tmp_path / check.FOLDERS[0], run_dir


needs_tool = pytest.mark.skipif(not shutil.which("exiftool"), reason="requires ExifTool")


@needs_tool
def test_temporary_copies_and_sidecar_refusal(layout):
    original, run_dir = layout
    src = jpeg(original / "example.jpg")
    protected = jpeg(original / "signed.jpg", False)
    protected.with_suffix(".C2PA").write_bytes(b"synthetic sidecar")
    jpeg(original / "untouched.jpg", False)
    counts = check.run(original.parent, run_dir, 2)
    assert counts == dict(files=4, failed=0, verified=1, verified_auxiliary=0,
                          no_eligible_field=1, originals_intact=4,
                          analysis_only_format=1, provenance_refused=1)
    report, = run_dir.iterdir()
    rows = [json.loads(line) for line in report.read_text().splitlines()]
    verified, = (r for r in rows if r.get("status") == "verified")
    assert verified["field"] == "XMP-aux:SerialNumber"
    assert verified["original_before"] == check.sha(src) != verified["output_sha256"]


@needs_tool
def test_wrong_refusal_fails_for_both_operations(layout, monkeypatch):
    original, run_dir = layout
    path = jpeg(original / "synthetic.jpg", False)
    path.with_suffix(".c2pa").touch()
    called = []
    def wrong(*args):
        called.append(args[0])
        raise ValueError("field missing")
    monkeypatch.setattr(check, "plan", wrong)
    monkeypatch.setattr(check, "apply", wrong)
    row = check.examine(path, run_dir, check.sha(path))
    assert row["status"] == "failed"
    assert len(called) == 2 and all(p != path for p in called)
    assert not list(run_dir.iterdir())


@needs_tool
def test_protected_bytes_and_audit_extent(layout):
    original, run_dir = layout
    path = jpeg(original / "check.jpg")
    before = check.analyze(path)
    field = check.TARGETS[0]
    dest = run_dir / "out.jpg"
    audit = check.apply(path, dest, {field: None})
    change, = audit["changes"]
    data = dest.read_bytes()
    dest.write_bytes(data[:-1] + b"x")
    with pytest.raises(ValueError, match="Protected bytes"):
        check.verify_bytes(path, dest, before, change, field)
    dest.write_bytes(data)
    with pytest.raises(ValueError, match="exactly"):
        check.verify_bytes(path, dest, before, dict(change, length=change["length"] + 1), field)


def test_secondary_pixels_compared_independently(monkeypatch, tmp_path):
    original = jpeg(tmp_path / "a.jpg")
    dest = tmp_path / "b.jpg"
    field = check.TARGETS[0]
    audit = check.apply(original, dest, {field: None})
    start = audit["changes"][0]["offset"]
    before = dict(sha256=check.sha(original), frames=[{"pixels": "primary"}],
                  blocks=[dict(kind="APP1 XMP", frame=1, offset=0, size=original.stat().st_size)],
                  codestreams=[{"pixels": "primary"}, {"pixels": "aux1"}])
    after = dict(before, sha256=check.sha(dest), codestreams=[{"pixels":"primary"}, {"pixels":"aux2"}])
    monkeypatch.setattr(check, "analyze", lambda p: after)
    assert 0 < start < original.stat().st_size
    with pytest.raises(ValueError, match="codestreams"):
        check.verify_copy(original, dest, before, audit, audit,
                          dict(original_before=before["sha256"], field=field))


def test_other_metadata_is_protected():
    target = "XMP-aux:Main:Copy1:SerialNumber"
    retained = "ExifIFD:Main:SerialNumber"
    before = {target: "one", retained: "two"}
    with pytest.raises(ValueError, match="Other ExifTool"):
        check.metadata_check(before, {}, check.TARGETS[0], {})


@needs_tool
def test_named_subject_refusal_requires_matching_xml(layout):
    original, run_dir = layout
    source = jpeg(original / "named.jpg")
    # Rebuild the APP1 length after inserting rdf:about.
    raw = source.read_bytes()
    extra = b' r:about="urn:example:other"'
    size = int.from_bytes(raw[4:6], "big") + len(extra)
    source.write_bytes(raw[:4] + size.to_bytes(2, "big") +
                       raw[6:].replace(b'<r:Description', b'<r:Description' + extra))
    row = check.examine(source, run_dir, check.sha(source))
    assert row["status"] == "named_subject_refused"
    assert row["refusals"]["plan"] == row["refusals"]["apply"]

    # An identical diagnostic on a normal photo is a regression.
    ordinary = jpeg(original / "simple.jpg")
    assert not check.names_another_subject(ordinary, check.analyze(ordinary), check.TARGETS[0])
