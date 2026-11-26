"""Lossless JPEG metadata export. Every replaced byte range can be restored from the private audit."""
import hashlib
import re
import struct
from collections import defaultdict
from xml.parsers import expat

from .history import CRS, XAP, history_field
from .jpeg import MPF, image_streams
from .xmp import ATTRIBUTE, TAG_END, RDF, NAMESPACES, NS_SEPARATOR, _names, _top_rdf, locations
from photometaclean.metadata.classification import source_term
from photometaclean.metadata.editing import APPLIED, SETTINGS, IPTC
from photometaclean.metadata.generators import generator_signal

EXPORT = "JPEG:AIRecords"
XMP = b"http://ns.adobe.com/xap/1.0/\0"
EXT = b"http://ns.adobe.com/xmp/extension/\0"
AI_TYPES = {"trainedAlgorithmicMedia", "compositeWithTrainedAlgorithmicMedia", "compositeSynthetic",
            "algorithmicallyEnhanced"}
LIMIT = 8 * 1024**2


def ai_indicators(analysis):
    return (any(source_term(d["value"], allow_short=True) in AI_TYPES
                for d in analysis.get("classification", {}).get("declarations", ()))
            or any(s["operation"] not in {"lens_blur", "depth", "retouch", "masks"}
                   for s in analysis.get("editing_signals", ())))


def xml_field(tag, value):
    uri, name = tag
    if uri == NAMESPACES["iptcExt"]:
        if name in IPTC or (name == "DigitalSourceType" and source_term(value.strip(), allow_short=True) in AI_TYPES):
            return name
    if uri == NAMESPACES["aux"] and (name in SETTINGS or name in APPLIED):
        return name
    if uri == XAP and name == "CreatorTool" and generator_signal("XMP-xmp:CreatorTool", value):
        return name
    if (uri, name) in {("http://purl.org/dc/terms/", "provenance"),
                       ("http://ns.adobe.com/xap/1.0/mm/", "Manifest")} and "jumbf" in value.lower():
        return "C2PA reference"
    return None


def packet_spans(packet, *, clean_ai, history):
    if len(packet) > LIMIT or b"<!DOCTYPE" in packet or b"\0" in packet:
        raise ValueError("Unsupported XMP size or encoding")
    packet.decode("utf8")
    parser = expat.ParserCreate("UTF-8", namespace_separator=NS_SEPARATOR)
    parser.namespace_prefixes = True
    stack, spans = [], []

    def selected(tag, value, owner):
        # Top-level RDF properties belong to the image. Nested, unrelated structures
        # such as a camera Look can use the very same property names.
        if history and len(stack) >= owner and stack[-owner]["tag"] == (RDF, "RDF"):
            subject = stack[1-owner]
            if subject["own"] and _top_rdf([node["tag"] for node in stack[:len(stack)-owner+1]]):
                if field := history_field(tag, value):
                    return field
        return xml_field(tag, value) if clean_ai else None

    def firefly():
        for i, entry in enumerate(stack):
            if entry["tag"] == (CRS, "RetouchAreas"):
                target = entry
                if (len(stack) > i+2 and stack[i+1]["tag"] in {(RDF,"Seq"),(RDF,"Bag")}
                        and stack[i+2]["tag"] == (RDF,"li")):
                    target = stack[i+2]
                target["remove"] = "Firefly RetouchAreas"
                break

    def start(name, attrs):
        if len(stack) > 128:
            raise ValueError("XMP nesting exceeds limit")
        tag, spelling = _names(name)
        begin = parser.CurrentByteIndex
        attr_map = {_names(n)[1]: (_names(n)[0], v) for n, v in attrs.items()}
        entry = dict(tag=tag, begin=begin, text=[], remove=None, resource="",
                     own=not any(key == (RDF, "about") and value for key, value in attr_map.values()))
        stack.append(entry)
        cursor = begin + 1 + len(spelling.encode())
        while match := ATTRIBUTE.match(packet, cursor):
            cursor = match.end()
            attr = attr_map.get(match[1].decode())
            if not attr:
                continue
            key, value = attr
            if key == (RDF, "resource"):
                entry["resource"] = value
            if clean_ai and key == (CRS, "fill_method") and value.strip().casefold() == "firefly":
                firefly()
            label = selected(key, value, 2)
            if label:
                spans.append((match.start(), cursor, label))
        closing = TAG_END.match(packet, cursor)
        if not closing:
            raise ValueError("Unsupported XMP tag")
        entry.update(empty=bool(closing[1]), content=closing.end())

    def chars(value):
        if stack:
            stack[-1]["text"].append(value)

    def end(name):
        entry = stack[-1]
        value = entry["resource"] or "".join(entry["text"])
        if clean_ai and entry["tag"] == (CRS, "fill_method") and value.strip().casefold() == "firefly":
            firefly()
        label = entry["remove"] or selected(entry["tag"], value, 3)
        if label:
            stop = entry["content"] if entry["empty"] else packet.index(b">", parser.CurrentByteIndex) + 1
            spans.append((entry["begin"], stop, label))
        stack.pop()

    parser.StartElementHandler, parser.EndElementHandler, parser.CharacterDataHandler = start, end, chars
    try:
        parser.Parse(packet, True)
    except expat.ExpatError as exc:
        raise ValueError("Malformed XMP packet") from exc
    # A removed structured property already covers all its child nodes and attributes.
    covered = []
    for span in sorted(spans, key=lambda item: (item[0], -item[1])):
        if not covered or span[0] >= covered[-1][1]:
            covered.append(span)
    return covered


def clean_packet(packet, *, clean_ai=True, history=False):
    spans = packet_spans(packet, clean_ai=clean_ai, history=history)
    out = bytearray(packet)
    for start, end, _ in spans:
        out[start:end] = b" " * (end-start)
    return bytes(out), sorted({name for _, _, name in spans})


def credential_segments(data, parts):
    """Only detach complete C2PA JUMBF superboxes, preserving independent APP11 records."""
    groups = defaultdict(list)
    for s in parts:
        if s.marker == 0xeb:
            raw = data[s.payload:s.end]
            if not raw.startswith(b"JP") or len(raw) < 16:
                raise ValueError("Unknown JPEG APP11 structure")
            instance, seq = struct.unpack(">HI", raw[2:8])
            groups[instance].append((seq, s))
    selected = []
    for fragments in groups.values():
        fragments.sort(key=lambda item: item[0])
        first = fragments[0][1]
        header = data[first.payload+8:first.payload+16]
        if header[4:] != b"jumb":
            raise ValueError("Unknown JPEG JUMBF box")
        if list(range(1,len(fragments)+1)) != [seq for seq,_ in fragments]:
            raise ValueError("Incomplete JUMBF fragment sequence")
        length = int.from_bytes(header[:4], "big")
        if any(data[s.payload+8:s.payload+16] != header for _,s in fragments):
            raise ValueError("Mismatched JUMBF header")
        if length != 8 + sum(s.end-s.payload-16 for _,s in fragments):
            raise ValueError("Incomplete JUMBF superbox")
        desc = data[first.payload+16:first.end]
        if (desc[4:8] == b"jumd" and desc[8:24] == bytes.fromhex("6332706100110010800000aa00389b71")
                and len(desc) >= 30 and desc[24] & 2 and desc[25:30] == b"c2pa\0"):
            selected.extend(s for _,s in fragments)
        else:
            raise ValueError("Additional JUMBF data requires review")
    return selected


def jpeg_changes(data, privacy=(), *, clean_exif=False, clean_ai=True, history=False, has_provenance=False):
    """Return independent (start, end, replacement, description) metadata ranges."""
    primary, *aux = image_streams(data, allow_provenance=clean_ai)
    if primary.fixed_layout and has_provenance:
        raise ValueError("Mobile HDR provenance requires review")
    if aux and any(s.marker == 0xeb for s in aux[0].parts):
        raise ValueError("Auxiliary image has independent provenance")
    changes = []
    removed = credential_segments(data, primary.parts)
    for seg in removed:
        changes.append((seg.start, seg.end, b"", "C2PA / JUMBF"))
    if removed and aux:
        mp = next(s for s in primary.parts if s.marker == 0xe2 and data.startswith(MPF, s.payload))
        origin = mp.payload + len(MPF)
        order = "big" if data[origin:origin+2] == b"MM" else "little"
        deleted = sum(s.end - s.start for s in removed)
        shift = sum(s.end - s.start for s in removed if s.end <= origin)
        for pos, number in [(origin+54, primary.end-deleted), (origin+74, aux[0].start-deleted-origin+shift)]:
            value = number.to_bytes(4, order)
            if data[pos:pos+4] != value:
                changes.append((pos, pos+4, value, "MPF image position"))
    masters, extended = [], defaultdict(list)
    for s in primary.parts:
        if s.marker == 0xfe and "JPEG:Comment" in privacy and data[s.payload:s.end].strip(b" "):
            changes.append((s.payload, s.end, b" "*(s.end-s.payload), "JPEG:Comment"))
        if s.marker != 0xe1:
            continue
        if clean_exif and data.startswith(b"Exif\0\0", s.payload, s.end):
            from .share_exif import generator_fields
            changes.extend(generator_fields(data, s.payload+6, s.end, clean_ai=clean_ai, history=history))
        elif data.startswith(XMP,s.payload,s.end):
            masters.append(s)
        elif data.startswith(EXT,s.payload,s.end):
            pos=s.payload+len(EXT)
            guid=data[pos:pos+32]
            if pos+40 > s.end or not re.fullmatch(b"[0-9A-Fa-f]{32}",guid):
                raise ValueError("Invalid Extended XMP header")
            length, offset=struct.unpack_from(">II",data,pos+32)
            extended[guid].append((offset,length,pos,s.end))
    if len(masters)>1 or len(extended)>1 or (extended and not masters):
        raise ValueError("Ambiguous primary XMP packets")
    if masters:
        main = masters[0]
        pos=main.payload+len(XMP)
        raw=data[pos:main.end]
        if primary.fixed_layout:
            locations(raw, ())
        updated, names=clean_packet(raw, clean_ai=clean_ai, history=history)
        selected = set(privacy) - {"JPEG:Comment"}
        if selected:
            buf = bytearray(updated)
            for key, a, b, _ in locations(updated, selected):
                buf[a:b] = b" " * (b-a)
                names.append(key)
            updated = bytes(buf)
        for guid, parts in extended.items():
            packet=bytearray()
            ordered=sorted(parts)
            total=ordered[0][1]
            if total>LIMIT:
                raise ValueError("Extended XMP exceeds limit")
            for offset,length,header,end in ordered:
                if len(packet)!=offset or length!=total or end-header-40>total-offset:
                    raise ValueError("Overlapping or missing Extended XMP fragment")
                packet.extend(data[header+40:end])
            if (len(packet)!=total or hashlib.md5(packet, usedforsecurity=False).hexdigest().upper().encode()!=guid.upper()
                    or raw.upper().count(guid.upper())!=1):
                raise ValueError("Extended XMP reference or digest mismatch")
            if primary.fixed_layout:
                locations(bytes(packet), ())
            cleaned, fields=clean_packet(bytes(packet), clean_ai=clean_ai, history=history)
            if fields:
                new_guid=hashlib.md5(cleaned, usedforsecurity=False).hexdigest().upper().encode()
                updated=re.sub(re.escape(guid),new_guid,updated,flags=re.I)
                names.append("Extended XMP reference")
                for offset,length,header,end in ordered:
                    changes.append((header,end,new_guid+data[header+32:header+40]+cleaned[offset:offset+end-header-40],
                                    "Extended XMP · "+", ".join(fields)))
        if updated!=raw:
            changes.append((pos, main.end, updated,"XMP · "+", ".join(names)))
    if primary.fixed_layout and any(end - start != len(value) or end > primary.end
                                    for start, end, value, _ in changes):
        raise ValueError("Mobile HDR export requires fixed image positions")
    return sorted(changes)


def recovery_data(data, patches):
    """Retain verbatim original metadata, including signatures, in the private journal."""
    import base64
    if sum(end-start for start,end,_,_ in patches) > 16 * 1024**2:
        raise ValueError("Metadata exceeds the local recovery record limit")
    shift = 0
    records = []
    for start, end, replacement, label in patches:
        records.append(dict(output_offset=start+shift, output_length=len(replacement), kind=label,
                            original_base64=base64.b64encode(data[start:end]).decode("ascii")))
        shift += len(replacement) - (end-start)
    return records


def recovered_digest(output, records):
    """Verify that the archived metadata plus this copy reproduce the exact source."""
    import base64
    digest = hashlib.sha256()
    cursor = 0
    view = memoryview(output)
    for entry in records:
        start = entry["output_offset"]
        stop = start + entry["output_length"]
        if not cursor <= start <= stop <= len(view):
            raise ValueError("Invalid metadata recovery range")
        digest.update(view[cursor:start])
        digest.update(base64.b64decode(entry["original_base64"], validate=True))
        cursor = stop
    digest.update(view[cursor:])
    return digest.hexdigest()
