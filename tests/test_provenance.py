from pathlib import Path

from PIL import Image
import pytest

from photometaclean.metadata.analysis import analyze
from photometaclean.metadata.provenance import sidecars


def test_adjacent_manifest_after_prior_analysis(tmp_path):
    photo = tmp_path / "sample.jpg"
    Image.new("RGB", (20, 16), "gray").save(photo)
    assert not sidecars(photo)
    detached = photo.with_suffix(".C2pA")
    detached.write_bytes(b"invalid synthetic manifest")
    result = analyze(photo)
    assert result["provenance_references"]["sidecars"] == [str(detached)]
    assert result["signature"] == "verification unavailable"
    assert result["validation_error"]


def test_ambiguous_adjacent_manifests(tmp_path):
    photo = tmp_path / "image.jpg"
    Image.new("RGB", (20, 16)).save(photo)
    for name in ("image.c2pa", "image.jpg.c2pa"):
        (tmp_path / name).write_bytes(b"sample")
    assert "Multiple adjacent" in analyze(photo)["validation_error"]


def test_sidecar_symlink_reported_without_read(tmp_path):
    photo = tmp_path / "sample.jpg"
    Image.new("RGB", (20, 16)).save(photo)
    try:
        photo.with_suffix(".c2pa").symlink_to(tmp_path / "unreadable")
    except OSError:
        pytest.skip("symlink creation unavailable")
    assert "regular file" in analyze(photo)["validation_error"]


def test_offline_reference_recognized_by_namespace_even_with_custom_prefix(tmp_path):
    from photometaclean.core.edit import XMP, plan

    photo = tmp_path / "sample.jpg"
    Image.new("RGB", (16, 16)).save(photo)
    jpeg = photo.read_bytes()
    url = "https://example.invalid/claims"
    packet = (XMP + b'<r:RDF xmlns:r="http://www.w3.org/1999/02/22-rdf-syntax-ns#">'
              b'<r:Description xmlns:p="http://purl.org/dc/terms/">'
              b'<p:provenance r:resource="' + url.encode() + b'"/></r:Description></r:RDF>')
    photo.write_bytes(jpeg[:2] + b"\xff\xe1" + (len(packet)+2).to_bytes(2,"big") + packet + jpeg[2:])
    result = analyze(photo)
    assert result["provenance_references"]["xmp"]["dcterms:provenance"] == [url]
    assert not result.get("manifest")
    with pytest.raises(ValueError, match="provenance"):
        plan(photo, {"JPEG:Comment": None})


def test_rdf_resource_source_type_visible_in_read_and_edit_paths(tmp_path):
    from photometaclean.core.edit import XMP, plan
    from photometaclean.metadata.findings import explain

    uri = "http://cv.iptc.org/newscodes/digitalsourcetype/compositeWithTrainedAlgorithmicMedia"
    packet = (XMP + b'<r:RDF xmlns:r="http://www.w3.org/1999/02/22-rdf-syntax-ns#"><r:Description '
              b'xmlns:i="http://iptc.org/std/Iptc4xmpExt/2008-02-29/"><i:DigitalSourceType r:resource="'
              + uri.encode() + b'"/></r:Description></r:RDF>')
    photo = tmp_path / "control.jpg"
    Image.new("RGB", (12, 16)).save(photo)
    raw = photo.read_bytes()
    photo.write_bytes(raw[:2] + b"\xff\xe1" + (len(packet)+2).to_bytes(2,"big") + packet + raw[2:])
    row = analyze(photo)
    assert [d["value"] for d in row["classification"]["declarations"]] == [uri]
    assert "Generative Bearbeitung" in explain(row, "de").headline
    preview = plan(photo, {"XMP-iptcExt:DigitalSourceType": None}, "generated test fixture")
    assert preview["changes"][0]["before"] == uri
