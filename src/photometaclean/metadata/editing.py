"""Identify exact metadata properties. Preserve the scope of each declaration."""
from .generators import LABELS as GENERATOR_LABELS, generator_signal

APPLIED = {
    "EnhanceDenoiseAlreadyApplied": "denoise",
    "EnhanceDetailsAlreadyApplied": "raw_details",
    "EnhanceSuperResolutionAlreadyApplied": "super_resolution",
}
SETTINGS = {
    "EnhanceDenoiseVersion": "denoise", "EnhanceDenoiseLumaAmount": "denoise",
    "EnhanceDetailsVersion": "raw_details", "EnhanceSuperResolutionVersion": "super_resolution",
    "EnhanceSuperResolutionScale": "super_resolution",
}
CAMERA_RAW = {"MaskGroupBasedCorrections": "masks", "LensBlur": "lens_blur",
              "RetouchAreas": "retouch", "RetouchInfo": "retouch", "DepthMapInfo": "depth"}
IPTC = {"AIPromptInformation": "prompt", "AIPromptWriterName": "prompt_writer",
        "AISystemUsed": "ai_system", "AISystemVersionUsed": "ai_version"}
LABELS = {
    **GENERATOR_LABELS,
    "firefly_fill": ("Firefly fill in a retouch area", "Firefly-Füllung in einem Retuschierbereich"),
    "denoise": ("Denoise", "Entrauschen"), "raw_details": ("Raw Details", "Raw-Details"),
    "super_resolution": ("Super Resolution", "Super-Auflösung"), "masks": ("Masking", "Maskierung"),
    "lens_blur": ("Lens blur", "Objektivunschärfe"), "retouch": ("Retouching", "Retusche"),
    "depth": ("Depth map", "Tiefenkarte"), "prompt": ("AI prompt", "KI-Prompt"),
    "prompt_writer": ("Prompt author", "Promptautor"), "ai_system": ("AI system", "KI-System"),
    "ai_version": ("AI system version", "Version des KI-Systems"),
}
STATES = {"recorded": ("recorded in the file", "in der Datei gespeichert"),
          "applied": ("reported as applied", "als angewendet gemeldet"),
          "off": ("reported as off", "als inaktiv gemeldet"),
          "setting": ("setting recorded", "Einstellung gespeichert"),
          "declared": ("field populated", "Feld ausgefüllt")}


def editing_signals(metadata):
    signals = []
    for field, value in metadata.items():
        if value is None or value == "" or value == [] or value == {}:
            continue
        group, *_, name = field.split(":") if ":" in field else ("", field)
        tool = None
        state = "setting"
        if group == "XMP-aux":
            tool = APPLIED.get(name) or SETTINGS.get(name)
            if name in APPLIED:
                flag = str(value).casefold().strip()
                if flag in {"true", "1"}:
                    state = "applied"
                elif flag in {"false", "0"}:
                    state = "off"
        elif group == "XMP-crs":
            tool = CAMERA_RAW.get(name)
            if name == "RetouchAreas" and isinstance(value, list):
                areas = sum(isinstance(area, dict) and area.get("Fill_method") == "firefly" for area in value)
                if areas:
                    signals.append(dict(field=field, operation="firefly_fill", state="declared", areas=areas))
        elif group == "XMP-iptcExt":
            tool = IPTC.get(name)
            state = "declared"
        if tool:
            signals.append(dict(field=field, operation=tool, state=state))
        else:
            signal = generator_signal(field, value)
            if signal:
                signals.append(signal)
    return signals
