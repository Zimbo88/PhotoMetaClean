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


def test_full_delivery_checks_capacity_before_copying(tmp_path, capsys, monkeypatch):
    from types import SimpleNamespace
    source = tmp_path / "photos"
    source.mkdir()
    note = source / "notes.txt"
    note.write_bytes(b"original customer notes")
    monkeypatch.setattr("photometaclean.core.copy.shutil.disk_usage", lambda _: SimpleNamespace(free=2))
    assert main(["patch", str(source)]) == 1
    assert "Zu wenig Platz" in capsys.readouterr().err
    assert not (source/"Patch").exists()
    assert not list((source/"Patch-Protokolle"/"Unvollstaendig").rglob("*.txt"))
    assert note.read_bytes() == b"original customer notes"
    assert main(["patch", str(source), "--only-changed"]) == 0


def test_patch_source_cannot_be_the_system_root(tmp_path):
    import os
    from photometaclean.core.delivery import patch_source
    system = Path(os.environ.get("SystemRoot") or Path.home()).anchor if os.name == "nt" else "/"
    with pytest.raises(ValueError, match="Fotoordner"):
        patch_source(Path(system))
    assert patch_source(tmp_path) == tmp_path.resolve()


def test_existing_patch_directory_link_is_treated_as_occupied(tmp_path, capsys):
    source, other = tmp_path/"in", tmp_path/"other"
    source.mkdir()
    other.mkdir()
    (other/"client.txt").write_bytes(b"existing")
    try:
        (source/"Patch").symlink_to(other, target_is_directory=True)
    except OSError:
        pytest.skip("Directory links unavailable")
    (source/"input.txt").write_bytes(b"photo notes")
    assert main(["patch", str(source)]) == 0
    result = json.loads(capsys.readouterr().out)
    assert Path(result["customer_folder"]) == source/"Patch-2"
    assert list(other.iterdir()) == [other/"client.txt"]
    assert (other/"client.txt").read_bytes() == b"existing"
    assert (source/"Patch-2"/"input.txt").read_bytes() == b"photo notes"


def test_out_of_space_during_copy_stops_cli_batch(tmp_path, monkeypatch, capsys):
    import errno
    source = tmp_path/"photos"
    source.mkdir()
    for n in ("a", "b", "c"):
        (source/n).write_bytes(n.encode())
    visited = []
    def full(path, *args, **kwargs):
        visited.append(path.name)
        raise OSError(errno.ENOSPC, "test volume full")
    monkeypatch.setattr("photometaclean.core.patch.patch_file", full)
    assert main(["patch", str(source)]) == 1
    result = json.loads(capsys.readouterr().out)
    assert visited == ["a"] and result["errors"] == 1 and result["customer_folder"] is None
    assert not (source/"Patch").exists()
    assert all((source/n).read_bytes() == n.encode() for n in ("a", "b", "c"))
