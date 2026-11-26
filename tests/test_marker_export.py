"""Exercise real inspection, lossless edits and the text intended for a public forum."""
import json
import struct
import zlib

from PIL import Image, ImageCms, PngImagePlugin
import pytest

from photometaclean.core.edit import plan
from photometaclean.core.patch import patch_file
from photometaclean.formats.recipes import RECIPE_FIELDS
from photometaclean.metadata.analysis import analyze
from photometaclean.metadata.feedback import feedback_text, snapshot
from photometaclean.metadata.generators import generator_signal
from photometaclean.metadata.classification import interpret

PROFILE = ImageCms.ImageCmsProfile(ImageCms.createProfile("sRGB")).tobytes()
SETTINGS = "private prompt\nSteps: 20, Sampler: Euler, CFG scale: 7.0, Seed: 123"
GRAPH = json.dumps({"1": {"class_type": "Sampler", "inputs": {"text": "private prompt"}}})
WORKFLOW = json.dumps({"nodes": [{"id": 1, "type": "Sampler"}], "links": []})


@pytest.mark.parametrize("key,value", [
    ("parameters", SETTINGS), ("prompt", GRAPH), ("workflow", WORKFLOW),
    ("invokeai_metadata", '{"app_version":"5","seed":2}'),
    ("invokeai_workflow", '{"nodes":[{"id":1,"type":"image"}],"edges":[]}'),
])
@pytest.mark.parametrize("storage", ["text", "compressed", "itxt", "compressed_itxt"])
def test_click_removes_the_complete_png_chunk(tmp_path, key, value, storage):
    info = PngImagePlugin.PngInfo()
    info.add_text("Copyright", "Test artist")
    info.add_text("Comment", "keep my notes")
    method = info.add_itxt if "itxt" in storage else info.add_text
    method(key, value, zip="compressed" in storage)
    src = tmp_path / "example.png"
    Image.new("RGB", (14, 16), "brown").save(src, pnginfo=info, icc_profile=PROFILE)
    original = src.read_bytes()
    out = tmp_path / "out" / src.name
    result = patch_file(src, out, RECIPE_FIELDS, True)
    assert result.get("audit"), (result.get("reason"), result["analysis"].get("editing_signals"))
    assert result["postcheck"]["state"] == "clear"
    assert result["audit"]["integrity_before"] == result["audit"]["integrity_after"]
    assert src.read_bytes() == original
    with Image.open(out) as im:
        assert key not in im.info and im.info["Comment"] == "keep my notes"
        assert im.info["Copyright"] == "Test artist" and im.info["icc_profile"] == PROFILE
    assert len(out.read_bytes()) < len(original)


def test_adobe_settings_are_distinct_from_applied_edit_and_camera_origin(tmp_path):
    import xml.etree.ElementTree as ET
    from photometaclean.formats.xmp import NAMESPACES, RDF
    from photometaclean.core.edit import XMP
    rdf = ET.Element(f"{{{RDF}}}RDF")
    desc = ET.SubElement(rdf, f"{{{RDF}}}Description")
    for group, name, val in [
        ("aux", "EnhanceDenoiseLumaAmount", "30"), ("aux", "EnhanceDenoiseVersion", "1"),
        ("aux", "EnhanceDenoiseAlreadyApplied", "True"), ("iptcExt", "DigitalSourceType", "digitalCapture"),
    ]:
        desc.set(f"{{{NAMESPACES[group]}}}{name}", val)
    src = tmp_path / "photo.jpg"
    Image.new("RGB", (28, 22)).save(src, comment=b"retained", icc_profile=PROFILE)
    raw = src.read_bytes()
    packet = XMP + ET.tostring(rdf)
    original = raw[:2] + b"\xff\xe1" + struct.pack(">H", len(packet)+2) + packet + raw[2:]
    src.write_bytes(original)
    dst = tmp_path / "out.jpg"
    result = patch_file(src, dst, RECIPE_FIELDS, True, camera_confirmation="camera photo")
    assert len(result["audit"]["changes"]) == 2
    assert src.read_bytes() == original and len(dst.read_bytes()) == len(original)
    assert result["audit"]["integrity_after"] == result["audit"]["integrity_before"]
    assert result["postcheck"]["state"] == "remaining"
    assert {s["state"] for s in result["postcheck"]["signals"]} == {"applied"}
    assert result["postcheck"]["source_types"][0]["value"] == "digitalCapture"


def test_generic_text_and_unknown_graphs_keep_the_original(tmp_path):
    info = PngImagePlugin.PngInfo()
    info.add_text("Title", "AI and fireflies")
    info.add_text("parameters", "ordinary photographic details")
    info.add_text("workflow", '{"nodes":[],"links":[]}')
    src = tmp_path / "picture.png"
    Image.new("RGB", (4, 4)).save(src, pnginfo=info)
    result = patch_file(src, tmp_path / "copy.png", RECIPE_FIELDS, True)
    assert result.get("copy_only") and not result["analysis"]["editing_signals"]
    assert not generator_signal("PNG:Doc1:Parameters", SETTINGS)
    assert not generator_signal("IFD0:Software", "my favorite ComfyUI images")


def test_malformed_png_recipe_blocked_before_writing(tmp_path):
    src = tmp_path / "bad.png"
    Image.new("RGB", (3, 4)).save(src)
    packet = b"zTXtparameters\0\0" + zlib.compress(b" " * (1024 * 1024 + 1))
    raw = src.read_bytes()
    src.write_bytes(raw[:33] + struct.pack(">I", len(packet)-4) + packet + struct.pack(">I", zlib.crc32(packet)) + raw[33:])
    with pytest.raises(ValueError, match="Oversized|size limit"):
        plan(src, {"PNG:Parameters": None})


def test_detached_credentials_keep_png_recipe(tmp_path):
    src = tmp_path / "protected.png"
    info = PngImagePlugin.PngInfo()
    info.add_text("parameters", SETTINGS)
    Image.new("RGB", (4, 4)).save(src, pnginfo=info)
    src.with_suffix(".c2pa").write_bytes(b"unreadable manifest")
    result = patch_file(src, tmp_path / "copy.png", RECIPE_FIELDS, True)
    assert result["reason"] == "provenance" and result.get("copy_only")


@pytest.mark.parametrize("field,known", [("XMP-iptcExt:Main:DigitalSourceType", True),
                                         ("unrelated:DigitalSourceType", False)])
def test_short_iptc_term_requires_correct_scope(field, known):
    meaning = interpret({field: "trainedAlgorithmicMedia"})["declarations"][0]["meaning"]
    assert ("trained model" in meaning) is known


def test_forum_report_never_dumps_private_values_or_private_errors(tmp_path):
    info = PngImagePlugin.PngInfo()
    info.add_text("Author", "Secret Person")
    info.add_text("parameters", SETTINGS)
    info.add_text("FireflyExperimental", "Secret Person")
    src = tmp_path / "private-file.png"
    Image.new("RGB", (6, 9)).save(src, pnginfo=info)
    analysis = analyze(src)
    analysis["warnings"] = str(src)
    row = {"task":"analyze", "data":analysis, "error":"Secret Person"}
    for lang in ("en", "de"):
        report = feedback_text(row, lang, "Instagram")
        assert "Instagram" in report and "PNG:Parameters" in report
        for private in ("Secret Person", "private prompt", str(tmp_path), src.name, analysis["sha256"], "FireflyExperimental"):
            assert private not in report
        assert "PNG:FireflyExperimental" in feedback_text(row, lang, extra=True)
    assert snapshot(analysis)["incomplete"]


def test_copy_report_matches_the_actual_output(tmp_path):
    info = PngImagePlugin.PngInfo()
    info.add_text("parameters", SETTINGS)
    src = tmp_path / "photo.png"
    Image.new("RGB", (4, 4)).save(src, pnginfo=info)
    result = patch_file(src, tmp_path / "out.png", RECIPE_FIELDS, True)
    report = feedback_text({"task":"patch", "data":result}, "de", "X")
    before, after = report.split("Geprüfte Ausgabekopie")
    assert "PNG:Parameters" in before and "PNG:Parameters" not in after
    assert "private prompt" not in report and "Keine bekannten" in after


def test_folder_patch_keeps_complex_field_and_removes_independent_settings(tmp_path):
    from photometaclean.formats.xmp import FieldReviewRequired
    from photometaclean.core.review import review
    src = tmp_path / "mixed.png"
    raw = ('<r:RDF xmlns:r="http://www.w3.org/1999/02/22-rdf-syntax-ns#"><r:Description '
           'xmlns:i="http://iptc.org/std/Iptc4xmpExt/2008-02-29/" '
           'xmlns:a="http://ns.adobe.com/exif/1.0/aux/" a:EnhanceDenoiseLumaAmount="44">'
           '<i:AIPromptInformation><r:Alt><r:li xml:lang="x-default">example</r:li></r:Alt>'
           '</i:AIPromptInformation></r:Description></r:RDF>')
    info = PngImagePlugin.PngInfo()
    info.add_itxt("XML:com.adobe.xmp", raw)
    info.add_text("parameters", SETTINGS)
    Image.new("RGB", (5, 6)).save(src, pnginfo=info)
    with pytest.raises(FieldReviewRequired):
        review(src, {"XMP-iptcExt:AIPromptInformation": None, "PNG:Parameters": None})
    out = tmp_path / "out.png"
    result = patch_file(src, out, RECIPE_FIELDS, True)
    assert {item["field"] for item in result["audit"]["changes"]} == {"XMP-aux:EnhanceDenoiseLumaAmount", "PNG:Parameters"}
    assert set(result["retained_fields"]) == {"XMP-iptcExt:AIPromptInformation"}
    assert result["postcheck"]["state"] == "remaining"
    assert b"<r:li" in out.read_bytes() and b"parameters" not in out.read_bytes()


def test_report_with_malformed_manifest_assertions_is_still_available():
    record = {"task": "analyze", "data": {"format": "JPEG", "validation_error": "private input",
              "manifest": {"active_manifest": "a", "manifests": {"a": {"assertions": [
                  None, {"label": None}, {"label": "c2pa.actions", "data": "private input"}
              ]}}, "validation_results": {"activeManifest": {"failure": [None, {"code": []}]}}}}}
    report = feedback_text(record, "de")
    assert "C2PA" in report and "unvollständig" in report and "private input" not in report
