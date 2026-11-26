"""Discover regular files without crossing links and limit outstanding analyses."""
from concurrent.futures import FIRST_COMPLETED, ProcessPoolExecutor, wait
import multiprocessing
import os
from pathlib import Path


def walk_tree(root, recursive, output, *, delivery=False):
    from .delivery import SUFFIX, linked, old_journal, old_report, private_folder

    excluded = Path(output).resolve() if output else None
    if excluded and root.resolve().is_relative_to(excluded):
        raise ValueError("Output contains the input directory")
    if delivery and any(private_folder(p) for p in (root, *root.parents)):
        raise ValueError("Private Protokolle / Private log directory")

    def fail(error):
        raise error

    for parent, directories, files in os.walk(root, onerror=fail):
        base = Path(parent)
        if delivery and base != root and any(old_report(base / name) for name in files):
            directories.clear()
            continue
        ignored = set()
        if delivery:
            for name in directories:
                if private_folder(base / name):
                    ignored.add(name)
                    if name.endswith(SUFFIX):
                        ignored.add(name[:-len(SUFFIX)])
        directories[:] = sorted(d for d in directories if recursive and d not in ignored
                                and not linked(base / d) and (base / d).resolve() != excluded)
        if delivery:
            files = [n for n in files if not old_journal(n) and not old_report(base / n)]
        yield base, sorted(files)


def discover(root, recursive=True, output=None, *, keep_aliases=False, delivery=False):
    from .delivery import linked

    root = Path(root)
    if linked(root):
        raise ValueError(f"Symbolic link: {root}")
    if root.is_file():
        yield root
        return
    if not root.is_dir():
        raise FileNotFoundError(root)
    seen = set()
    for base, files in walk_tree(root, recursive, output, delivery=delivery):
        for name in files:
            path = base / name
            if linked(path) or not path.is_file():
                continue
            stat = path.stat()
            identity = (stat.st_dev, stat.st_ino) if stat.st_ino else path.resolve()
            if keep_aliases or identity not in seen:
                seen.add(identity)
                yield path


def analyze_one(path):
    from photometaclean.metadata.analysis import analyze
    try:
        return analyze(path)
    except Exception as exc:
        from photometaclean.metadata.classification import interpret
        return {"path": str(path), "error": str(exc), "classification": interpret({})}


def large_file(path):
    try:
        return path.stat().st_size >= 64 * 1024**2
    except OSError:
        # Let the worker produce the per-file error.
        return False


def scheduled(items, submit, workers, is_large, stopped=lambda: False):
    """Run large inputs individually. Keep only the current queue and one lookahead."""
    items = iter(items)
    current = next(items, None)
    pending = {}
    large_running = False
    while current is not None or pending:
        while current is not None and len(pending) < workers and not large_running and not stopped():
            large = is_large(current)
            if large and pending:
                break
            pending[submit(current)] = current
            large_running = large
            current = next(items, None)
        if stopped():
            current = None
            for job in list(pending):
                if job.cancel():
                    del pending[job]
        if not pending:
            break
        done, _ = wait(pending, return_when=FIRST_COMPLETED)
        for job in done:
            yield pending.pop(job), job
        if not pending:
            large_running = False


def analyses(paths, workers):
    if not 1 <= workers <= 64:
        raise ValueError("Choose 1–64 workers")
    if workers == 1:
        for path in paths:
            yield path, analyze_one(path)
        return
    with ProcessPoolExecutor(workers, mp_context=multiprocessing.get_context("spawn")) as pool:
        for path, job in scheduled(paths, lambda p: pool.submit(analyze_one, p), workers, large_file):
            yield path, job.result()


def differences(before, after):
    return {
        "added": {k: after[k] for k in sorted(after.keys() - before.keys())},
        "removed": {k: before[k] for k in sorted(before.keys() - after.keys())},
        "changed": {k: [before[k], after[k]] for k in sorted(before.keys() & after.keys())
                    if before[k] != after[k]},
    }
