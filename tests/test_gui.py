import os
from pathlib import Path
import time

import pytest
from PIL import Image

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
pytest.importorskip("PySide6.QtWidgets")
from PySide6.QtCore import QSettings
from PySide6.QtWidgets import QApplication, QMessageBox

from photometaclean.gui.app import Window
from photometaclean.core.review import review, apply_reviewed, destination_path


@pytest.fixture
def window(tmp_path,monkeypatch):
    app = QApplication.instance() or QApplication([])
    settings = QSettings(str(tmp_path/"settings.ini"), QSettings.Format.IniFormat)
    settings.setValue("workers",1)
    monkeypatch.setattr("photometaclean.gui.app.QSettings",lambda *args:settings)
    w = Window()
    yield w
    w.close()
    app.processEvents()


def source(path):
    Image.new("RGB",(8,8),"red").save(path,"JPEG")
    data = path.read_bytes()
    path.write_bytes(data[:2]+b"\xff\xfe\x00\x08secret"+data[2:])
    return path


def finish(w):
    end = time.monotonic()+20
    while w.timer.isActive() and time.monotonic()<end:
        QApplication.processEvents()
        time.sleep(.005)
    assert not w.timer.isActive()


def test_review_apply_round_trip(window,tmp_path,monkeypatch):
    p = source(tmp_path/"ä file.jpg")
    original = p.read_bytes()
    window.add([p])
    window.output = tmp_path/"output"
    window.mode.setCurrentIndex(3)
    monkeypatch.setattr(window,"fields",lambda mode: ({"JPEG:Comment":None},""))
    window.start()
    finish(window)
    assert window.apply_button.isEnabled()
    assert window.read_row(0)["data"]["preview"]["changes"][0]["field"] == "JPEG:Comment"
    window.table.selectRow(0)
    monkeypatch.setattr(QMessageBox,"question",lambda *args:QMessageBox.StandardButton.Yes)
    window.apply()
    finish(window)
    assert window.counts["corrected"] == 1
    assert p.read_bytes() == original
    assert b"secret" not in (window.output/p.name).read_bytes()


@pytest.mark.parametrize("change",["hash","sidecar","extension-sidecar","permissions"])
def test_review_rechecks_input(tmp_path,change):
    p = source(tmp_path/"test.jpg")
    record = review(p,{"JPEG:Comment":None})
    if change == "hash":
        p.write_bytes(p.read_bytes().replace(b"secret",b"public"))
    elif change == "permissions":
        record["preview"]["changes"] = []
    else:
        (tmp_path/("test.C2PA" if change=="sidecar" else "test.jpg.c2pa")).touch()
    dest = tmp_path/"out.jpg"
    with pytest.raises(ValueError):
        apply_reviewed(record,dest)
    assert not dest.exists()


def test_protected_destinations(tmp_path,monkeypatch):
    monkeypatch.chdir(tmp_path)
    for name in ("vorm Update","Nach Update"):
        with pytest.raises(ValueError):
            destination_path(tmp_path/name/"file.json")


def test_compare_unmatched(window,tmp_path):
    left,right = tmp_path/"left",tmp_path/"right"
    left.mkdir()
    right.mkdir()
    source(right/"only.jpg")
    window.add([left,right])
    window.mode.setCurrentIndex(1)
    window.start()
    finish(window)
    assert window.counts["skipped"] == 1
    assert window.read_row(0)["data"]["right_exists"]


def test_localized_modes(window):
    assert window.mode.count() == 5
    window.de = True
    window.mode_changed()
    assert "Doppelklick" in window.hint.text()


def test_parallel_analysis_and_report(window,tmp_path,monkeypatch):
    from PySide6.QtWidgets import QFileDialog

    inputs = tmp_path/"inputs"
    inputs.mkdir()
    nested = inputs/"nested"
    nested.mkdir()
    for folder in [inputs,nested]:
        source(folder/"gleich.jpg")
    window.output = inputs/"output"
    window.output.mkdir()
    source(window.output/"previous.jpg")
    window.settings.setValue("workers",2)
    window.add([inputs,nested])
    window.start()
    finish(window)
    assert window.counts["found"] == window.counts["done"] == 2
    assert window.counts["errors"] == 0
    target = tmp_path/"report.json"
    monkeypatch.setattr(QFileDialog,"getSaveFileName",lambda *args:(str(target),"JSON"))
    window.export()
    import json
    rows = json.loads(target.read_text())
    assert {row["relative"] for row in rows} == {"gleich.jpg", str(Path("nested")/"gleich.jpg")}
    assert all(row["data"]["frames"] for row in rows)


def test_compare_changes(window,tmp_path):
    a = source(tmp_path/"one.jpg")
    b = tmp_path/"two.jpg"
    b.write_bytes(a.read_bytes().replace(b"secret",b"public"))
    window.add([a,b])
    window.mode.setCurrentIndex(1)
    window.start()
    finish(window)
    data = window.read_row(0)["data"]
    assert any(pair == ["secret","public"] for pair in data["differences"]["changed"].values())


def test_cancel_before_discovery(tmp_path):
    from photometaclean.gui.jobs import Batch

    source(tmp_path/"img.jpg")
    job = Batch("analyze",[tmp_path],True,None,1)
    seen = []
    job.result.connect(seen.append)
    job.stop.set()
    job.run()
    assert not seen


def test_mouse_batch_only_selects_eligible_previews(window, tmp_path, monkeypatch):
    from PySide6.QtCore import QTimer, Qt
    from PySide6.QtTest import QTest
    from PySide6.QtWidgets import QCheckBox, QDialogButtonBox, QFileDialog

    folder = tmp_path / "inputs"
    folder.mkdir()
    for name in ("one.jpg", "two.jpg", "protected.jpg"):
        source(folder / name)
    (folder / "protected.c2pa").write_bytes(b"synthetic sidecar")
    output = tmp_path / "copies"
    output.mkdir()
    dialogs = iter([str(folder), str(output)])
    monkeypatch.setattr(QFileDialog, "getExistingDirectory", lambda *args: next(dialogs))
    monkeypatch.setattr(QMessageBox, "question", lambda *args: QMessageBox.StandardButton.Yes)
    window.show()
    QTest.mouseClick(window.controls[1], Qt.MouseButton.LeftButton)
    window.mode.setCurrentIndex(window.mode.findData("privacy"))

    def approve_field():
        dialog = QApplication.activeModalWidget()
        box = dialog.findChild(QCheckBox, "JPEG:Comment")
        assert box.text() != "JPEG:Comment"
        box.click()
        dialog.findChild(QDialogButtonBox).button(QDialogButtonBox.StandardButton.Ok).click()
    QTimer.singleShot(0, approve_field)
    QTest.mouseClick(window.start_button, Qt.MouseButton.LeftButton)
    finish(window)
    assert window.select_button.isEnabled() and not window.apply_button.isEnabled()
    QTest.mouseClick(window.select_button, Qt.MouseButton.LeftButton)
    assert len(window.table.selectionModel().selectedRows()) == 2
    QTest.mouseClick(window.apply_button, Qt.MouseButton.LeftButton)
    finish(window)
    assert sorted(p.name for p in output.glob("*.jpg")) == ["one.jpg", "two.jpg"]
    assert window.open_button.isEnabled()
    opened = []
    monkeypatch.setattr("photometaclean.gui.app.QDesktopServices.openUrl", opened.append)
    QTest.mouseClick(window.open_button, Qt.MouseButton.LeftButton)
    assert Path(opened[0].toLocalFile()) == output


def test_photographer_preview_needs_evidence_in_dialog(window):
    from PySide6.QtCore import QTimer
    from PySide6.QtWidgets import QDialogButtonBox, QPlainTextEdit

    def type_evidence():
        dialog = QApplication.activeModalWidget()
        accept = dialog.findChild(QDialogButtonBox).button(QDialogButtonBox.StandardButton.Ok)
        assert not accept.isEnabled()
        dialog.findChild(QPlainTextEdit).setPlainText("Synthetic camera capture and edit log reviewed")
        assert accept.isEnabled()
        accept.click()
    QTimer.singleShot(0, type_evidence)
    changes, evidence = window.fields("photo")
    assert changes == {"XMP-iptcExt:DigitalSourceType": None}
    assert "capture" in evidence


@pytest.mark.parametrize("only_changed", [False, True])
def test_patch_button_from_source_to_verified_mixed_outputs(window, tmp_path, monkeypatch, only_changed):
    from PIL.PngImagePlugin import PngInfo
    from PySide6.QtCore import QTimer
    from PySide6.QtWidgets import QCheckBox, QDialogButtonBox, QFileDialog

    folder = tmp_path / "Photos"
    nested = folder / "nested"
    nested.mkdir(parents=True)
    patch = folder / "Patch"
    patch.mkdir()
    source(patch / "previous.jpg")
    (patch / "PhotoMetaClean-abcd1234.jsonl").write_text('{"file":"previous.jpg","stage": "patch"}\n')
    first = source(nested / "sample.jpg")
    second = nested / "sample.png"
    tags = PngInfo()
    tags.add_text("Comment", "synthetic")
    Image.new("RGB", (13, 17)).save(second, pnginfo=tags)
    protected = source(folder / "protected.jpg")
    protected.with_suffix(".c2pa").touch()
    hashes = {p: p.read_bytes() for p in (first, second, protected)}
    monkeypatch.setattr(QFileDialog, "getExistingDirectory", lambda *args: str(folder))
    window.settings.setValue("patch_fields", ["JPEG:Comment", "PNG:Comment"])
    assert not window.only_changed.isChecked()
    window.only_changed.setChecked(only_changed)
    (folder / "empty").mkdir()
    window.patch_button.click()
    finish(window)
    assert window.job.task == "patch"
    assert (patch / "previous.jpg").is_file()
    assert window.output == folder / "Patch-2"
    assert window.patch_report.parent == folder / "Patch-2-Protokolle"
    assert not list(window.output.rglob("*.jsonl"))
    patch = window.output
    assert window.counts["corrected"] == 2
    assert window.counts["flagged"] >= 1
    assert all(p.read_bytes() == content for p, content in hashes.items())
    assert (patch / "nested/sample.jpg").is_file() and (patch / "nested/sample.png").is_file()
    assert not (patch / "Patch").exists()
    if only_changed:
        assert not (patch / protected.name).exists()
    else:
        assert (patch / protected.name).read_bytes() == protected.read_bytes()
        assert (patch / "protected.c2pa").is_file() and (patch / "empty").is_dir()
        assert window.counts["unchanged"] == 2
    import json
    events = [json.loads(line) for line in window.patch_report.read_text(encoding="utf8").splitlines()]
    assert len(events) == 4 and all(e["stage"] == "patch" for e in events)
    assert sum("destination" in e for e in events) == (2 if only_changed else 4)


@pytest.mark.parametrize("de", [True, False])
def test_about_all_desktops(window, de):
    from PySide6.QtCore import QTimer
    from PySide6.QtWidgets import QDialog, QLabel
    from photometaclean import __version__
    window.de = de
    labels = []
    def inspect():
        dialog = QApplication.activeModalWidget()
        labels.extend((label.text(), label.openExternalLinks()) for label in dialog.findChildren(QLabel))
        QDialog.accept(dialog)
    QTimer.singleShot(0, inspect)
    window.about_button.click()
    assert not window.windowIcon().pixmap(48, 48).isNull()
    text = " ".join(t for t, _ in labels)
    assert __version__ in text and "Mathias Zimmermann" in text
    assert ("Kostenlos" if de else "Free") in text
    assert any("https://github.com/Zimbo88/PhotoMetaClean" in t and live for t, live in labels)


def test_one_click_default_repeated_run_and_chosen_output(window, tmp_path, monkeypatch):
    from PySide6.QtWidgets import QFileDialog
    folder = tmp_path / "source"
    folder.mkdir()
    photo = source(folder / "sample.jpg")
    output = tmp_path / "chosen"
    output.mkdir()
    window.add([folder])
    monkeypatch.setattr(QFileDialog, "getExistingDirectory", lambda *args: str(output))
    window.pick_output()
    for run in range(2):
        window.patch_button.click()
        finish(window)
        assert window.counts["unchanged"] == 1 and window.counts["errors"] == 0
        assert (window.output / photo.name).read_bytes() == photo.read_bytes()
        if run == 0:
            assert window.output == output / "Patch"
        else:
            assert window.output.parent == output
    assert not (folder / "Patch").exists()


def test_one_click_respects_photo_approval(window, tmp_path, monkeypatch):
    from photometaclean.core.review import FIELDS
    from photometaclean.core.edit import XMP
    folder = tmp_path / "photos"
    folder.mkdir()
    photo = source(folder / "one.jpg")
    packet = (b'<r:RDF xmlns:r="http://www.w3.org/1999/02/22-rdf-syntax-ns#"><r:Description '
              b'xmlns:i="http://iptc.org/std/Iptc4xmpExt/2008-02-29/" i:DigitalSourceType="'
              b'http://cv.iptc.org/newscodes/digitalsourcetype/trainedAlgorithmicMedia"/></r:RDF>')
    data = photo.read_bytes()
    photo.write_bytes(data[:2] + b"\xff\xe1" + (2+len(XMP+packet)).to_bytes(2, "big") + XMP + packet + data[2:])
    original = photo.read_bytes()
    # Only the inspected and selected source is approved, even with matching metadata.
    other = folder / "two.jpg"
    other.write_bytes(original)
    window.add([folder])
    window.mode.setCurrentIndex(window.mode.findData("photo"))
    monkeypatch.setattr(window, "fields", lambda mode: ({FIELDS[-1]: None}, "Incorrect declaration in synthetic controls"))
    window.start()
    finish(window)
    row = next(i for i in window.review_rows if Path(window.read_row(i)["path"]) == photo)
    window.table.selectRow(row)
    window.patch_button.click()
    finish(window)
    assert window.counts["corrected"] == window.counts["unchanged"] == 1
    assert original == photo.read_bytes() == other.read_bytes() == (window.output/other.name).read_bytes()
    assert b"trainedAlgorithmicMedia" not in (window.output/photo.name).read_bytes()

@pytest.mark.parametrize("term,enabled,corrected", [
    ("trainedAlgorithmicMedia", True, True),
    ("trainedAlgorithmicMedia", False, False),
    ("compositeWithTrainedAlgorithmicMedia", True, True),
    ("digitalCapture", True, False),
    ("algorithmicallyEnhanced", True, True),
])
def test_first_click_cleans_selected_jpeg_source_types(window, tmp_path, term, enabled, corrected):
    from photometaclean.core.edit import XMP

    folder = tmp_path / "photos"
    folder.mkdir()
    photo = source(folder / "camera.jpg")
    import xml.etree.ElementTree as ET
    from photometaclean.formats.xmp import NAMESPACES, RDF
    rdf = ET.Element(f"{{{RDF}}}RDF")
    description = ET.SubElement(rdf, f"{{{RDF}}}Description")
    description.set(f"{{{NAMESPACES['aux']}}}SerialNumber", "test-device")
    description.set(f"{{{NAMESPACES['iptcExt']}}}DigitalSourceType",
                    f"http://cv.iptc.org/newscodes/digitalsourcetype/{term}")
    xmp = XMP + ET.tostring(rdf, encoding="utf-8")
    data = photo.read_bytes()
    original = data[:2] + b"\xff\xe1" + (len(xmp) + 2).to_bytes(2, "big") + xmp + data[2:]
    photo.write_bytes(original)
    assert window.camera_patch.isChecked() and not window.saved_rules()
    window.camera_patch.setChecked(enabled)
    window.add([folder])
    window.patch_button.click()
    finish(window)
    copy = (folder / "Patch" / photo.name).read_bytes()
    assert window.counts["corrected"] == int(corrected)
    assert (copy != original) == corrected
    assert b"test-device" in copy and b"secret" in copy and photo.read_bytes() == original
    assert (term.encode() not in copy) == corrected
    if corrected:
        assert window.read_row(0)["data"]["audit"]["evidence"]
        assert window.table.item(0, 6).text() != "Patch"


def test_forum_report_after_clean_scan_and_clipboard(window, tmp_path, monkeypatch):
    from PySide6 import QtWidgets as W
    from PySide6.QtGui import QGuiApplication
    from photometaclean.metadata.feedback import DISCUSSIONS
    picture = source(tmp_path / "private-name.jpg")
    window.add([picture])
    window.start()
    finish(window)
    window.table.selectRow(0)
    opened = []
    monkeypatch.setattr("photometaclean.gui.feedback.QDesktopServices.openUrl", lambda url: opened.append(url.toString()))

    def inspect(dialog):
        preview = dialog.findChild(W.QPlainTextEdit)
        platform = dialog.findChild(W.QComboBox)
        platform.setCurrentIndex(platform.findText("Instagram"))
        buttons = dialog.findChildren(W.QPushButton)
        assert opened == [] and picture.name not in preview.toPlainText() and "Instagram" in preview.toPlainText()
        copy = next(b for b in buttons if b.text() in ("Bericht kopieren", "Copy report"))
        copy.click()
        assert QGuiApplication.clipboard().text() == preview.toPlainText()
        assert "secret" not in preview.toPlainText() and not opened
        next(b for b in buttons if b.text() in ("Forum öffnen", "Open forum")).click()
        assert opened == [DISCUSSIONS]
    monkeypatch.setattr(W.QDialog, "exec", inspect)
    assert window.feedback_button.isEnabled()
    window.feedback_button.click()


def test_history_checkbox_is_optional_and_independent(window,tmp_path):
    from test_history import XML
    from test_hdr_edit import segment
    from photometaclean.formats.share import XMP

    folder = tmp_path/"photos"
    folder.mkdir()
    photo=source(folder/"image.jpg")
    raw=photo.read_bytes()
    photo.write_bytes(raw[:2]+segment(0xe1,XMP+XML)+raw[2:])
    window.add([folder])
    window.camera_patch.setChecked(False)
    assert not window.history.isChecked()
    window.patch_button.click()
    finish(window)
    assert (window.output/photo.name).read_bytes()==photo.read_bytes()
    window.history.setChecked(True)
    window.patch_button.click()
    finish(window)
    copy=(window.output/photo.name).read_bytes()
    assert b"Photoshop" not in copy and b"fixture-camera" in copy
    assert window.counts["corrected"]==1


def test_copy_failure_keeps_partial_files_out_of_customer_folder(window,tmp_path,monkeypatch):
    import photometaclean.gui.jobs as jobs
    real = jobs.patch_file
    def simulate(path, *args, **kwargs):
        if path.name == "unreadable.jpg":
            raise OSError("Simulated read failure")
        return real(path, *args, **kwargs)
    monkeypatch.setattr(jobs, "patch_file", simulate)
    folder = tmp_path/"Auftrag"
    folder.mkdir()
    source(folder/"one.jpg")
    source(folder/"unreadable.jpg")
    window.add([folder])
    window.patch_button.click()
    finish(window)
    assert not (folder/"Patch").exists()
    assert (folder/"Patch-Protokolle/Unvollstaendig/one.jpg").is_file()
    assert window.counts["errors"] == 1 and window.counts["unchanged"] == 1
    assert window.logs_button.isEnabled() and not window.open_button.isEnabled()


@pytest.mark.parametrize("de", [True,False])
def test_narrow_desktop_layout_and_language(window,de):
    from PySide6.QtWidgets import QApplication
    window.de = de
    window.settings.setValue("language", "de" if de else "en")
    other = type(window)(window.settings)
    other.resize(760,640)
    other.show()
    QApplication.processEvents()
    other.more_tools.setChecked(True)
    QApplication.processEvents()
    assert other.centralWidget().horizontalScrollBar().maximum() == 0
    assert other.centralWidget().widget().width() == other.centralWidget().viewport().width()
    for button in (other.full_folder, other.select_button, other.apply_button):
        assert button.width() >= button.minimumSizeHint().width()
    assert other.full_folder.isChecked()
    assert other.full_folder.text() == ("Sorglos · kompletter Kundenordner" if de else "Complete customer folder")
    assert other.history.isVisible() and other.mode.isVisible() and other.select_button.isVisible()
    other.close()


def test_localized_copy_reason_and_full_cell_tooltip(window):
    reason = "Existing provenance protects this history / Herkunftsnachweis schützt diesen Verlauf"
    for de, phrase in ((True, "Ein Herkunftsnachweis"), (False, "A provenance record")):
        window.de = de
        window.counts = dict(found=1, done=0, size=0, unchanged=0, skipped=0, errors=0, flagged=0, corrected=0)
        window.add_row(dict(task="patch", path="example.jpg", relative="example.jpg", data={
            "copy_only":True, "reason":reason, "analysis":{}}))
        item = window.table.item(window.table.rowCount()-1, 7)
        assert item.text().startswith(phrase) and item.toolTip() == item.text()
        assert " / " not in item.text()


@pytest.mark.parametrize("de", [True, False])
def test_hdr_and_iptc_skip_reasons_in_selected_language(window, de):
    from photometaclean.core.edit import IPTC_DIGEST_WARNING
    window.de = de
    hdr = window.copy_reason("Unverified mobile HDR index or gain-map description")
    iptc = window.copy_reason("Metadatenprüfung offen / Metadata warning: " + IPTC_DIGEST_WARNING)
    assert ("HDR-Aufbau" if de else "HDR layout") in hdr
    assert ("im Original" if de else "original") in iptc
