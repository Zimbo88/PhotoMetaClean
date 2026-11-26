"""Build a limited, human-readable support report from a local inspection."""
from collections import Counter
import re

from photometaclean import __version__
from .classification import SOURCE_TYPES, source_term
from .editing import APPLIED, CAMERA_RAW, IPTC, LABELS, SETTINGS, STATES
from .generators import JSON_FIELDS, SOFTWARE
from .findings import entries, mapping

DISCUSSIONS = "https://github.com/Zimbo88/PhotoMetaClean/discussions"
PLATFORMS = ("Instagram", "Facebook", "X", "Threads", "TikTok", "LinkedIn", "Pinterest", "YouTube")
FORMATS = set("JPEG PNG GIF WEBP TIFF HEIC HEIF AVIF MPO DNG ARW JXL BMP JPEG2000".split())
KNOWN = (set(APPLIED) | set(SETTINGS) | set(CAMERA_RAW) | set(IPTC) | JSON_FIELDS |
         {"DigitalSourceType", "Software", "CreatorTool", "UserComment", "Parameters"})
GROUPS = {"XMP-aux", "XMP-crs", "XMP-iptcExt", "XMP-xmp", "PNG", "IFD0", "ExifIFD"}
ACTIONS = set("c2pa.opened c2pa.created c2pa.edited c2pa.placed c2pa.cropped c2pa.drawing c2pa.removed c2pa.transcoded c2pa.repackaged".split())
CODES = {"claimSignature.validated", "claimSignature.mismatch", "signingCredential.trusted",
         "signingCredential.untrusted", "assertion.dataHash.match", "assertion.dataHash.mismatch",
         "assertion.bmffHash.match", "assertion.boxesHash.match"}
# Unknown field names can be user-defined. Include only on explicit request after preview.
CANDIDATE = re.compile(r"(?:AI[A-Z]|.*(?:Firefly|Denoise|Generative|Generator|Inpaint|Diffusion|Prompt|Workflow|MaskGroup|ContentCredential|Watermark|SuperResolution))", re.I)


def snapshot(analysis):
    fmt = str(analysis.get("format", "")).upper()
    evidence = set()
    candidates = set()
    metadata = analysis.get("metadata", {})
    for field, value in metadata.items():
        parts = field.split(":")
        group, name = parts[0], parts[-1]
        if (group, name) in {("IFD0", "Software"), ("XMP-xmp", "CreatorTool"), ("PNG", "Software")} and isinstance(value, str):
            product = re.match(r"^(Adobe (?:Photoshop Lightroom Classic|Photoshop Lightroom|Lightroom Classic|Lightroom|Photoshop|Camera Raw|Firefly))\b(?:\s+(\d+(?:\.\d+){0,3}))?", value, re.I)
            if product:
                evidence.add(product[1] + (" " + product[2] if product[2] else ""))
        if (group in GROUPS and name not in KNOWN and len(parts) >= 2 and
                re.fullmatch(r"[A-Za-z][A-Za-z0-9_]{1,62}", name) and CANDIDATE.match(name)):
            candidates.add(f"{group}:{name}")
    for signal in analysis.get("editing_signals", ()):
        parts = signal["field"].split(":")
        op, state = signal.get("operation"), signal.get("state")
        if parts[0] in GROUPS and parts[-1] in KNOWN and op in LABELS and state in STATES:
            item = f"{parts[0]}:{parts[-1]} · {op} ({state})"
            product = signal.get("software")
            if product in SOFTWARE.values():
                item += " · " + product
            evidence.add(item)
    for item in analysis.get("classification", {}).get("declarations", []):
        field = item["field"]
        term = source_term(item["value"], allow_short=True)
        scope = "C2PA" if field.startswith("C2PA:") else "XMP" if field.startswith("XMP-") else "Other"
        evidence.add(f"{scope}:DigitalSourceType · " + (term if term in SOURCE_TYPES else "?"))
    manifest = mapping(analysis.get("manifest"))
    active_id = manifest.get("active_manifest")
    active = mapping(mapping(manifest.get("manifests")).get(active_id)) if isinstance(active_id, str) else {}
    for assertion in entries(active.get("assertions")):
        assertion = mapping(assertion)
        label = assertion.get("label")
        if not isinstance(label, str):
            continue
        if label == "com.adobe.app-enforced":
            evidence.add(label)
        if re.fullmatch(r"c2pa\.actions(?:\.v2)?(?:__\d+)?", label):
            evidence.add(label.split("__")[0])
            for action in entries(mapping(assertion.get("data")).get("actions")):
                if isinstance(action, dict) and isinstance(action.get("action"), str) and action["action"] in ACTIONS:
                    evidence.add(action["action"])
    checks = mapping(mapping(manifest.get("validation_results")).get("activeManifest"))
    for key in ("success", "failure"):
        for entry in entries(checks.get(key)):
            if isinstance(mapping(entry).get("code"), str) and entry["code"] in CODES:
                evidence.add(entry["code"])
    refs = analysis.get("provenance_references", {})
    containers = Counter(b["kind"] for b in analysis.get("blocks", []) if b["kind"] in {
        "APP1 XMP", "APP1 Extended XMP", "APP1 EXIF", "APP11 JUMBF fragment", "APP2 MPF", "APP2 ISO 21496-1"})
    containers = [f"{name} ×{n}" for name, n in sorted(containers.items())]
    return dict(format=fmt if fmt in FORMATS else "?", evidence=sorted(evidence), containers=containers,
                candidates=sorted(candidates)[:24], manifest=bool(manifest), sidecar=bool(refs.get("sidecars")),
                pointer=bool(refs.get("xmp")), incomplete=bool(analysis.get("error") or
                analysis.get("validation_error") or analysis.get("warnings")))


def feedback_text(record, lang, platform="", extra=False):
    def t(en, de):
        return de if lang == "de" else en

    data = record.get("data", {})
    lines = [f"PhotoMetaClean {__version__} · " + t("AI label feedback", "Rückmeldung zur KI-Kennzeichnung"),
             t("Platform", "Plattform") + " · " + (platform if platform in PLATFORMS else t("unspecified", "ohne Angabe"))]
    analysis = data.get("analysis", data if record.get("task") == "analyze" else None)
    sections = []
    if analysis is not None:
        sections.append((t("Original inspected", "Untersuchtes Original"), snapshot(analysis)))
    saved = data.get("postcheck", {}).get("feedback")
    if saved:
        sections.append((t("Saved copy inspected", "Geprüfte Ausgabekopie"), saved))
    if data.get("copy_only"):
        lines.append(t("Copy verified byte for byte against the original.", "Ausgabekopie mit dem Original byteweise abgeglichen."))
    elif data.get("omitted"):
        lines.append(t("No copy written.", "Keine Kopie geschrieben."))
    elif data.get("audit"):
        from photometaclean.core.review import FIELDS
        from photometaclean.formats.recipes import RECIPE_FIELDS
        from photometaclean.formats.history import HISTORY
        from photometaclean.formats.share import EXPORT
        fields = {item["field"] for item in data["audit"]["changes"]} & (set(FIELDS) | RECIPE_FIELDS | {EXPORT, HISTORY})
        lines.append(t("Fields removed", "Entfernte Felder") + " · " + ", ".join(sorted(fields)))
    if record.get("error") or not sections:
        lines.append(t("Inspection unavailable or incomplete.", "Untersuchung fehlt oder ist unvollständig."))
    for title, item in sections:
        lines += ["", title + " · " + item["format"]]
        for label, present in [("C2PA", item["manifest"]), ("C2PA sidecar", item["sidecar"]),
                               ("XMP provenance link", item["pointer"])]:
            if present:
                lines.append(label)
        lines += item["containers"] + item["evidence"]
        if not item["evidence"]:
            lines.append(t("No recognized AI or source fields.", "Keine bekannten KI- oder Quellenfelder gefunden."))
        if item["incomplete"]:
            lines.append(t("Inspection incomplete.", "Prüfung unvollständig."))
        if extra:
            lines.extend(item["candidates"])
    return "\n".join(lines)
