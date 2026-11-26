"""Recognize tool-specific records without inferring the origin of the whole image."""
import json
import re


LABELS = {
    "generator_software": ("Named image tool", "Genanntes Bildwerkzeug"),
    "comfy_prompt": ("ComfyUI processing graph", "ComfyUI-Arbeitsschritte"),
    "comfy_workflow": ("ComfyUI workflow", "ComfyUI-Arbeitsablauf"),
    "invoke_metadata": ("InvokeAI image settings", "InvokeAI-Bildeinstellungen"),
    "invoke_workflow": ("InvokeAI workflow", "InvokeAI-Arbeitsablauf"),
    "sd_parameters": ("Stable Diffusion WebUI-style settings", "Einstellungen im Stable-Diffusion-WebUI-Format"),
}

SOFTWARE = {name.casefold(): name for name in (
    "Adobe Firefly", "ComfyUI", "InvokeAI", "Midjourney", "Stable Diffusion",
    "NovelAI", "Ideogram", "Leonardo.Ai", "DALL·E", "DALL-E", "OpenAI DALL-E",
)}
SOFTWARE_FIELDS = {("IFD0", "Software"), ("PNG", "Software"), ("XMP-xmp", "CreatorTool")}
JSON_FIELDS = {"Prompt", "Workflow", "Invokeai_metadata", "Invokeai_workflow"}


def has_settings_line(text):
    if not isinstance(text, str) or len(text) > 1024 * 1024:
        return False
    line = text.rstrip().rsplit("\n", 1)[-1]
    if len(line) > 16384 or not line.startswith("Steps: "):
        return False
    settings = dict(part.split(": ", 1) for part in line.split(", ") if ": " in part)
    return (settings.get("Steps", "").isdigit() and bool(settings.get("Sampler"))
            and bool(re.fullmatch(r"\d+(?:\.\d+)?", settings.get("CFG scale", "")))
            and bool(re.fullmatch(r"-?\d+", settings.get("Seed", ""))))


def workflow_record(name, value):
    if isinstance(value, str):
        if len(value) > 1024 * 1024 or not value.lstrip().startswith("{"):
            return None
        try:
            value = json.loads(value)
        except (ValueError, RecursionError):
            return None
    if not isinstance(value, dict):
        return None
    if name == "Invokeai_metadata":
        if isinstance(value.get("app_version"), str) and any(
            key in value for key in ("generation_mode", "model", "seed", "steps")
        ):
            return "invoke_metadata"
    elif name == "Prompt":
        if any(isinstance(node, dict) and isinstance(node.get("class_type"), str)
               and isinstance(node.get("inputs"), dict) for node in value.values()):
            return "comfy_prompt"
    else:
        nodes = value.get("nodes")
        if isinstance(nodes, list) and any(
            isinstance(node, dict) and "id" in node and isinstance(node.get("type"), str) for node in nodes
        ):
            if name == "Workflow" and isinstance(value.get("links"), list):
                return "comfy_workflow"
            if name == "Invokeai_workflow" and isinstance(value.get("edges"), list):
                return "invoke_workflow"
    return None


def generator_signal(field, value):
    parts = field.split(":")
    if len(parts) < 2 or (len(parts) > 2 and parts[1] != "Main"):
        return None
    group, name = parts[0], parts[-1]
    operation = None
    if (group, name) in SOFTWARE_FIELDS and isinstance(value, str) and len(value) < 128:
        product = re.sub(r"\s+v?\d+(?:\.\d+){0,3}$", "", value.strip().casefold())
        if product in SOFTWARE:
            return dict(field=field, operation="generator_software", state="recorded", software=SOFTWARE[product])
    elif (group, name) in {("PNG", "Parameters"), ("ExifIFD", "UserComment")}:
        if has_settings_line(value):
            operation = "sd_parameters"
    elif group == "PNG" and name in JSON_FIELDS:
        operation = workflow_record(name, value)
    if operation:
        return dict(field=field, operation=operation, state="recorded")
    return None


def has_generator_record(analysis):
    return any(item.get("operation") in LABELS for item in analysis.get("editing_signals", ()))
