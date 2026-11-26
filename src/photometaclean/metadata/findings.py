"""Read-only presentation of an existing analysis. No file or network access."""
from .editing import LABELS, STATES, editing_signals
from .classification import MAIN_SOURCE_FIELD, source_term
from .generators import LABELS as GENERATOR_LABELS
from collections import Counter
from dataclasses import dataclass
import re


# Only interpret the canonical IPTC identifiers. Unknown values stay visible.
SOURCE_TYPES = {
    "trainedAlgorithmicMedia": ("Generation with a trained model reported", "Erzeugung mit trainiertem Modell gemeldet"),
    "compositeWithTrainedAlgorithmicMedia": ("Generative editing reported", "Generative Bearbeitung gemeldet"),
    "compositeSynthetic": ("Generative elements reported", "Generative Bildelemente gemeldet"),
    "algorithmicallyEnhanced": ("Algorithmic enhancement reported (AI use unspecified)",
                                "Algorithmische Verbesserung gemeldet (KI-Einsatz offen)"),
    "computationalCapture": ("Computational camera capture reported", "Mehrbild-Kameraaufnahme gemeldet"),
    "digitalCapture": ("Digital capture reported (later edits unspecified)",
                       "Digitale Aufnahme gemeldet (spätere Bearbeitung offen)"),
    "humanEdits": ("Human editing with non-generative tools reported",
                   "Menschliche Bearbeitung mit nichtgenerativen Werkzeugen gemeldet"),
    "minorHumanEdits": ("Minor human edits reported", "Kleine manuelle Retuschen gemeldet"),
}
EDIT_ACTIONS = {"c2pa.drawing", "c2pa.edited", "c2pa.placed"}
ACTION_NAMES = {
    "c2pa.opened": ("Opened an existing asset", "Vorhandene Datei geöffnet"),
    "c2pa.created": ("Created an asset", "Datei erstellt"),
    "c2pa.drawing": ("Applied a drawing operation", "Zeichenvorgang angewendet"),
    "c2pa.edited": ("Edited the asset", "Datei bearbeitet"),
    "c2pa.removed": ("Removed a component", "Bestandteil entfernt"),
    "c2pa.cropped": ("Cropped the image", "Bild zugeschnitten"),
    "c2pa.transcoded": ("Transcoded the asset", "Datei transkodiert"),
    "c2pa.repackaged": ("Repackaged the asset", "Datei neu verpackt"),
    "c2pa.placed": ("Inserted an element", "Element eingefügt"),
}
ACTION_LABEL = re.compile(r"c2pa\.actions(?:\.v2)?(?:__\d+)?")
ABSENT = {"no embedded jpeg jumbf detected", "manifest not found"}
BINDINGS = {"assertion.dataHash.match", "assertion.bmffHash.match", "assertion.boxesHash.match",
            "assertion.collectionHash.match"}


def mapping(value):
    return value if isinstance(value, dict) else {}


def entries(value):
    return value if isinstance(value, list) else []


def literal(value):
    """Keep each metadata string on its own line of evidence, including in a terminal."""
    if not isinstance(value, str):
        return ""
    return "".join(c if c.isprintable() else ascii(c)[1:-1] for c in value)


@dataclass(frozen=True)
class Findings:
    headline: str
    verification: str
    text: str


def actions(data):
    """Resolve wildcard and action-specific template defaults, then explicit fields."""
    defaults = {}
    for item in entries(data.get("templates")):
        template = mapping(item)
        name = literal(template.get("action"))
        fields, params = defaults.setdefault(name, ({}, {}))
        fields.update(template)
        params.update(mapping(template.get("templateParameters")))
        params.update(mapping(template.get("parameters")))
    agents = entries(data.get("softwareAgents"))
    for item in entries(data.get("actions")):
        action = mapping(item)
        name = literal(action.get("action"))
        if not name:
            continue
        fields, params = {}, {}
        for key in ("*", name):
            if key in defaults:
                fields.update(defaults[key][0])
                params.update(defaults[key][1])
        fields.update(action)
        params.update(mapping(action.get("parameters")))
        agent = fields.get("softwareAgent")
        index = fields.get("softwareAgentIndex")
        if "softwareAgentIndex" in action or agent is None:
            if type(index) is int and 0 <= index < len(agents):
                agent = agents[index]
        if isinstance(agent, dict):
            agent = agent.get("name")
        yield name, literal(fields.get("digitalSourceType")), literal(agent), params, literal(fields.get("description"))


def verification_details(analysis, manifest, active, location, sidecars, pointers, t):
    checks = mapping(mapping(manifest.get("validation_results")).get("activeManifest"))

    def codes(group):
        return {literal(mapping(entry).get("code")) for entry in entries(checks.get(group))} - {""}

    success = codes("success")
    failures = codes("failure").union(filter(None, map(literal, entries(analysis.get("validation_failures")))))
    state = literal(analysis.get("signature", manifest.get("validation_state"))).lower()
    invalid = state == "invalid" or bool(failures - {"signingCredential.untrusted"})
    absent = state in ABSENT and not manifest
    if analysis.get("error"):
        verification = t("Analysis failed", "Analyse fehlgeschlagen")
    elif invalid:
        verification = t("C2PA validation failed", "C2PA-Prüfung fehlgeschlagen")
    elif analysis.get("validation_error") or state == "verification unavailable":
        verification = t("Verification unavailable", "Prüfung nicht verfügbar")
    elif absent:
        verification = t("No embedded manifest detected", "Kein eingebettetes Manifest erkannt")
    elif not active:
        verification = t("Provenance unchecked", "Herkunft ungeprüft")
    elif "claimSignature.validated" in success:
        verification = t("Claim signature verified", "Manifest-Signatur bestätigt")
    else:
        verification = t("Signature unconfirmed", "Signatur unbestätigt")

    # A Valid SDK result can coexist with an untrusted signer. Assertion URI
    # matches alone do not bind the asset bytes to the active manifest.
    if "signingCredential.untrusted" in failures:
        trust = t("No trusted certificate path in the local check", "Kein vertrauenswürdiger Zertifikatspfad in der lokalen Prüfung")
    elif active and ("signingCredential.trusted" in success or state == "trusted"):
        trust = t("Signer trusted locally", "Zertifikat lokal vertrauenswürdig")
    else:
        trust = t("Certificate trust undetermined", "Zertifikatsvertrauen offen")

    if manifest:
        verification = location + " · " + verification
    elif sidecars:
        verification = t("Sidecar referenced", "Sidecar-Hinweis") + " · " + verification
    elif pointers:
        verification = t("XMP provenance reference", "XMP-Herkunftsverweis") + " · " + verification
    lines = [t("Local verification", "Lokale Prüfung"), verification]
    if active or failures:
        if "claimSignature.validated" in success and "claimSignature.mismatch" not in failures and invalid:
            lines.append(t("Claim signature verified", "Manifest-Signatur bestätigt"))
        if any(code.endswith(".mismatch") and code.replace(".mismatch", ".match") in BINDINGS for code in failures):
            lines.append(t("Asset binding failed", "Dateibindung fehlgeschlagen"))
        elif BINDINGS & success:
            lines.append(t("Asset binding verified", "Dateibindung bestätigt"))
        else:
            lines.append(t("Asset binding unconfirmed", "Dateibindung unbestätigt"))
        lines.append(trust)
        lines.extend(sorted(failures))
    elif absent and not (sidecars or pointers):
        lines.append(t("External credentials may exist.", "Externe Herkunftsnachweise können vorliegen."))
    for key in ("error", "validation_error"):
        if analysis.get(key):
            lines.append(literal(analysis[key]))
    badge = verification + " · " + trust if active else verification
    return lines, badge, invalid, absent


def reported_evidence(analysis, active, t):
    def source_meaning(value, action=None, *, allow_short=False):
        term = source_term(value, allow_short=allow_short)
        if term == "trainedAlgorithmicMedia" and action and action != "c2pa.created":
            return t("Model-generated media reported in this step", "Modellerzeugtes Material in diesem Schritt gemeldet")
        if term in SOURCE_TYPES:
            return t(*SOURCE_TYPES[term])
        return t("Unrecognized source type", "Unbekannter Quellentyp")

    summaries = []
    evidence = Counter()
    for assertion in entries(active.get("assertions")):
        label = literal(mapping(assertion).get("label"))
        if label == "com.adobe.app-enforced":
            evidence[t("Adobe records enforced attribution (com.adobe.app-enforced)",
                       "Adobe meldet eine erzwungene Herkunftsangabe (com.adobe.app-enforced)")] += 1
        if not ACTION_LABEL.fullmatch(label):
            continue
        for name, source, agent, params, detail in actions(mapping(assertion.get("data"))):
            description = t(*ACTION_NAMES[name]) if name in ACTION_NAMES else ""
            fields = [description, name, agent, detail, literal(params.get("com.adobe.acr.value"))]
            if source:
                meaning = source_meaning(source, name)
                fields += [source, meaning]
                summaries.append(meaning)
            elif name in EDIT_ACTIONS and params.get("com.adobe.acr.value") == "Healing changed, Uses GenAI":
                meaning = t(*SOURCE_TYPES["compositeWithTrainedAlgorithmicMedia"])
                fields.append(meaning)
                summaries.append(meaning)
            if params.get("com.adobe.appEnforced") is True:
                fields.append("com.adobe.appEnforced")
            evidence[" · ".join(filter(None, fields))] += 1

    metadata_lines = []
    declarations = entries(mapping(analysis.get("classification")).get("declarations"))
    xmp_source = False
    for item in declarations:
        field = literal(mapping(item).get("field"))
        if field.startswith("C2PA:"):
            continue  # Flattened copies lack the action and validation context.
        value = literal(mapping(item).get("value"))
        line = f"{field} · {value}"
        if MAIN_SOURCE_FIELD.fullmatch(field):
            xmp_source = True
            meaning = source_meaning(value, allow_short=True)
            line += " · " + meaning
            summaries.append(meaning)
        metadata_lines.append(line)

    return list(dict.fromkeys(summaries)), evidence, metadata_lines, xmp_source


def parent_history(manifest, active_id, t):
    manifests = mapping(manifest.get("manifests"))
    current = mapping(manifests.get(active_id)) if isinstance(active_id, str) else {}
    visited = {active_id} if isinstance(active_id, str) else set()
    history = []
    while current:
        parents = [mapping(item).get("active_manifest") for item in entries(current.get("ingredients"))
                   if mapping(item).get("relationship") == "parentOf"]
        if len(parents) != 1 or not isinstance(parents[0], str) or parents[0] in visited:
            break
        parent_id = parents[0]
        visited.add(parent_id)
        current = mapping(manifests.get(parent_id))
        if current:
            _, evidence, _, _ = reported_evidence({}, current, t)
            history.append((parent_id, evidence))
    return history


def explain(analysis, lang="en"):
    """Explain active and explicitly linked parent claims with their source scope."""
    if lang not in ("en", "de"):
        raise ValueError("Choose de or en")

    def t(en, de):
        return de if lang == "de" else en

    manifest = mapping(analysis.get("manifest"))
    references = mapping(analysis.get("provenance_references"))
    sidecars = entries(references.get("sidecars"))
    pointers = mapping(references.get("xmp"))
    external_hint = bool(sidecars or pointers)
    location = {
        "sidecar": t("Sidecar manifest", "Sidecar-Manifest"),
        "embedded": t("Embedded manifest", "Eingebettetes Manifest"),
    }.get(literal(analysis.get("manifest_location")), t("Manifest (location unspecified)", "Manifest (Speicherort offen)"))
    active_id = manifest.get("active_manifest")
    active = mapping(mapping(manifest.get("manifests")).get(active_id)) if isinstance(active_id, str) else {}
    checks, badge, invalid, absent = verification_details(analysis, manifest, active, location, sidecars, pointers, t)
    summaries, evidence, metadata_lines, xmp_source = reported_evidence(analysis, active, t)
    signals = analysis.get("editing_signals")
    if signals is None:
        signals = editing_signals(mapping(analysis.get("metadata")))

    if invalid:
        headline = t("Unverified claims · validation failed", "Unbestätigte Angaben · Prüfung fehlgeschlagen")
    elif analysis.get("error"):
        headline = t("No usable analysis", "Keine auswertbare Analyse")
    elif summaries:
        headline = " / ".join(summaries)
    elif active:
        headline = t("Manifest gives no recognized source classification",
                     "Manifest ohne erkannte Herkunftseinstufung")
    elif any(item["operation"] in GENERATOR_LABELS for item in signals):
        headline = t("Image tool recorded · origin undetermined", "Bildwerkzeug eingetragen · Entstehung offen")
    else:
        headline = t("Creation history undetermined", "Entstehungsgeschichte offen")

    history = parent_history(manifest, active_id, t)
    if history and not invalid and not analysis.get("error"):
        headline += t(" · Parent history available", " · Vorgeschichte dokumentiert")
    lines = [headline, "", *checks]
    if evidence:
        lines += ["", location + " · " + t("reported actions and assertions", "gemeldete Aktionen und Aussagen")]
        lines.extend(f"  {line}  (×{count})" if count > 1 else f"  {line}" for line, count in evidence.items())
    if history:
        lines += ["", t("Earlier exports · declarations in linked parent manifests",
                        "Frühere Exporte · Angaben der verknüpften Vorgängermanifeste"),
                  t("The signature and binding results above apply to the active manifest.",
                    "Die obige Signatur- und Bindungsprüfung gilt für das aktive Manifest.")]
        for parent_id, parent_evidence in reversed(history):
            lines.append("  " + literal(parent_id))
            lines.extend("    " + line for line in parent_evidence)
    if signals:
        lines += ["", t("Editing and AI fields", "Bearbeitungs- und KI-Felder")]
        for item in signals:
            detail = t(*LABELS[item["operation"]])
            if item.get("software"):
                detail += " · " + literal(item["software"])
            if item.get("areas"):
                detail += f" (×{item['areas']})"
            lines.append("  " + " · ".join((detail, t(*STATES[item["state"]]), literal(item["field"]))))
    if metadata_lines:
        lines += ["", t("File metadata declarations", "Angaben in den Dateimetadaten"), *metadata_lines]
    if external_hint:
        lines += ["", t("Sidecars and XMP references", "Sidecars und XMP-Verweise")]
        lines.extend("  Sidecar · " + literal(path) for path in sidecars)
        for key, value in pointers.items():
            values = value if isinstance(value, list) else [value]
            lines.extend(f"  XMP · {literal(key)} · {literal(str(item))}" for item in values)
        lines.append(t("A reference alone establishes neither a signature nor a link to these image bytes.",
                       "Ein Verweis allein belegt weder eine Signatur noch die Bindung an diese Bilddatei."))
    lines += ["", t("These records alone establish neither the full edit history nor a platform label.",
                    "Diese Angaben allein belegen weder die vollständige Bearbeitungshistorie noch eine Plattformkennzeichnung."),
              "", t("Correction and re-export", "Korrektur und Neu-Export")]
    if (xmp_source and absent and not external_hint and not invalid and not analysis.get("error")
            and not analysis.get("validation_error") and analysis.get("format") == "JPEG"):
        lines.append(t("For your own photo, check the original and document independent evidence of an incorrect "
                       "XMP DigitalSourceType. Use Photographer mode to preview the supported field, approve a new "
                       "copy and keep the audit. The preview checks edit eligibility.",
                       "Bei einem eigenen Foto das Original prüfen und eine falsche XMP-DigitalSourceType-Angabe "
                       "unabhängig belegen. Im Fotografenmodus das unterstützte Feld in der Vorschau prüfen, eine "
                       "neue Kopie freigeben und das Protokoll aufbewahren. Die Vorschau prüft die Bearbeitbarkeit."))
    if manifest or external_hint or invalid:
        lines.append(t("Keep the export and any sidecar together. Editing covered bytes can invalidate a signature.",
                       "Export und zugehörige Sidecar-Dateien zusammen aufbewahren. Änderungen an gebundenen Bytes können eine Signatur entwerten."))
    lines.append(t("Check the original and catalog history. Re-export a separate copy with accurate credentials, "
                   "retain any generative steps and compare both exports locally.",
                   "Original und Kataloghistorie prüfen. Eine separate Kopie mit zutreffenden Herkunftsangaben "
                   "exportieren, generative Schritte dokumentiert lassen und beide Exporte lokal vergleichen."))
    return Findings(headline, badge, "\n".join(lines))
