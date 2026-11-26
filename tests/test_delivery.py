import json
from pathlib import Path

from PIL import Image
import pytest

from photometaclean.cli.app import main
from photometaclean.core.batch import discover
from photometaclean.core.delivery import new_delivery
from photometaclean.formats.share import XMP


def test_complete_tree_retries_and_private_logs(tmp_path, capsys):
    source = tmp_path / "Fotos"
    nested = source / "Serie ä"
    nested.mkdir(parents=True)
    (source/"leer").mkdir()
    # This similarly named folder belongs to the photographer.
    (source/"Patch").mkdir()
    (source/"Patch"/"Lizenz.txt").write_text("customer note")
    photo = nested/"foto.jpg"
    Image.new("RGB", (8,10), "teal").save(photo)
    original = photo.read_bytes()
    packet = XMP + (b'<r:RDF xmlns:r="http://www.w3.org/1999/02/22-rdf-syntax-ns#">'
                    b'<r:Description xmlns:c="http://ns.adobe.com/camera-raw-settings/1.0/" '
                    b'c:Exposure2012="+0.4"/></r:RDF>')
    photo.write_bytes(original[:2]+b"\xff\xe1"+(len(packet)+2).to_bytes(2,"big")+packet+original[2:])
    marked = photo.read_bytes()
    (source/"foto.jpg").write_bytes(original)
    (nested/"info.jsonl").write_text("customer file\n")
    (source/"old.jpg.photometaclean.jsonl").write_text("private journal")
    (source/"PhotoMetaClean-abc12345.jsonl").write_text('{"file":"old.jpg","stage": "patch"}\n')
    for n in (2,3):
        assert main(["patch",str(source),"--history"]) == 0
        result = json.loads(capsys.readouterr().out)
        output, logs = Path(result["customer_folder"]), Path(result["logs"])
        assert (result["corrected"], result["unchanged"], result["errors"]) == (1,3,0)
        assert output == source/f"Patch-{n}" and logs == source/f"Patch-{n}-Protokolle"
        assert (output/"leer").is_dir()
        assert {p.relative_to(output) for p in output.rglob("*") if p.is_file()} == {
            Path("foto.jpg"),Path("Serie ä/foto.jpg"),Path("Serie ä/info.jsonl"),Path("Patch/Lizenz.txt")}
        assert (output/"foto.jpg").read_bytes() == original and photo.read_bytes() == marked
        assert b"+0.4" not in (output/"Serie ä/foto.jpg").read_bytes()
        assert len((logs/"Durchlauf.jsonl").read_text().splitlines()) == 4
        journal = logs/"Dateien/Serie ä/foto.jpg.photometaclean.jsonl"
        approved = json.loads(journal.read_text(encoding="utf-8").splitlines()[0])
        assert Path(approved["destination"]) == output/"Serie ä/foto.jpg"
    assert main(["patch",str(source),"--history","--only-changed"]) == 0
    result = json.loads(capsys.readouterr().out)
    assert result["omitted"] == 3 and result["unchanged"] == 0
    assert [p.name for p in Path(result["customer_folder"]).rglob("*") if p.is_file()] == ["foto.jpg"]


def test_two_runs_and_existing_empty_target(tmp_path):
    a, b = new_delivery(tmp_path), new_delivery(tmp_path)
    assert a.output != b.output
    (a.work/"private.txt").touch()
    assert not list(discover(tmp_path, delivery=True))
    a.output.mkdir()
    with pytest.raises(OSError):
        a.finish()
    assert not list(a.output.iterdir()) and (a.work/"private.txt").exists()
    b.finish()
    assert b.output.is_dir() and not b.work.exists()


def test_output_location_inside_existing_client_subfolder(tmp_path, capsys):
    source = tmp_path / "photos"
    parent = source / "delivery"
    parent.mkdir(parents=True)
    note = parent / "client.txt"
    note.write_bytes(b"client instructions")
    assert main(["patch", str(source), "--output", str(parent)]) == 0
    result = json.loads(capsys.readouterr().out)
    assert result["unchanged"] == 1
    output = Path(result["customer_folder"])
    assert (output / "delivery" / note.name).read_bytes() == note.read_bytes()
    assert list((output / "delivery").iterdir()) == [output / "delivery" / note.name]
