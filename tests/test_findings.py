"""Only locally generated evidence is used in these tests."""
from copy import deepcopy
import hashlib
import json

import pytest
from PIL import Image

from photometaclean.cli.app import main
from photometaclean.metadata.classification import interpret
from photometaclean.metadata.findings import explain


URI = "http://cv.iptc.org/newscodes/digitalsourcetype/"
GENERATIVE = URI + "compositeWithTrainedAlgorithmicMedia"
GENERATED = URI + "trainedAlgorithmicMedia"
NO_JUMBF = "no embedded JPEG JUMBF detected"


def record(*actions, state="Valid", failures=("signingCredential.untrusted",)):
    checks = {"success": [{"code": code} for code in ("claimSignature.validated", "assertion.dataHash.match")],
              "failure": [{"code": code} for code in failures]}
    manifest = {"active_manifest": "current", "manifests": {"current": {"assertions": [
        {"label": "c2pa.actions.v2", "data": {"actions": list(actions)}}]}},
        "validation_results": {"activeManifest": checks}}
    return {"format": "JPEG", "manifest": manifest, "signature": state,
            "classification": interpret({}, manifest), "validation_failures": list(failures)}


def retouch():
    return {"action": "c2pa.edited", "digitalSourceType": GENERATIVE,
            "softwareAgent": {"name": "Adobe Remove Object"},
            "parameters": {"com.adobe.acr.value": "Healing changed, Uses GenAI"}}


@pytest.mark.parametrize("lang,edit,signature,binding,trust", [
    ("en", "Generative editing reported", "Claim signature verified", "Asset binding verified", "No trusted certificate path"),
    ("de", "Generative Bearbeitung gemeldet", "Manifest-Signatur bestätigt", "Dateibindung bestätigt", "Kein vertrauenswürdiger Zertifikatspfad"),
])
def test_retouch_with_untrusted_signer(lang, edit, signature, binding, trust):
    row = record({"action": "c2pa.opened"}, retouch(), retouch())
    original = deepcopy(row)
    result = explain(row, lang)
    assert result.headline == edit
    for expected in (signature, binding, trust, "c2pa.opened", "Adobe Remove Object",
                     "Healing changed, Uses GenAI", "×2", GENERATIVE):
        assert expected in result.text
    assert "Photographer mode" not in result.text and "Fotografenmodus" not in result.text
    assert row == original


@pytest.mark.parametrize("action,source,summary", [
    ("c2pa.created", GENERATED, "Generation with a trained model reported"),
    ("c2pa.placed", GENERATED, "Model-generated media reported in this step"),
    ("c2pa.edited", URI + "algorithmicallyEnhanced", "AI use unspecified"),
    ("c2pa.created", URI + "digitalCapture", "later edits unspecified"),
    ("c2pa.edited", URI + "humanEdits", "non-generative tools"),
    ("c2pa.edited", "https://example.invalid/trainedAlgorithmicMedia", "Unrecognized source type"),
])
def test_source_type_in_action_context(action, source, summary):
    result = explain(record({"action": action, "digitalSourceType": source}))
    assert summary in result.headline
    assert source in result.text


def test_only_applied_template_and_active_manifest_contribute_claims():
    row = record({"action": "c2pa.drawing", "softwareAgentIndex": 0, "digitalSourceType": GENERATIVE})
    manifests = row["manifest"]["manifests"]
    data = manifests["current"]["assertions"][0]["data"]
    data["templates"] = [{"action": "*", "digitalSourceType": GENERATED,
                          "templateParameters": {"com.adobe.appEnforced": True}},
                         {"action": "unused", "description": "unused description"}]
    data["softwareAgents"] = [{"name": "Test brush"}]
    manifests["ingredient"] = record({"action": "c2pa.created", "digitalSourceType": GENERATED})["manifest"]["manifests"]["current"]
    result = explain(row)
    assert "Test brush" in result.text and "com.adobe.appEnforced" in result.text
    assert GENERATED not in result.text and "unused description" not in result.text


def test_unverified_evidence_after_binding_failure():
    row = record(retouch(), state="Invalid", failures=["assertion.dataHash.mismatch"])
    result = explain(row)
    assert "validation failed" in result.headline and "Adobe Remove Object" in result.text
    assert "Claim signature verified" in result.text and "Asset binding failed" in result.text
    assert "Asset binding verified" not in result.text


def test_invalid_signature_even_if_trust_succeeds():
    row = record(retouch(), state="Invalid", failures=["claimSignature.mismatch"])
    checks = row["manifest"]["validation_results"]["activeManifest"]
    checks["success"] = [{"code": "signingCredential.trusted"}]
    result = explain(row)
    assert "C2PA validation failed" in result.text and "Signer trusted locally" in result.text
    assert "Claim signature verified" not in result.text


def test_no_validation_details_does_not_infer_trust_or_binding():
    row = record(retouch(), failures=[])
    del row["manifest"]["validation_results"]
    result = explain(row)
    assert "Signature unconfirmed" in result.text and "Asset binding unconfirmed" in result.text
    assert "Certificate trust undetermined" in result.text


def test_source_type_and_conditional_correction_for_own_xmp():
    meta = {"XMP-iptcExt:DigitalSourceType": GENERATED}
    row = {"format": "JPEG", "signature": NO_JUMBF, "classification": interpret(meta)}
    result = explain(row)
    assert "Generation with a trained model reported" in result.headline
    assert "independent evidence" in result.text and "preview" in result.text
    assert "XMP-iptcExt:DigitalSourceType" in result.text
    row["provenance_references"] = {"xmp": {"XMP-dcterms:Provenance": "https://example.invalid/a"},
                                    "sidecars": ["file.c2pa"]}
    result = explain(row)
    assert "Sidecar referenced" in result.verification
    assert "file.c2pa" in result.text and "https://example.invalid/a" in result.text
    assert "Photographer mode" not in result.text


@pytest.mark.parametrize("location,label", [("sidecar", "Sidecar manifest"), ("embedded", "Embedded manifest"),
                                           (None, "Manifest (location unspecified)")])
def test_manifest_origin_with_other_references(location, label):
    row = record(retouch())
    row["provenance_references"] = {"sidecars": ["first.c2pa", "second.c2pa"], "xmp": {}}
    if location:
        row["manifest_location"] = location
    result = explain(row)
    assert label in result.verification
    assert label + " · reported actions" in result.text and "second.c2pa" in result.text
    if location != "embedded":
        assert "embedded" not in result.text.lower()


@pytest.mark.parametrize("row,en,de", [
    ({"signature": NO_JUMBF}, "No embedded manifest detected", "Kein eingebettetes Manifest erkannt"),
    ({"signature": "unchecked"}, "Provenance unchecked", "Herkunft ungeprüft"),
    ({"signature": "verification unavailable", "validation_error": "test error"}, "Verification unavailable", "Prüfung nicht verfügbar"),
    ({"error": "decoding failed"}, "Analysis failed", "Analyse fehlgeschlagen"),
])
def test_no_reliable_classification(row, en, de):
    for lang, phrase in [("en", en), ("de", de)]:
        result = explain(row, lang)
        assert phrase in result.verification
        assert "digitalCapture" not in result.headline
        if "error" in row or "validation_error" in row:
            assert (row.get("error") or row["validation_error"]) in result.text


def test_real_cli_reads_synthetic_file_and_keeps_json_contract(tmp_path, capsys):
    photo = tmp_path / "Test ä.jpg"
    Image.new("RGB", (9, 11)).save(photo)
    original = hashlib.sha256(photo.read_bytes()).digest()
    assert main(["explain", str(photo), "--lang", "de", "--workers", "1"]) == 0
    readable = capsys.readouterr().out
    assert "Test ä.jpg" in readable and "Korrektur und Neu-Export" in readable and "Kein eingebettetes Manifest" in readable
    assert main(["analyze", str(photo), "--workers", "1"]) == 0
    assert "metadata" in json.loads(capsys.readouterr().out)["analysis"]
    assert hashlib.sha256(photo.read_bytes()).digest() == original


def test_cli_explain_error_continues_to_next_file(tmp_path, monkeypatch, capsys):
    rows = [(tmp_path / "a", {"error": "broken"}), (tmp_path / "b", record(retouch()))]
    monkeypatch.setattr("photometaclean.cli.app.analyses", lambda *args: iter(rows))
    assert main(["explain", str(tmp_path)]) == 1
    output = capsys.readouterr().out
    assert "broken" in output and "Adobe Remove Object" in output


def test_cli_xmp_reference_then_unreadable_sidecar(tmp_path, capsys):
    photo = tmp_path / "source.jpg"
    xmp = b"""<x:xmpmeta xmlns:x="adobe:ns:meta/">
      <rdf:RDF xmlns:rdf="http://www.w3.org/1999/02/22-rdf-syntax-ns#">
        <rdf:Description rdf:about="" xmlns:dcterms="http://purl.org/dc/terms/"
                         dcterms:provenance="https://example.invalid/credential"/>
      </rdf:RDF></x:xmpmeta>"""
    Image.new("RGB", (8, 9)).save(photo)
    jpeg = photo.read_bytes()
    payload = b"http://ns.adobe.com/xap/1.0/\0" + xmp
    app1 = b"\xff\xe1" + (len(payload) + 2).to_bytes(2, "big") + payload
    photo.write_bytes(jpeg[:2] + app1 + jpeg[2:])
    args = ["explain", str(photo), "--workers", "1"]
    assert main(args) == 0
    text = capsys.readouterr().out
    assert "XMP provenance reference" in text and "https://example.invalid/credential" in text
    assert "Claim signature verified" not in text
    photo.with_suffix(".c2pa").write_bytes(b"synthetic unreadable sidecar")
    assert main(args) == 0
    text = capsys.readouterr().out
    assert "Sidecar referenced" in text and "Verification unavailable" in text
    assert "source.c2pa" in text and "Sidecar manifest · reported actions" not in text


def test_gui_first_tab_and_table_use_same_sidecar_evidence(tmp_path, monkeypatch):
    monkeypatch.setenv("QT_QPA_PLATFORM", "offscreen")
    qt = pytest.importorskip("PySide6.QtWidgets")
    from PySide6.QtCore import QSettings
    from photometaclean.gui.app import Window

    app = qt.QApplication.instance() or qt.QApplication([])
    settings = QSettings(str(tmp_path / "settings.ini"), QSettings.Format.IniFormat)
    settings.setValue("language", "de")
    monkeypatch.setattr("photometaclean.gui.app.QSettings", lambda *args: settings)
    window = Window()
    try:
        row = record(retouch())
        row["manifest_location"] = "sidecar"
        row["provenance_references"] = {"sidecars": ["test.c2pa"], "xmp": {}}
        window.counts = dict(done=0, size=0, skipped=0, errors=0, flagged=0, corrected=0, unchanged=0)
        window.add_row({"task": "analyze", "relative": "test.jpg", "path": "test.jpg", "data": row})
        expected = explain(row, "de")
        assert window.table.item(0, 4).text() == expected.headline
        assert window.table.item(0, 5).text() == expected.verification

        def inspect(dialog):
            tabs = dialog.findChild(qt.QTabWidget)
            assert tabs.tabText(0) == "Herkunftsbefund" and tabs.widget(0).isReadOnly()
            assert tabs.widget(0).toPlainText() == expected.text
            assert tabs.tabText(tabs.count() - 1) == "Vollständiger Bericht"
        monkeypatch.setattr(qt.QDialog, "exec", inspect)
        window.detail(0)
    finally:
        window.close()
        app.processEvents()


def test_history_follows_only_linked_parents_and_handles_cycles():
    row = record({"action": "c2pa.transcoded"})
    manifest = row["manifest"]
    active = manifest["active_manifest"]
    store = manifest["manifests"]
    store[active]["ingredients"] = [{"relationship": "parentOf", "active_manifest": "previous"},
                                    {"relationship": "inputTo", "active_manifest": "model-reference"}]
    parent = record({"action": "c2pa.created", "digitalSourceType": GENERATED})["manifest"]
    store["previous"] = parent["manifests"][parent["active_manifest"]]
    store["previous"]["ingredients"] = [{"relationship": "parentOf", "active_manifest": active}]
    store["model-reference"] = store["previous"]
    result = explain(row)
    assert "model-reference" not in result.text
    assert "Earlier exports" in result.text
    assert "Generation with a trained model reported" in result.text
    assert "Generation with a trained model reported" not in result.headline


def test_ai_fields_respect_flag_state_namespace_and_context():
    meta = {"XMP-aux:Main:EnhanceDenoiseAlreadyApplied": True,
            "XMP-aux:Main:EnhanceSuperResolutionAlreadyApplied": "False",
            "XMP-crs:Main:LensBlur": {"Version": 1},
            "XMP-iptcExt:Main:AIPromptInformation": "synthetic private text",
            "IFD0:Main:AISystemUsed": "namesake"}
    result = explain({"metadata": meta})
    assert result.headline == "Creation history undetermined"
    assert "Denoise · reported as applied" in result.text
    assert "Super Resolution · reported as off" in result.text
    assert "Lens blur · setting recorded" in result.text
    assert "AI prompt · field populated" in result.text
    assert "synthetic private text" not in result.text and "namesake" not in result.text


def test_firefly_fill_requires_an_exact_retouch_area_method():
    row = {"metadata": {"XMP-crs:Main:RetouchAreas": [{"Fill_method": "firefly"}, {"Fill_method": "firefly"},
                                                      {"Fill_method": "clone"}, {"Description": "firefly"}]}}
    result = explain(row, "de")
    assert "Firefly-Füllung in einem Retuschierbereich (×2)" in result.text
    assert "Entstehungsgeschichte offen" in result.headline
