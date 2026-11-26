"""Interpret IPTC declarations while keeping the creation history unresolved."""
import re

# Public IPTC vocabulary. Digital capture alone says nothing about later edits.
SOURCE_TYPES = {
    "trainedAlgorithmicMedia": "generated with a trained model",
    "compositeWithTrainedAlgorithmicMedia": "contains generative edits or elements",
    "algorithmicallyEnhanced": "algorithmically enhanced; AI involvement unspecified",
    "humanEdits": "human editing with non-generative tools",
    "minorHumanEdits": "minor human edits (retired IPTC term)",
    "computationalCapture": "computational camera capture; subsequent edits unspecified",
    "compositeSynthetic": "composite including generative AI elements",
    "digitalCapture": "digital capture; subsequent edits unspecified",
}

MAIN_SOURCE_FIELD = re.compile(r"XMP-iptcExt:(?:Main:(?:Copy\d+:)?|PrimaryXMP:)?DigitalSourceType")
IPTC_URI = re.compile(r"https?://cv\.iptc\.org/newscodes/digitalsourcetype/([A-Za-z]+)")


def source_term(value, *, allow_short=False):
    if not isinstance(value, str):
        return ""
    if allow_short and value in SOURCE_TYPES:
        return value
    match = IPTC_URI.fullmatch(value)
    return match[1] if match else ""


def interpret(metadata, manifest=None):
    metadata = dict(metadata)
    if manifest:
        active = manifest.get("manifests", {}).get(manifest.get("active_manifest"), {})
        for index, assertion in enumerate(active.get("assertions", [])):
            if not assertion.get("label", "").startswith("c2pa.actions"):
                continue
            for number, action in enumerate(assertion.get("data", {}).get("actions", [])):
                if isinstance(action, dict) and action.get("digitalSourceType"):
                    key = f"C2PA:assertion[{index}]:action[{number}]:digitalSourceType"
                    metadata[key] = action["digitalSourceType"]
    declarations = []
    types = set()
    for key, value in metadata.items():
        if key.rsplit(":", 1)[-1].casefold() != "digitalsourcetype":
            continue
        for item in value if isinstance(value, list) else [value]:
            term = source_term(item, allow_short=bool(MAIN_SOURCE_FIELD.fullmatch(key)))
            declarations.append({"field": key, "value": item,
                                 "meaning": SOURCE_TYPES.get(term, "unrecognized declaration")})
            types.add(term if term in SOURCE_TYPES else str(item))
    return {"declarations": declarations, "creation_history": "unverified",
            "review_multiple_declarations": len(types) > 1}
