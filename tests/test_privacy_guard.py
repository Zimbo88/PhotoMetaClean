"""Exercise the actual hook against disposable Git indexes."""
from pathlib import Path
import shutil
import subprocess
import sys

import pytest

ROOT = Path(__file__).resolve().parents[1]


@pytest.fixture
def repo(tmp_path):
    subprocess.run(["git", "init", "-q", str(tmp_path)], check=True)
    for name in ["scripts/privacy_guard.py", ".githooks/pre-commit", ".gitignore"]:
        target = tmp_path / name
        target.parent.mkdir(exist_ok=True)
        shutil.copy2(ROOT / name, target)
    return tmp_path


def run(repo, *args):
    return subprocess.run(args, cwd=repo, capture_output=True)


def guard(repo):
    return run(repo, sys.executable, "scripts/privacy_guard.py")


@pytest.mark.parametrize("name,data", [
    ("vorm Update/file.md", b"text"), ("Nach Update/sub/file", b"text"),
    ("research/local-run/output.md", b"text"), ("research/private-dump/data", b"x"),
    ("public/a.JpEg", b"x"), ("renamed.txt", bytes.fromhex("ffd8ff")),
    ("fixture.GiF", b"x"), ("portrait.svg", b"<svg/>"), ("source.hif", b"x"),
    ("table.CSV", b"x"), ("sidecar.XMP", b"x"), ("report.md", b"GPSLatitude" + b": 12.5"),
    ("log.md", b'{"BodySerialNumber' + b'":"12345"}'), ("binary", b"a\0b"),
    ("oversize", b"a" * (4 * 1024 * 1024 + 1)),
], ids=lambda value: None if isinstance(value, str) else "payload")
def test_reject_staged_even_after_worktree_cleanup(repo, name, data):
    target = repo / name
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_bytes(data)
    assert run(repo, "git", "add", "-f", "--", name).returncode == 0
    target.write_text("clean")
    result = guard(repo)
    assert result.returncode == 1 and b"Privacy guard" in result.stderr


def test_clean_index_and_untracked_private_file(repo):
    (repo / "notes.md").write_text("Öffentliche Zusammenfassung", encoding="utf-8")
    (repo / "untracked.JPG").write_bytes(b"private")
    assert run(repo, "git", "add", ".").returncode == 0
    assert guard(repo).returncode == 0


def test_real_commit_hook(repo):
    assert run(repo, "git", "config", "core.hooksPath", ".githooks").returncode == 0
    (repo / "private.csv").write_text("secret")
    assert run(repo, "git", "add", "-f", "private.csv").returncode == 0
    result = run(repo, "git", "-c", "user.name=Test", "-c", "user.email=test@example.invalid",
                 "commit", "-m", "exercise guard")
    assert result.returncode != 0 and b"Privacy guard" in result.stderr
