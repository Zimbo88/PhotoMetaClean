"""Look for embedded and adjacent provenance locally, with network fetches disabled."""
import io
import json
import os
from xml.etree import ElementTree
import stat

from photometaclean.formats.xmp import SOURCE_TYPE, locations
from .classification import interpret

MAX_MANIFEST = 16 * 1024 * 1024
SUPPORTED = {".jpg", ".jpeg", ".png", ".webp", ".tif", ".tiff", ".avif", ".heic", ".heif", ".hif", ".dng", ".gif", ".apng", ".jxl", ".svg", ".arw", ".nef"}
OFFLINE = {"core": {"allowed_network_hosts": []},
           "verify": {"remote_manifest_fetch": False, "ocsp_fetch": False}}


def _sidecar_index(directory):
    index = {}
    with os.scandir(directory) as entries:
        for entry in entries:
            key = entry.name.casefold()
            if key.endswith(".c2pa"):
                index.setdefault(key, []).append(entry.name)
    return index


def sidecars(path):
    if path.suffix.casefold() == ".c2pa":
        return []
    parent = path.parent
    index = _sidecar_index(parent)
    keys = {path.with_suffix(".c2pa").name.casefold(), (path.name + ".c2pa").casefold()}
    return sorted(parent / name for key in keys for name in index.get(key, ()))


def _manifest_bytes(path):
    info = path.lstat()
    if not stat.S_ISREG(info.st_mode) or info.st_size > MAX_MANIFEST:
        raise ValueError("Sidecar must be a regular file at most 16 MiB")
    flags = os.O_RDONLY | getattr(os, "O_NOFOLLOW", 0) | getattr(os, "O_BINARY", 0) | getattr(os, "O_NONBLOCK", 0)
    with os.fdopen(os.open(path, flags), "rb") as stream:
        if not os.path.samestat(info, os.fstat(stream.fileno())):
            raise ValueError("Sidecar changed while opening")
        data = stream.read(info.st_size + 1)
    if len(data) != info.st_size or not data:
        raise ValueError("Empty or changed sidecar")
    return data


POINTER_FIELDS = {
    "{http://purl.org/dc/terms/}provenance": "dcterms:provenance",
    "{http://ns.adobe.com/xap/1.0/mm/}Manifest": "xmpMM:Manifest",
    "{http://ns.adobe.com/xap/1.0/mm/}Provenance": "xmpMM:Provenance",
    "{http://ns.adobe.com/xap/1.0/mm/}provenance": "xmpMM:provenance",
}
RDF_RESOURCE = "{http://www.w3.org/1999/02/22-rdf-syntax-ns#}resource"


def _packet_evidence(metadata, blocks, data):
    values_from_xml = set()
    # ExifTool may retain the author's arbitrary prefix for Dublin Core Terms.
    pointers = {k: v for k, v in metadata.items() if k.casefold().startswith("xmp-dcterms:")
                and k.rsplit(":", 1)[-1].casefold() == "provenance"}
    for block in blocks:
        if block["kind"] != "APP1 XMP":
            continue
        start = block["offset"]
        packet = data[start:start + block["size"]].partition(b"http://ns.adobe.com/xap/1.0/\0")[2]
        if not packet or b"<!DOCTYPE" in packet or b"\0" in packet:
            continue
        if block["frame"] == 1 and b"DigitalSourceType" in packet:
            try:
                values_from_xml.update(old for _, _, _, old in locations(packet, [SOURCE_TYPE]))
            except ValueError:
                # Complex RDF remains available in the original ExifTool evidence.
                pass
        try:
            root = ElementTree.fromstring(packet)
        except ElementTree.ParseError:
            continue
        for node in root.iter():
            fields = [(tag, value) for tag, value in node.attrib.items() if tag in POINTER_FIELDS]
            if node.tag in POINTER_FIELDS:
                fields.append((node.tag, node.get(RDF_RESOURCE) or (node.text or "").strip()))
            for tag, value in fields:
                values = pointers.setdefault(POINTER_FIELDS[tag], [])
                if value not in values:
                    values.append(value)
    if values_from_xml:
        metadata = dict(metadata)
        reported = set()
        for field, value in list(metadata.items()):
            if field.startswith("XMP-iptcExt:") and field.endswith(":DigitalSourceType"):
                if value == "":
                    del metadata[field]
                elif isinstance(value, str):
                    reported.add(value)
        missing = sorted(values_from_xml - reported)
        if missing:
            metadata["XMP-iptcExt:PrimaryXMP:DigitalSourceType"] = missing
    return pointers, metadata


def inspect_provenance(result, path, data):
    adjacent = sidecars(path)
    metadata = result["metadata"]
    remote, classification_metadata = _packet_evidence(metadata, result["blocks"], data)
    result["classification"] = interpret(classification_metadata)
    result["provenance_references"] = {"sidecars": list(map(str, adjacent)), "xmp": remote}
    blocks = result["blocks"]
    embedded = any(b["kind"] == "APP11 JUMBF fragment" for b in blocks)
    result["signature"] = "no embedded JPEG JUMBF detected" if blocks else "unchecked"
    if not adjacent and blocks and not embedded:
        return
    image_mime = next((v for k, v in metadata.items() if k.endswith(":MIMEType")), "")
    if (not adjacent and not embedded and path.suffix.casefold() not in SUPPORTED
            and image_mime not in {"image/jpeg", "image/png", "image/gif", "image/webp", "image/avif",
                                   "image/heif", "image/heic", "image/tiff", "image/jxl", "image/svg+xml"}):
        return

    try:
        import c2pa

        with c2pa.Context.from_dict(OFFLINE) as context:
            # An explicit in-memory asset prevents implicit sidecar discovery by the SDK.
            reader = (c2pa.Reader.try_create(io.BytesIO(data), context=context)
                      if not blocks or embedded else None)
            location = "embedded"
            if reader is None and adjacent:
                if len(adjacent) != 1:
                    raise ValueError("Multiple adjacent manifests require review")
                detached = _manifest_bytes(adjacent[0])
                mime = next((v for k, v in metadata.items() if k.endswith(":MIMEType")), None)
                reader = c2pa.Reader(mime, io.BytesIO(data), manifest_data=detached, context=context)
                location = "sidecar"
            if reader is None:
                result["signature"] = "manifest not found"
                return
            with reader:
                manifest = json.loads(reader.json())
                result["manifest_location"] = location
                result["manifest"] = manifest
                result["classification"] = interpret(classification_metadata, manifest)
                checks = manifest.get("validation_results", {}).get("activeManifest", {})
                result["validation_failures"] = [entry.get("code") for entry in checks.get("failure", [])]
                result["signature"] = reader.get_validation_state() or "indeterminate"
    except Exception as exc:
        result.update(signature="verification unavailable", validation_error=str(exc))
