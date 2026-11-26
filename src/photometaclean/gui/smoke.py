"""Exercise one folder patch in the actual packaged GUI using temporary inputs."""
from pathlib import Path
from tempfile import TemporaryDirectory

from PIL import Image, PngImagePlugin
from PySide6.QtCore import QSettings, QTimer

from photometaclean.core.edit import XMP
from .app import Window


def exercise_patch(app):
    with TemporaryDirectory() as tmp:
        root = Path(tmp).resolve()
        settings = QSettings(str(root / "test.ini"), QSettings.Format.IniFormat)
        win = Window(settings)
        win.show()
        if win.windowIcon().pixmap(96, 96).isNull():
            raise RuntimeError("Missing application icon")
        folder = root / "inputs"
        folder.mkdir()
        picture = folder / "Nacht ä 東京.jpg"
        Image.new("RGB", (13, 7), "purple").save(picture, comment=b"synthetic comment")
        packet = XMP + (
            b'<r:RDF xmlns:r="http://www.w3.org/1999/02/22-rdf-syntax-ns#"><r:Description '
            b'xmlns:c="http://ns.adobe.com/camera-raw-settings/1.0/" c:Exposure2012="+0.66" '
            b'xmlns:i="http://iptc.org/std/Iptc4xmpExt/2008-02-29/" '
            b'i:DigitalSourceType="http://cv.iptc.org/newscodes/digitalsourcetype/trainedAlgorithmicMedia"/></r:RDF>')
        data = picture.read_bytes()
        picture.write_bytes(data[:2] + b"\xff\xe1" + (len(packet)+2).to_bytes(2, "big") + packet + data[2:])
        before = picture.read_bytes()
        settings_png = folder / "tool.png"
        pnginfo = PngImagePlugin.PngInfo()
        pnginfo.add_text("parameters", "Steps: 20, Sampler: Euler, CFG scale: 7, Seed: 1", zip=True)
        Image.new("RGB", (8, 8)).save(settings_png, pnginfo=pnginfo)
        note = folder / "note.txt"
        note.write_bytes(b"synthetic sidecar")
        if not win.full_folder.isChecked():
            raise RuntimeError("Complete customer folder must be the default")
        if win.history.isChecked():
            raise RuntimeError("Editing history must be opt-in")
        win.history.setChecked(True)
        win.add([folder])
        win.patch_button.click()
        win.job.finished.connect(app.quit)
        QTimer.singleShot(90000, app.quit)
        app.exec()
        win.job.wait()
        app.processEvents()
        output = folder / "Patch"
        if (set(p.name for p in output.iterdir()) != {picture.name, settings_png.name, note.name}
                or win.patch_report.parent != folder / "Patch-Protokolle"
                or len(list(win.patch_report.parent.rglob("*.photometaclean.jsonl"))) != 2
                or win.counts["corrected"] != 2 or win.counts["unchanged"] != 1
                or b"parameters" in (output / settings_png.name).read_bytes()
                or picture.read_bytes() != before or b"trainedAlgorithmicMedia" in (output / picture.name).read_bytes()
                or b"+0.66" in (output / picture.name).read_bytes()
                or b"synthetic comment" not in (output / picture.name).read_bytes()
                or (output / note.name).read_bytes() != note.read_bytes()):
            raise RuntimeError("Packaged folder patch failed")
        win.close()
    return 0
