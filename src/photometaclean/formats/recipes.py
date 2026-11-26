"""Editable processing settings. Source, creator and signed assertions are separate."""
from zlib import decompressobj, error as ZlibError

from photometaclean.metadata.generators import generator_signal

# PNG keywords are case-sensitive. ExifTool capitalizes the first letter.
PNG_KEYS = {
    b"Software": "PNG:Software",
    b"parameters": "PNG:Parameters", b"prompt": "PNG:Prompt", b"workflow": "PNG:Workflow",
    b"invokeai_metadata": "PNG:Invokeai_metadata", b"invokeai_workflow": "PNG:Invokeai_workflow",
}
XMP_SETTINGS = {
    "XMP-aux:EnhanceDenoiseVersion", "XMP-aux:EnhanceDenoiseLumaAmount",
    "XMP-aux:EnhanceDetailsVersion", "XMP-aux:EnhanceSuperResolutionVersion",
    "XMP-aux:EnhanceSuperResolutionScale", "XMP-iptcExt:AIPromptInformation",
}
PNG_FIELDS = set(PNG_KEYS.values())
RECIPE_FIELDS = PNG_FIELDS | XMP_SETTINGS
TEXT_LIMIT = 1024 * 1024


def png_recipe(kind, key, payload, *, history=False):
    """Verify the keyword and the decoded content independently of ExifTool."""
    field = PNG_KEYS.get(key)
    if field is None:
        return None
    compressed = kind == b"zTXt"
    encoding = "latin1"
    if kind == b"iTXt":
        if payload[:2] not in (b"\0\0", b"\x01\0"):
            raise ValueError("Invalid PNG international text header")
        compressed = payload[0] == 1
        parts = payload[2:].split(b"\0", 2)
        if len(parts) != 3:
            raise ValueError("Invalid PNG international text")
        payload = parts[-1]
        encoding = "utf8"
    elif compressed:
        if payload[:1] != b"\0":
            raise ValueError("Unsupported PNG text compression")
        payload = payload[1:]
    if compressed:
        decoder = decompressobj()
        try:
            payload = decoder.decompress(payload, TEXT_LIMIT + 1)
        except ZlibError as exc:
            raise ValueError("Invalid compressed PNG settings") from exc
        if not decoder.eof or decoder.unused_data or decoder.unconsumed_tail:
            raise ValueError("Oversized or malformed compressed PNG settings")
    if len(payload) > TEXT_LIMIT:
        raise ValueError("PNG settings exceed size limit")
    value = payload.decode(encoding)
    if history and key == b"Software":
        from .history import EDITOR, HISTORY
        if EDITOR.search(value):
            return HISTORY, value
    return (field, value) if generator_signal(field, value) else None
