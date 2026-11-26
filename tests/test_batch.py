import os
import pytest
from photometaclean.cli.app import report
from photometaclean.core.batch import discover, differences


def test_tree(tmp_path):
    folder = tmp_path / "A ä" / ("a" * 75) / ("b" * 75)
    folder.mkdir(parents=True)
    photo = folder / "bild"
    photo.touch()
    (tmp_path / "bild").touch()
    output = tmp_path / "out"
    output.mkdir()
    (output / "previous").touch()
    assert set(discover(tmp_path, output=output)) == {photo, tmp_path / "bild"}
    assert list(discover(tmp_path, recursive=False)) == [tmp_path / "bild"]


def test_links(tmp_path):
    original = tmp_path / "a"
    original.touch()
    try:
        (tmp_path / "loop").symlink_to(tmp_path, target_is_directory=True)
        os.link(original, tmp_path / "b")
    except OSError:
        pytest.skip("Link privilege unavailable")
    assert list(discover(tmp_path)) == [original]


def test_cancelled_report(tmp_path):
    target = tmp_path / "report"
    with pytest.raises(KeyboardInterrupt), report(target) as stream:
        stream.write("partial")
        raise KeyboardInterrupt
    assert not list(tmp_path.iterdir())


def test_report_no_overwrite(tmp_path):
    target = tmp_path / "report"
    target.write_text("keep")
    with pytest.raises(FileExistsError), report(target) as stream:
        stream.write("other")
    assert target.read_text() == "keep"


def test_diff():
    assert differences({"x": 1, "gone": 0}, {"x": 2, "new": None}) == {
        "added": {"new": None}, "removed": {"gone": 0}, "changed": {"x": [1, 2]}}


def test_large_work_excludes_other_jobs():
    from concurrent.futures import Future
    from photometaclean.core.batch import scheduled

    active = set()
    items = list(range(5))
    def submit(item):
        if item == 2 or 2 in active:
            assert not active
        active.add(item)
        job = Future()
        job.set_result(item)
        return job
    processed = []
    for item, job in scheduled(items, submit, 4, lambda i: i == 2):
        assert item == job.result()
        active.remove(item)
        processed.append(item)
    assert sorted(processed) == items


def test_verified_copy_rechecks_source_and_refuses_overwrite(tmp_path):
    from hashlib import sha256
    from photometaclean.core.copy import copy_exact

    source = tmp_path / "source.bin"
    target = tmp_path / "out" / source.name
    source.write_bytes(b"synthetic content")
    with pytest.raises(ValueError):
        copy_exact(source, target, expected="obsolete")
    assert not target.exists()
    digest = sha256(source.read_bytes()).hexdigest()
    result = copy_exact(source, target, expected=digest)
    assert result["source_sha256"] == result["output_sha256"] == digest
    with pytest.raises(FileExistsError):
        copy_exact(source, target)
    assert target.read_bytes() == source.read_bytes()


def test_exclusive_publication_without_hardlinks(tmp_path, monkeypatch):
    import errno
    import os
    from photometaclean.core.publish import publish_new

    def reject_link(*args):
        raise OSError(errno.EPERM, "Volume has no hard links")

    monkeypatch.setattr(os, "link", reject_link)
    temp, target = tmp_path / "temp", tmp_path / "target"
    temp.write_bytes(b"first")
    publish_new(temp, target)
    temp.write_bytes(b"second")
    with pytest.raises(FileExistsError):
        publish_new(temp, target)
    assert target.read_bytes() == b"first"


@pytest.mark.parametrize("kind", ["copy", "edit", "report"])
def test_linked_parent_rejected_for_file_outputs(tmp_path, kind):
    from PIL import Image
    from photometaclean.core.copy import copy_exact
    from photometaclean.core.edit import apply
    original = tmp_path/"original.jpg"
    Image.new("RGB", (4, 6)).save(original, comment=b"camera")
    contents = original.read_bytes()
    other = tmp_path/"another project"
    other.mkdir()
    sentinel = other/"keep.txt"
    sentinel.write_bytes(b"previous work")
    link = tmp_path/"shortcut"
    try:
        link.symlink_to(other, target_is_directory=True)
    except OSError:
        pytest.skip("Directory links unavailable")
    target = link/"new file.jpg"
    with pytest.raises(ValueError, match="Linked output"):
        if kind == "copy":
            copy_exact(original, target)
        elif kind == "edit":
            apply(original, target, {"JPEG:Comment": None})
        else:
            with report(target):
                pass
    assert list(other.iterdir()) == [sentinel] and sentinel.read_bytes() == b"previous work"
    assert original.read_bytes() == contents


def test_two_simultaneous_copies_never_replace_each_other(tmp_path):
    from concurrent.futures import ThreadPoolExecutor
    from threading import Barrier
    from photometaclean.core.copy import copy_exact
    sync = Barrier(2)
    dest = tmp_path/"output.jpg"
    sources = [tmp_path/"first.jpg", tmp_path/"second.jpg"]
    for src in sources:
        src.write_bytes(src.name.encode())
    def write(src):
        sync.wait(timeout=5)
        try:
            copy_exact(src, dest)
        except FileExistsError:
            return None
        return src
    with ThreadPoolExecutor(2) as pool:
        winners = [p for p in pool.map(write, sources) if p]
    assert len(winners) == 1 and dest.read_bytes() == winners[0].name.encode()
    assert all(src.read_bytes() == src.name.encode() for src in sources)


def test_windows_regular_paths_and_reserved_output_names():
    from pathlib import PureWindowsPath
    from photometaclean.core.review import _reserved_windows_path
    assert _reserved_windows_path(PureWindowsPath("C:/Photos/CON"))
    assert _reserved_windows_path(PureWindowsPath("C:/Photos/test."))
    assert not _reserved_windows_path(PureWindowsPath("C:/Photos/long folder/image.jpg"))
    assert not _reserved_windows_path(PureWindowsPath("//?/C:/Photos/long folder/image.jpg"))
    assert not _reserved_windows_path(PureWindowsPath("//?/UNC/server/share/photos/image.jpg"))


def test_report_can_use_a_regular_parent_reference(tmp_path):
    folder = tmp_path/"work"
    folder.mkdir()
    with report(folder/".."/"report.jsonl") as stream:
        stream.write("completed\n")
    assert (tmp_path/"report.jsonl").read_bytes().splitlines() == [b"completed"]
