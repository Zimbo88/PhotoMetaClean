"""Suggest fields from an inspection. Only the byte-level review approves edits."""
from pathlib import Path

from photometaclean.formats.raster import PARSERS
from photometaclean.formats.recipes import PNG_FIELDS
from photometaclean.metadata.generators import generator_signal
from photometaclean.formats.xmp import FIELDS, SOURCE_TYPE
from photometaclean.metadata.classification import MAIN_SOURCE_FIELD, source_term


def has_generated_label(analysis):
    """Only the unambiguous IPTC declaration for a fully generated image."""
    declarations = analysis.get("classification", {}).get("declarations", [])
    if len(declarations) != 1:
        return False
    declaration = declarations[0]
    return (bool(MAIN_SOURCE_FIELD.fullmatch(declaration["field"]))
            and source_term(declaration["value"], allow_short=True) == "trainedAlgorithmicMedia")


def edit_options(path, analysis):
    refs = analysis.get("provenance_references", {})
    if (analysis.get("manifest") or any(refs.values()) or
            any(b["kind"] == "APP11 JUMBF fragment" for b in analysis.get("blocks", []))):
        return (), "provenance"
    if analysis.get("error") or analysis.get("validation_error"):
        return (), "unverified"
    if Path(path).suffix.casefold() not in {".jpg", ".jpeg", ".jfif", ".jpe", *PARSERS}:
        return (), "format"
    found = set()
    fmt = analysis.get("format", "").upper()
    native = {("JPEG", "File:Comment"): "JPEG:Comment", ("GIF", "File:Comment"): "GIF:Comment",
              ("TIFF", "IFD0:ImageDescription"): "TIFF:ImageDescription",
              ("PNG", "PNG:Comment"): "PNG:Comment"}
    for key, value in analysis.get("metadata", {}).items():
        parts = key.split(":")
        if len(parts) < 2 or not str(value).strip() or value is None:
            continue
        name = parts[0] + ":" + parts[-1]
        if name in PNG_FIELDS and generator_signal(key, value):
            found.add(name)
        if name in FIELDS:
            found.add(name)
        if (fmt, name) in native:
            found.add(native[fmt, name])
    if any(d["field"].startswith("XMP-iptcExt:") and d["field"].endswith(":DigitalSourceType")
           for d in analysis.get("classification", {}).get("declarations", [])):
        found.add(SOURCE_TYPE)
    return tuple(sorted(found)), "available" if found else "absent"
