"""Streaming command-line interface. Reports can contain private metadata."""
import argparse
from contextlib import contextmanager
import json
import multiprocessing
import os
from pathlib import Path
import sys
from tempfile import NamedTemporaryFile

from photometaclean.core.publish import publish_new
from photometaclean.core.batch import analyses, differences, discover
from photometaclean.metadata.findings import explain, literal


@contextmanager
def report(target):
    if target is None:
        yield sys.stdout
        return
    from photometaclean.core.review import destination_path
    target = destination_path(target)
    with NamedTemporaryFile(mode="w", encoding="utf8", dir=target.parent, delete=False) as tmp:
        name = Path(tmp.name)
    try:
        with name.open("w", encoding="utf8") as stream:
            yield stream
            stream.flush()
            os.fsync(stream.fileno())
        publish_new(name, target)
    finally:
        name.unlink(missing_ok=True)


def write(stream, result):
    print(json.dumps(result, ensure_ascii=False, default=str), file=stream, flush=True)


def compare(left, right, recursive):
    from photometaclean.metadata.analysis import analyze
    if left.is_file() and right.is_file():
        pairs = [(left, right)]
    elif left.is_dir() and right.is_dir():
        first = {p.relative_to(left) for p in discover(left, recursive)}
        second = {p.relative_to(right) for p in discover(right, recursive)}
        for name in sorted(first ^ second):
            yield {"path": str(name), "side": "before" if name in first else "after"}
        pairs = ((left / name, right / name) for name in sorted(first & second))
    else:
        raise ValueError("Select two files or two directories")
    for before, after in pairs:
        a, b = analyze(before), analyze(after)
        yield {"before": str(before), "after": str(after),
               "metadata": differences(a["metadata"], b["metadata"]),
               "structure": differences({k:v for k,v in a.items() if k != "metadata"},
                                        {k:v for k,v in b.items() if k != "metadata"})}


def parser():
    cli = argparse.ArgumentParser(description="PhotoMetaClean • lokale Bildmetadaten / local image metadata")
    sub = cli.add_subparsers(dest="command", required=True)
    scan = sub.add_parser("analyze", help="Datei oder Ordner untersuchen / inspect file or folder")
    findings = sub.add_parser("explain", help="Herkunft offline erklären / explain provenance offline")
    findings.add_argument("--lang", choices=("de", "en"), default="en", help="Ausgabesprache / output language")
    for cmd in (scan, findings):
        cmd.add_argument("source", type=Path)
        cmd.add_argument("--workers", type=int, default=min(4, os.cpu_count() or 1))
    patch = sub.add_parser("patch", help="Vollständigen Kundenordner erstellen / create a complete customer folder")
    patch.add_argument("source", type=Path)
    patch.add_argument("--output", type=Path, help="Parent for Patch and its private logs (default: source)")
    patch.add_argument("--only-changed", action="store_true", help="Only include corrected files")
    patch.add_argument("--history", action="store_true", help="Also remove supported editing history")
    patch.set_defaults(report=None)
    diff = sub.add_parser("compare", help="Dateien oder Ordner vergleichen / compare files or folders")
    diff.add_argument("before", type=Path)
    diff.add_argument("after", type=Path)
    edit = sub.add_parser("edit", help="Änderungen prüfen / preview edits")
    edit.add_argument("source", type=Path)
    edit.add_argument("--changes", required=True, help="JSON object with supported fields")
    edit.add_argument("--evidence", default="", help="Basis der Korrektur / documented basis")
    edit.add_argument("--output", type=Path, help="New output directory for approved copies")
    edit.add_argument("--apply", action="store_true", help="Approve the explicitly selected changes")
    for cmd in (scan, diff, edit, findings):
        cmd.add_argument("--flat", action="store_true")
        cmd.add_argument("--report", type=Path, help="New plain text report (default stdout)" if cmd is findings
                         else "New JSON Lines report (default stdout)")
    return cli


def patch_folder(args, stream):
    from photometaclean.core.copy import mirror_directories
    from photometaclean.core.delivery import linked, new_delivery, private_folder
    from photometaclean.core.patch import patch_file
    from photometaclean.formats.history import HISTORY
    from photometaclean.formats.recipes import RECIPE_FIELDS
    from photometaclean.formats.share import EXPORT

    if linked(args.source) or not args.source.is_dir():
        raise ValueError("Choose a regular source folder / Regulären Quellordner wählen")
    source = args.source.resolve()
    if any(private_folder(p) for p in (source, *source.parents)):
        raise ValueError("Private Protokolle / Private log directory")
    parent = args.output.absolute() if args.output else source
    logs = new_delivery(parent)
    full = not args.only_changed
    if full:
        mirror_directories(source, logs.work, exclude=logs.output)
    rules = {EXPORT, *RECIPE_FIELDS}
    if args.history:
        rules.add(HISTORY)
    corrected = unchanged = omitted = errors = 0
    with (logs.directory / "Durchlauf.jsonl").open("x", encoding="utf8") as journal:
        for path in discover(source, output=logs.output, delivery=True, keep_aliases=full):
            rel = path.relative_to(source)
            event = {"file": str(rel)}
            try:
                result = patch_file(path, logs.work / rel, rules, full,
                                    camera_confirmation="User requested folder export", logs=logs)
                corrected += int("audit" in result)
                unchanged += int(bool(result.get("copy_only")))
                omitted += int(bool(result.get("omitted")))
                event.update(reason=result["reason"], destination=result.get("destination"),
                             status="corrected" if "audit" in result else "copied" if full else "omitted")
                if check := result.get("postcheck"):
                    event.update(readback=check["state"], verification_issue=check["issue"])
            except (OSError, RuntimeError, ValueError) as exc:
                event["error"] = str(exc)
                errors += 1
            write(journal, event)
    if not errors:
        logs.finish()
    write(stream, dict(customer_folder=None if errors else str(logs.output), logs=str(logs.directory),
                       corrected=corrected, unchanged=unchanged, omitted=omitted, errors=errors))
    return int(bool(errors))


def run(args, stream):
    errors = 0
    if args.command == "patch":
        return patch_folder(args, stream)
    if args.command == "compare":
        for row in compare(args.before, args.after, not args.flat):
            write(stream, row)
    elif args.command in ("analyze", "explain"):
        for path, row in analyses(discover(args.source, not args.flat), args.workers):
            if args.command == "explain":
                print(literal(str(path)), explain(row, args.lang).text, "", sep="\n", file=stream, flush=True)
            else:
                write(stream, {"file": str(path), "analysis": row})
            errors += bool(row.get("error"))
    else:
        from photometaclean.core.review import apply_reviewed, review
        changes = json.loads(args.changes)
        if not isinstance(changes, dict) or not changes:
            raise ValueError("--changes requires a nonempty JSON object")
        if args.apply and not args.output:
            raise ValueError("--apply requires --output")
        from photometaclean.core.delivery import edit_logs
        logs = edit_logs(args.output) if args.apply else None
        for path in discover(args.source, not args.flat, args.output, delivery=args.apply):
            try:
                preview = review(path, changes, args.evidence)
                write(stream, {"file": str(path), "preview": preview})
                if args.apply:
                    rel = path.relative_to(args.source) if args.source.is_dir() else Path(path.name)
                    destination = args.output / rel
                    write(stream, {"file": str(path), "result": apply_reviewed(preview, destination, logs=logs)})
            except (ValueError, OSError, RuntimeError) as exc:
                write(stream, {"file": str(path), "error": str(exc)})
                errors += 1
    return int(bool(errors))


def main(argv=None):
    multiprocessing.freeze_support()
    args = parser().parse_args(argv)
    try:
        if args.report:
            if args.command == "edit" and args.apply and args.output and args.report.resolve().is_relative_to(args.output.resolve()):
                raise ValueError("Save the report outside the customer folder")
            for root in (getattr(args, k, None) for k in ("source", "before", "after")):
                if root and root.is_dir() and args.report.resolve().is_relative_to(root.resolve()):
                    raise ValueError("Save the report outside the input directory")
        with report(args.report) as stream:
            return run(args, stream)
    except KeyboardInterrupt:
        return 130
    except (ValueError, OSError, RuntimeError) as exc:
        print(str(exc), file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
