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
