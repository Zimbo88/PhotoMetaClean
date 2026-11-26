"""Desktop batch scheduling. Core processing stays independent of Qt."""
from concurrent.futures import ProcessPoolExecutor, ThreadPoolExecutor
from pathlib import Path
from threading import Event
import multiprocessing

from PySide6.QtCore import QThread, Signal

from photometaclean.core.batch import discover, analyze_one, differences, scheduled, large_file
from photometaclean.core.patch import patch_file
from photometaclean.core.copy import mirror_directories
from photometaclean.core.review import apply_reviewed, review


def walk(inputs, recursive, output, stop, keep_aliases=False, *, delivery=False):
    seen = set()
    for root in inputs:
        if stop.is_set():
            return
        for path in discover(root, recursive, output, keep_aliases=keep_aliases, delivery=delivery):
            if stop.is_set():
                return
            stat = path.stat()
            identity = (stat.st_dev, stat.st_ino) if stat.st_ino else path.resolve()
            if keep_aliases or identity not in seen:
                seen.add(identity)
                yield path, path.relative_to(root) if root.is_dir() else Path(root.name)


def compare(left, right):
    from photometaclean.metadata.analysis import analyze

    before, after = (analyze(p)["metadata"] for p in (left, right))
    return {"before": before, "after": after, "differences": differences(before, after)}


class Batch(QThread):
    total = Signal(int)
    current = Signal(str)
    result = Signal(object)
    failed = Signal(str)

    def __init__(self, task, inputs, recursive, output, workers, changes=None,
                 evidence="", approved=None, candidates=None, mirror=False, exclude=None, logs=None):
        super().__init__()
        self.task, self.inputs, self.recursive = task, inputs, recursive
        self.output, self.workers = output, workers
        self.logs = logs
        self.exclude = exclude or output
        self.changes, self.evidence = changes, evidence
        self.approved = approved or {}
        self.candidates = candidates
        self.mirror = mirror
        self.stop = Event()

    def process(self, path, relative):
        from photometaclean.metadata.analysis import analyze

        if self.task == "compare":
            right = self.inputs[1]
            if right.is_dir():
                right = right / relative
            left_ok = path.is_file() and not path.is_symlink()
            right_ok = right.is_file() and not right.is_symlink()
            if self.inputs[0].is_dir():
                left_ok = left_ok and path.resolve() == self.inputs[0].resolve() / relative
                right_ok = right_ok and right.resolve() == self.inputs[1].resolve() / relative
            if not left_ok or not right_ok:
                return {"unmatched": True, "left_exists": left_ok, "right_exists": right_ok}
            return compare(path, right)
        if self.task in ("patch", "apply"):
            destination = self.output / relative
            if destination.parent.resolve() != self.output.absolute() / relative.parent:
                raise ValueError("Ausgabepfad enthält eine Verknüpfung / Linked output directory")
            if self.task == "patch":
                return patch_file(path, destination, self.changes, self.mirror,
                                  self.approved.get(path), self.evidence, logs=self.logs)
            record = self.approved[path]
            return apply_reviewed(record, destination, logs=self.logs)
        if self.task == "review":
            changes = self.changes
            if self.candidates is not None:
                _, fields, reason, digest = self.candidates[path]
                changes = {key: None for key in fields if key in self.changes}
                if not changes:
                    raise ValueError(reason if reason != "available" else "absent")
            return review(path, changes, self.evidence)
        return analyze(path)

    def run(self):
        try:
            if self.task in ("apply", "patch") and self.logs is None:
                from photometaclean.core.delivery import edit_logs
                self.logs = edit_logs(self.output)
            if self.mirror and self.task in ("apply", "patch") and not self.stop.is_set():
                mirror_directories(self.inputs[0], self.output, exclude=self.exclude, stopped=self.stop.is_set)
            if self.task == "apply":
                files = [(p, rel) for p, (_, rel) in self.approved.items()]
                self.approved = {p: pair[0] for p, pair in self.approved.items()}
            elif self.candidates is not None:
                files = [(p, row[0]) for p, row in self.candidates.items()]
            elif self.task == "compare":
                left, right = self.inputs
                if left.is_dir() != right.is_dir():
                    raise ValueError("Gleichartige Quellen wählen / Select two files or two folders")
                files = list(walk([left], self.recursive, self.output, self.stop))
                if right.is_dir():
                    known = {rel for _, rel in files}
                    files.extend((left / rel, rel) for _, rel in
                                 walk([right], self.recursive, self.output, self.stop) if rel not in known)
            else:
                files = list(walk(self.inputs, self.recursive, self.exclude, self.stop, keep_aliases=self.mirror, delivery=self.task == "patch"))
            self.total.emit(len(files))
            items = iter(files)
            executor = (ProcessPoolExecutor(self.workers, mp_context=multiprocessing.get_context("spawn"))
                        if self.task == "analyze" and self.workers > 1 else ThreadPoolExecutor(self.workers))
            with executor as pool:
                def submit(item):
                    path, rel = item
                    self.current.emit(str(path))
                    if self.task == "analyze":
                        return pool.submit(analyze_one, path)
                    return pool.submit(self.process, path, rel)

                def large(item):
                    path, rel = item
                    if self.task == "compare":
                        right = self.inputs[1]
                        if large_file(right / rel if right.is_dir() else right):
                            return True
                    return large_file(path)

                for item, future in scheduled(items, submit, self.workers, large, self.stop.is_set):
                    self.deliver(future, item)
        except Exception as exc:
            self.failed.emit(str(exc))

    def deliver(self, future, item):
        path, rel = item
        row = dict(path=str(path), relative=str(rel), task=self.task)
        try:
            row["size"] = path.stat().st_size if path.is_file() else 0
            row["data"] = future.result()
        except Exception as exc:
            row["error"] = str(exc)
            row["skipped"] = isinstance(exc, (ValueError, FileExistsError)) and self.task in ("review", "apply")
        self.result.emit(row)
