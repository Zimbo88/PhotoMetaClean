"""Bind a metadata edit to the exact bytes used for its preview."""
import json
import ntpath
import os
import tempfile
from pathlib import Path, PureWindowsPath
from copy import deepcopy

PROJECT = Path(__file__).resolve().parents[3]
FIELDS = (
    "JPEG:Comment", "PNG:Comment", "GIF:Comment", "TIFF:ImageDescription", "XMP-exif:GPSLatitude", "XMP-exif:GPSLongitude",
    "XMP-aux:SerialNumber", "XMP-aux:LensSerialNumber",
    "XMP-iptcExt:DigitalSourceType",
)


def _reserved_windows_path(target):
    drive = target.drive.casefold()
    if drive.startswith("\\\\.\\"):
        return True
    if drive.startswith("\\\\?\\"):
        volume = drive[4:]
        if not (volume.startswith("unc\\") or (len(volume) == 2 and volume[0].isalpha() and volume[1] == ":")):
            return True
    reserved = getattr(ntpath, "isreserved", lambda name: PureWindowsPath(name).is_reserved())
    for part in target.parts[1:]:
        if part == "..":
            continue
        if ":" in part or part.endswith((" ", ".")):
            return True
        if reserved(part):
            return True
    return False


def destination_path(path):
    target = Path(path).absolute()
    if os.name == "nt" and _reserved_windows_path(target):
        raise ValueError("Reservierter Windows-Pfad / Reserved Windows path")
    if target.parent.resolve() != Path(os.path.abspath(target.parent)):
        raise ValueError("Verknüpfter Ausgabeordner / Linked output directory")
    target = Path(os.path.abspath(target))
    resolved = target.resolve()
    for root in (PROJECT, Path.cwd()):
        for folder in ("vorm Update", "Nach Update", "AI KI VERSUCH"):
            if resolved.is_relative_to((root / folder).resolve()):
                raise ValueError("Geschützter Forschungsordner / Protected research directory")
    if target.exists() or target.is_symlink():
        raise FileExistsError(target)
    return target


def review(path, changes, evidence=""):
    from .edit import plan

    source = Path(path).absolute()
    preview = plan(source, changes, evidence=evidence)
    return dict(source=str(source), source_sha256=preview["source_sha256"],
                changes=deepcopy(changes), evidence=evidence, preview=preview)


def check_saved_copy(path, expected_digest):
    from .batch import analyze_one

    from photometaclean.metadata.feedback import snapshot
    from photometaclean.metadata.classification import source_term

    analysis = analyze_one(path)
    digest = analysis.get("sha256")
    references = analysis.get("provenance_references", {})
    source_types = analysis.get("classification", {}).get("declarations", [])
    signals = analysis.get("editing_signals", [])
    provenance = bool(analysis.get("manifest") or any(references.values()) or
                      any(b["kind"] == "APP11 JUMBF fragment" for b in analysis.get("blocks", [])))
    issue = analysis.get("error") or analysis.get("validation_error") or analysis.get("warnings")
    if digest != expected_digest:
        issue = "SHA-256 mismatch"
    source_hints = any(source_term(d["value"], allow_short=True) not in {
        "digitalCapture", "computationalCapture", "minorHumanEdits", "humanEdits"} for d in source_types)
    tool_hints = any(s["state"] != "off" and s["operation"] not in {"masks", "depth", "lens_blur", "retouch"}
                     for s in signals)
    if issue:
        state = "incomplete"
    elif source_hints or tool_hints or provenance:
        state = "remaining"
    else:
        state = "clear"
    return dict(state=state, sha256=digest, source_types=source_types, signals=signals,
                provenance=provenance, issue=issue or "", feedback=snapshot(analysis))


def apply_reviewed(record, destination, *, logs=None):
    from .edit import apply

    target = destination_path(destination)
    if record["source_sha256"] != record["preview"]["source_sha256"]:
        raise ValueError("Ungültige Freigabe / Invalid approval")
    from .delivery import edit_logs
    logs = logs or edit_logs(target.parent)
    target.parent.mkdir(parents=True, exist_ok=True)
    journal = logs.journal_for(target)
    public_path = str(logs.delivered(target))
    # Persist the approved hashes first, so even an interrupted run is auditable.
    try:
        descriptor = os.open(journal, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
    except FileExistsError:
        # Preserve prior attempt records, including interrupted or failed writes.
        descriptor, journal = tempfile.mkstemp(prefix=".photometaclean-retry-", suffix=".jsonl", dir=journal.parent)
    with os.fdopen(descriptor, "w", encoding="utf8") as stream:
        def log(entry):
            stream.write(json.dumps(entry, ensure_ascii=False) + "\n")
            stream.flush()
            os.fsync(stream.fileno())

        log({"state": "approved", "destination": public_path, "record": record})
        try:
            audit = apply(Path(record["source"]), target, record["changes"],
                          evidence=record["evidence"], reviewed=record["preview"])
        except (ValueError, OSError, RuntimeError) as exc:
            log({"state": "failed", "error": str(exc)})
            raise
        audit["destination"] = public_path
        postcheck = check_saved_copy(target, audit["output_sha256"])
        log({"state": "readback_incomplete" if postcheck["state"] == "incomplete" else "verified",
             "output_sha256": audit["output_sha256"], "postcheck": postcheck})
    return dict(source=record["source"], source_sha256=record["source_sha256"],
                destination=public_path, journal=str(journal), audit=audit, postcheck=postcheck)
