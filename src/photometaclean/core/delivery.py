"""Keep customer copies and private records on separate paths, including interrupted runs."""
from dataclasses import dataclass
from itertools import count
import os
from pathlib import Path
import re
from tempfile import mkdtemp

from .publish import rename_new
from .review import destination_path

MARKER = ".photometaclean-logs-v1"
SUFFIX = "-Protokolle"
OLD_REPORT = re.compile(r"PhotoMetaClean-[a-z0-9_]{8}\.jsonl", re.I)


def private_folder(path):
    marker = path / MARKER
    return "-protokolle" in path.name.casefold() and not linked(path) and not linked(marker) and marker.is_file()


def old_journal(name):
    return name.endswith(".photometaclean.jsonl") or (name.startswith(".photometaclean-retry-") and name.endswith(".jsonl"))


def old_report(path):
    if not OLD_REPORT.fullmatch(path.name) or path.is_symlink() or not path.is_file():
        return False
    with path.open("rb") as stream:
        header = stream.read(8192)
    return not header or (header.startswith(b'{"file":') and b'"stage": "patch"' in header)


def linked(path):
    return path.is_symlink() or getattr(os.path, "isjunction", lambda _: False)(path)


@dataclass(frozen=True)
class ExportLogs:
    output: Path
    work: Path
    directory: Path

    def journal_for(self, target):
        relative = target.absolute().relative_to(self.work)
        parent = self.directory / "Dateien" / relative.parent
        if parent.resolve() != parent:
            raise ValueError("Linked journal directory / Verknüpfter Protokollordner")
        parent.mkdir(mode=0o700, parents=True, exist_ok=True)
        return parent / (relative.name + ".photometaclean.jsonl")

    def delivered(self, target):
        return self.output / target.absolute().relative_to(self.work)

    def finish(self):
        rename_new(self.work, self.output)


def edit_logs(output):
    """One private sibling for a manually reviewed batch or a direct core call."""
    output = Path(output).absolute()
    destination_path(output / ".photometaclean-output-check")
    if output.parent == output or output.resolve() != output:
        raise ValueError("Choose a separate output folder / Separaten Ausgabeordner wählen")
    output.parent.mkdir(parents=True, exist_ok=True)
    logs = Path(mkdtemp(prefix=output.name + SUFFIX + "-", dir=output.parent))
    (logs / MARKER).touch(exist_ok=False)
    return ExportLogs(output, output, logs)


def new_delivery(parent):
    parent = Path(parent).absolute()
    destination_path(parent / "Patch" / ".photometaclean-output-check")
    if parent.resolve() != parent or any(private_folder(p) for p in (parent, *parent.parents)):
        raise ValueError("Choose a regular output folder / Regulären Ausgabeordner wählen")
    parent.mkdir(parents=True, exist_ok=True)
    for number in count(1):
        output = parent / ("Patch" if number == 1 else f"Patch-{number}")
        if os.path.lexists(output):
            continue
        logs = parent / (output.name + SUFFIX)
        try:
            logs.mkdir(mode=0o700)
        except FileExistsError:
            continue
        (logs / MARKER).touch(exist_ok=False)
        work = logs / "Unvollstaendig"
        work.mkdir(mode=0o700)
        return ExportLogs(output, work, logs)
