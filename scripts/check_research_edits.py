"""Local JPEG acceptance check / Lokaler JPEG-Abnahmetest.

Run with the project Python. Only aggregate counts are printed. Each invocation
keeps its JSONL and diagnostics in a new research/private/edit-check-* folder.
Einzelmessungen bleiben privat. Bildkopien werden nach jeder Prüfung entfernt.
"""
import argparse
from collections import Counter
from concurrent.futures import ThreadPoolExecutor
from contextlib import contextmanager
from hashlib import file_digest
import json
import os
from pathlib import Path
import re
import shutil
import sys
import tempfile
from xml.etree import ElementTree

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
from photometaclean.core.edit import apply, plan
from photometaclean.metadata.analysis import analyze

FOLDERS = ("vorm Update", "Nach Update")
# Pick a real privacy field. A research test cannot establish a false origin claim.
TARGETS = ("XMP-aux:SerialNumber", "XMP-aux:LensSerialNumber",
           "XMP-exif:GPSLatitude", "XMP-exif:GPSLongitude")
FILE_CONTEXT = {"SourceFile", *("System:Main:" + k for k in
                ("FileName", "Directory", "FileAccessDate", "FileModifyDate",
                 "FileInodeChangeDate", "FileCreateDate", "FilePermissions"))}


def require(condition, message):
    if not condition:
        raise ValueError(message)


def sha(path):
    with path.open("rb") as stream:
        return file_digest(stream, "sha256").hexdigest()


def enumerate_files(root):
    paths = []

    def walk_error(error):
        raise error

    for name in FOLDERS:
        base = root / name
        require(base.is_dir() and not base.is_symlink(), "Missing or linked corpus directory")
        for folder, dirs, files in os.walk(base, onerror=walk_error):
            parent = Path(folder)
            require(all(not (parent / d).is_symlink() for d in dirs), "Linked directory")
            for file in files:
                path = parent / file
                require(path.is_file() and not path.is_symlink(), "Nonregular corpus entry")
                paths.append(path)
    return sorted(paths)


def field_keys(metadata, field):
    group, local = field.split(":")
    return [key for key in metadata if key.startswith(group + ":Main:")
            and key.rsplit(":", 1)[-1] == local]


def metadata_check(before, after, field, record):
    # analyze extracts these records independently with read-only ExifTool.
    keys = field_keys(before, field)
    require(len(keys) == 1 and not field_keys(after, field), "Target not uniquely removed")
    record["removed_tag"] = keys[0]
    differences = sorted(k for k in before.keys() | after.keys()
                         if k not in FILE_CONTEXT and
                         (k not in before or k not in after or before[k] != after[k]))
    record["exiftool_differences"] = differences
    permitted = set(keys)
    if field.startswith("XMP-exif:GPS"):
        # These are calculated by ExifTool from stored coordinates.
        permitted.update("Composite:Main:" + k for k in
                         ("GPSPosition", field.split(":")[1] + "Ref"))
    require(set(differences) <= permitted, "Other ExifTool metadata changed")


def verify_bytes(original, output, before, change, field):
    start, size = change["offset"], change["length"]
    end = start + size
    require(change["field"] == field and change["after"] is None and size > 0,
            "Audit does not describe one removal")
    xmp = [b for b in before["blocks"] if b["kind"] == "APP1 XMP" and b["frame"] == 1
           and b["offset"] <= start < end <= b["offset"] + b["size"]]
    require(len(xmp) == 1, "Target outside primary standard XMP")
    local = re.escape(field.split(":")[1].encode())
    attr = rb"""\s+[^\s:=<>"'/]+:""" + local + rb"""\s*=\s*(?:"[^"<]*"|'[^'<]*')"""
    with original.open("rb") as src, output.open("rb") as dst:
        def compare_region(length):
            while length:
                chunk = src.read(min(1024 * 1024, length))
                require(chunk and chunk == dst.read(len(chunk)), "Protected bytes changed")
                length -= len(chunk)

        compare_region(start)
        token = src.read(size)
        require(re.fullmatch(attr, token) and dst.read(size) == b" " * size,
                "Audited bytes are not exactly the selected XMP attribute")
        compare_region(original.stat().st_size - end)
        require(not dst.read(1), "Output grew")


def verify_copy(original, destination, before, preview, audit, record):
    after = analyze(destination)
    field = record["field"]
    require(preview["changes"] == audit["changes"] and len(audit["changes"]) == 1,
            "Applied changes differ from the single-field preview")
    require(before["sha256"] == record["original_before"] == preview["source_sha256"]
            == audit["source_sha256"], "Input hashes disagree")
    record["output_sha256"] = sha(destination)
    require(after["sha256"] == record["output_sha256"] == preview["output_sha256"]
            == audit["output_sha256"] != before["sha256"], "Output hashes disagree")
    verify_bytes(original, destination, before, audit["changes"][0], field)
    # Both lists include dimensions, mode and pixel digest. frames also carries ICC.
    for key in ("frames", "codestreams"):
        require(before[key] and all(f["pixels"] for f in before[key])
                and before[key] == after[key], "Decoded " + key + " differ or are missing")
    streams = sum(b["kind"] == "SOI" for b in before["blocks"])
    require(streams == len(before["codestreams"]), "Missing decoded JPEG stream")
    metadata_check(before["metadata"], after["metadata"], field, record)
    record.update(pixel_streams=before["codestreams"], change=audit["changes"][0])
    return "verified"


def names_another_subject(path, before, field):
    """Confirm the specific RDF layout independently of the writer's XMP parser."""
    rdf = "{http://www.w3.org/1999/02/22-rdf-syntax-ns#}"
    group, local = field.split(":")
    uri = {"XMP-aux": "http://ns.adobe.com/exif/1.0/aux/",
           "XMP-exif": "http://ns.adobe.com/exif/1.0/"}[group]
    prop = "{" + uri + "}" + local
    header = b"http://ns.adobe.com/xap/1.0/\0"
    subjects = []
    with path.open("rb") as stream:
        for block in before["blocks"]:
            if block["frame"] != 1 or block["kind"] != "APP1 XMP":
                continue
            stream.seek(block["offset"])
            packet = stream.read(block["size"]).split(header, 1)[1]
            root = ElementTree.fromstring(packet)
            rdf_root = root if root.tag == rdf + "RDF" else root.find(rdf + "RDF")
            if rdf_root is not None:
                subjects.extend(el.get(rdf + "about") for el in rdf_root.findall(rdf + "Description")
                                if prop in el.attrib)
    return len(subjects) == 1 and bool(subjects[0])


def probe_refusals(source, destination, changes):
    reasons = {}
    for name, action in (("plan", lambda: plan(source, changes)),
                         ("apply", lambda: apply(source, destination, changes))):
        try:
            action()
        except ValueError as exc:
            reasons[name] = str(exc)
        else:
            reasons[name] = ""
    return reasons


def check_copy(original, scratch, record):
    before = analyze(original)
    require(before["sha256"] == record["original_before"], "Original changed since inventory")
    keys = [k for k in TARGETS if len(field_keys(before["metadata"], k)) == 1]
    side_names = {original.with_suffix(".c2pa").name.casefold(), (original.name + ".c2pa").casefold()}
    sidecars = [p for p in original.parent.iterdir() if p.name.casefold() in side_names]
    embedded = bool(before.get("manifest"))
    protected = embedded or sidecars or any(b["kind"].startswith("APP11 ") for b in before["blocks"])
    record.update(signature=before["signature"], embedded_manifest=embedded,
                  codestream_count=len(before["codestreams"]), field=next(iter(keys), None))
    if not keys and not protected:
        return "no_eligible_field"
    source = scratch / original.name
    destination = scratch / "out" / original.name
    shutil.copyfile(original, source)
    require(sha(source) == record["original_before"], "Working copy mismatch")
    for sidecar in sidecars:
        require(sidecar.is_file() and not sidecar.is_symlink(), "Linked or invalid sidecar")
        shutil.copyfile(sidecar, scratch / sidecar.name)
    # A signed original may have no eligible field. Probe both entry points with a
    # privacy key and require an explicit provenance refusal ahead of field lookup.
    changes = {record["field"] or TARGETS[0]: None}
    try:
        if protected:
            reasons = probe_refusals(source, destination, changes)
            record["refusals"] = reasons
            require(all(any(word in reason.lower() for word in ("signed", "manifest", "provenance", "c2pa"))
                        for reason in reasons.values()), "Missing explicit provenance refusal")
            require(not destination.exists(), "Protected output published")
            if embedded:
                return "signed_refused"
            return "provenance_refused"
        try:
            preview = plan(source, changes)
        except ValueError as exc:
            reason = str(exc)
            if ("unrelated XMP field" not in reason or
                    not names_another_subject(original, before, record["field"])):
                raise
            # The tag exists, but the writer protects a named RDF subject.
            try:
                apply(source, destination, changes)
            except ValueError as rejection:
                require(str(rejection) == reason and not destination.exists(),
                        "Preview and apply disagree about the protected RDF subject")
            else:
                raise ValueError("Apply accepted a refused RDF subject")
            record["refusals"] = {"plan": reason, "apply": reason}
            return "named_subject_refused"
        audit = apply(source, destination, changes, reviewed=preview)
        return verify_copy(original, destination, before, preview, audit, record)
    finally:
        require(sha(source) == record["original_before"], "Edit modified its input copy")


def examine(original, run_dir, original_hash):
    record = dict(path=str(original), original_before=original_hash)
    try:
        if original.suffix.lower() in (".jpg", ".jpeg"):
            with tempfile.TemporaryDirectory(dir=run_dir) as work:
                record["status"] = check_copy(original, Path(work), record)
        else:
            record["status"] = "analysis_only_format"
    except Exception as exc:
        record.update(status="failed", error=f"{type(exc).__name__}: {exc}")
    return record


def run(root, run_dir, workers):
    paths = enumerate_files(root)
    baseline = {p: sha(p) for p in paths}
    counts = Counter(files=len(paths), failed=0, verified=0, verified_auxiliary=0)
    with (run_dir / "details.jsonl").open("x", encoding="utf8") as log:
        with ThreadPoolExecutor(max_workers=workers) as pool:
            records = pool.map(lambda path: examine(path, run_dir, baseline[path]), paths)
            for row in records:
                log.write(json.dumps(row, ensure_ascii=True) + "\n")
                counts[row["status"]] += 1
                if row["status"] == "verified" and row["codestream_count"] > 1:
                    counts["verified_auxiliary"] += 1
        current = set(enumerate_files(root))
        for path in sorted(current | baseline.keys()):
            end_hash = sha(path) if path in current else None
            ok = path in baseline and end_hash == baseline[path]
            log.write(json.dumps(dict(path=str(path), final_sha256=end_hash, original_intact=ok)) + "\n")
            counts["originals_intact" if ok else "failed"] += 1
    if not counts["verified"]:
        counts["no_verified_edits"] = 1
    return counts


@contextmanager
def private_diagnostics(path):
    # Native decoders may write directly to stderr, bypassing redirect_stderr.
    with path.open("xb") as log:
        sys.stdout.flush()
        sys.stderr.flush()
        saved = [os.dup(fd) for fd in (1, 2)]
        try:
            for fd in (1, 2):
                os.dup2(log.fileno(), fd)
            yield
        finally:
            sys.stdout.flush()
            sys.stderr.flush()
            for fd, previous in zip((1, 2), saved):
                os.dup2(previous, fd)
                os.close(previous)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--workers", type=int, choices=range(1, 9), default=2)
    args = parser.parse_args()
    os.umask(0o077)
    counts = Counter(failed=1)
    try:
        private = ROOT / "research" / "private"
        require(private.resolve() == private, "Private report directory is linked")
        private.mkdir(mode=0o700, exist_ok=True)
        folder = Path(tempfile.mkdtemp(prefix="edit-check-", dir=private))
        with private_diagnostics(folder / "diagnostics.log"):
            try:
                counts = run(ROOT, folder, args.workers)
            except Exception as exc:
                print(f"{type(exc).__name__}: {exc}", file=sys.stderr)
    except (OSError, ValueError):
        pass
    print(json.dumps(counts, sort_keys=True))
    return int(bool(counts["failed"] or counts["no_verified_edits"]))


if __name__ == "__main__":
    raise SystemExit(main())
