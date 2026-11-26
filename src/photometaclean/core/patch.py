"""Apply a previously approved correction or produce an exact, checked copy."""
from .batch import analyze_one
from .copy import copy_exact
from .options import edit_options, has_generated_label
from pathlib import Path

from photometaclean.formats.history import HISTORY, HISTORY_RASTERS, JPEG_EXTENSIONS, history_fields, signed_edit
from photometaclean.formats.share import AI_TYPES, EXPORT, ai_indicators
from photometaclean.metadata.classification import MAIN_SOURCE_FIELD, source_term
from photometaclean.formats.xmp import FieldReviewRequired, SOURCE_TYPE, PRIVACY_FIELDS
from photometaclean.formats.recipes import RECIPE_FIELDS
from photometaclean.metadata.generators import has_generator_record
from .review import FIELDS, apply_reviewed, review


def patch_file(source, target, rules, mirror, approved=None, camera_confirmation="", *, logs=None):
    analysis = analyze_one(source)
    fields, reason = edit_options(source, analysis)
    digest = analysis.get("sha256")
    record = None
    retained = {}
    if approved is not None:
        if fields and digest and digest == approved["source_sha256"]:
            record = approved
        else:
            reason = "approval_changed" if fields else reason
    elif (camera_confirmation and Path(source).suffix.lower() in JPEG_EXTENSIONS
          and ((EXPORT in rules and ai_indicators(analysis))
               or (HISTORY in rules and (history_fields(analysis.get("metadata", {})) or
                                          (EXPORT in rules and signed_edit(analysis)))))
          and not analysis.get("provenance_references", {}).get("sidecars")):
        try:
            selected = set(rules) & (PRIVACY_FIELDS | {EXPORT, HISTORY, "JPEG:Comment"})
            record = review(source, dict.fromkeys(selected), camera_confirmation)
            reason = "available"
        except ValueError as exc:
            reason = str(exc)
    else:
        changes = dict.fromkeys(sorted(set(fields) & set(rules) & (set(FIELDS[:-1]) | RECIPE_FIELDS)))
        if (HISTORY in rules and camera_confirmation and Path(source).suffix.lower() in HISTORY_RASTERS
                and history_fields(analysis.get("metadata", {})) and reason not in {"provenance", "unverified"}):
            changes[HISTORY] = None
            reason = "available"
        declarations = analysis.get("classification", {}).get("declarations", ())
        source_export = (HISTORY in rules and EXPORT in rules and camera_confirmation and
                         len(declarations) == 1 and MAIN_SOURCE_FIELD.fullmatch(declarations[0]["field"])
                         and source_term(declarations[0]["value"], allow_short=True) in AI_TYPES)
        if SOURCE_TYPE in fields and source_export:
            changes[SOURCE_TYPE] = None
            reason = "available"
        elif SOURCE_TYPE in fields and has_generated_label(analysis):
            if has_generator_record(analysis):
                reason = "generator_review"
            elif camera_confirmation and (EXPORT in rules or HISTORY not in rules):
                changes[SOURCE_TYPE] = None
            else:
                reason = "unconfirmed"
        elif SOURCE_TYPE in fields:
            reason = "other_source" if not changes else "available"
        elif fields and not changes:
            reason = "no_rule"
        while changes:
            try:
                record = review(source, changes, camera_confirmation if SOURCE_TYPE in changes or HISTORY in changes else "")
                break
            except FieldReviewRequired as exc:
                if exc.key not in changes:
                    raise
                retained[exc.key] = str(exc)
                reason = str(exc)
                del changes[exc.key]
            except ValueError as exc:
                reason = str(exc)
                break
    if record is not None:
        if record["source_sha256"] != digest:
            raise ValueError("Source changed after analysis")
        try:
            result = apply_reviewed(record, target, logs=logs)
        except ValueError as exc:
            if not {EXPORT, HISTORY}.intersection(record["changes"]) or Path(target).exists():
                raise
            reason = str(exc)
            result = copy_exact(source, target, digest) if mirror else {"omitted": True}
    elif mirror:
        result = copy_exact(source, target, digest)
    else:
        result = {"omitted": True}
    if logs and "destination" in result:
        result["destination"] = str(logs.delivered(Path(target)))
    if retained:
        result["retained_fields"] = retained
    result["analysis"] = analysis
    result["reason"] = reason
    return result
