"""Locate supported UTF-8 XMP properties without reserializing the packet."""
from dataclasses import dataclass, field
import re
from xml.parsers import expat

from .recipes import XMP_SETTINGS

RDF = "http://www.w3.org/1999/02/22-rdf-syntax-ns#"
XMP_META = "adobe:ns:meta/"
XMP_MM = "http://ns.adobe.com/xap/1.0/mm/"
NAMESPACES = {
    "exif": "http://ns.adobe.com/exif/1.0/",
    "aux": "http://ns.adobe.com/exif/1.0/aux/",
    "iptcExt": "http://iptc.org/std/Iptc4xmpExt/2008-02-29/",
}
FIELDS = {f"XMP-{group}:{name}": (NAMESPACES[group], name)
          for group, properties in (
              ("exif", ("GPSLatitude", "GPSLongitude")),
              ("aux", ("SerialNumber", "LensSerialNumber")),
              ("iptcExt", ("DigitalSourceType",)),
          ) for name in properties}
for key in XMP_SETTINGS:
    group, name = key[4:].split(":")
    FIELDS[key] = NAMESPACES[group], name
SOURCE_TYPE = "XMP-iptcExt:DigitalSourceType"
PRIVACY_FIELDS = {key for key, (uri, _) in FIELDS.items()
                  if uri in (NAMESPACES["exif"], NAMESPACES["aux"]) and key not in XMP_SETTINGS}
# dcterms:provenance may point to an external manifest with an arbitrary URL.
# Also hold packets with explicit media-management provenance/manifest fields
# for review. An ordinary xmpMM:DocumentID or History can be preserved in place.
PROVENANCE = {("http://purl.org/dc/terms/", "provenance"),
              (XMP_MM, "provenance"), (XMP_MM, "Provenance"), (XMP_MM, "Manifest"),
              ("http://www.w3.org/2000/09/xmldsig#", "Signature")}
ATTRIBUTE = re.compile(rb"""\s+([^\s=/>]+)\s*=\s*("[^"]*"|'[^']*')""")
TAG_END = re.compile(rb"\s*(/?)>")
NS_SEPARATOR = "\x1f"  # Not a legal XML character, even inside a URI.


class FieldReviewRequired(ValueError):
    """The named field cannot be cleared in this layout; the container may be valid."""
    def __init__(self, key, message):
        super().__init__(message)
        self.key = key


@dataclass
class _SimpleElement:
    key: str
    start: int
    content_start: int
    self_closing: bool
    resource: str | None
    text: list[str] = field(default_factory=list)


def _top_rdf(path):
    return (path == [(RDF, "RDF")] or
            (len(path) == 2 and path[0] in ((XMP_META, "xmpmeta"), (XMP_META, "xapmeta"))
             and path[1] == (RDF, "RDF")))


def _names(name):
    """Return the namespace-resolved name and the original qualified spelling."""
    parts = name.split(NS_SEPARATOR)
    if len(parts) == 1:
        return (None, name), name
    uri, local, *prefix = parts
    return (uri, local), f"{prefix[0]}:{local}" if prefix else local


def locations(packet, wanted):
    """Return (field, byte start, exclusive end, parsed value) for safe edits."""
    packet.decode("utf-8")
    if b"\0" in packet or b"<!DOCTYPE" in packet:
        raise ValueError("Unsupported XML encoding or DTD")
    parser = expat.ParserCreate("UTF-8", namespace_separator=NS_SEPARATOR)
    parser.namespace_prefixes = True
    targets = {FIELDS[key]: key for key in wanted}
    found = []
    seen = set()
    ancestry = []
    qualified_scope = [False]
    active = None
    own_subject = False
    top_records = 0
    used_dji_privacy = False

    def record(key, start, end, value):
        if key in seen:
            raise FieldReviewRequired(key, "Repeated XMP property requires manual review")
        if key == SOURCE_TYPE:
            if qualified_scope[-1]:
                raise FieldReviewRequired(key, "Inherited XML base or language needs manual review")
            if len(value.split()) != 1:
                raise FieldReviewRequired(key, "Expected a single DigitalSourceType value")
        seen.add(key)
        found.append((key, start, end, value))

    def start(name, attrs):
        nonlocal active, own_subject, top_records, used_dji_privacy
        if active is not None:
            raise FieldReviewRequired(active.key, "Structured XMP property needs manual review")
        element, lexical_name = _names(name)
        properties = {}
        selected = {}
        qualified = qualified_scope[-1]
        for attribute, value in attrs.items():
            expanded, spelling = _names(attribute)
            properties[expanded] = value
            if expanded in targets:
                selected[spelling] = (targets[expanded], value)
            if spelling in {"xml:base", "xml:lang"} and value:
                qualified = True
        qualified_scope.append(qualified)
        if element in PROVENANCE or PROVENANCE.intersection(properties):
            raise ValueError("Possible XMP provenance reference. Review and re-export from the original")

        parent_is_description = (len(ancestry) in (2, 3) and ancestry[-1] == (RDF, "Description")
                                 and _top_rdf(ancestry[:-1]))
        top_record = _top_rdf(ancestry)
        if top_record:
            top_records += 1
        ancestry.append(element)
        is_description = top_record and element == (RDF, "Description")
        dji_subject = False
        if is_description:
            about = properties.get((RDF, "about"))
            unambiguous = (RDF, "ID") not in properties and (RDF, "nodeID") not in properties
            own_subject = unambiguous and not about
            dji_subject = unambiguous and about == "DJI Meta Data" and not qualified

        offset = parser.CurrentByteIndex
        cursor = offset + 1 + len(lexical_name.encode())
        while match := ATTRIBUTE.match(packet, cursor):
            cursor = match.end()
            attr = match[1].decode()
            if attr in selected:
                key, value = selected[attr]
                if dji_subject and key in PRIVACY_FIELDS:
                    used_dji_privacy = True
                elif not is_description or not own_subject:
                    raise FieldReviewRequired(key, "Nested or unrelated XMP field needs manual review")
                record(key, match.start(), cursor, value)

        if element in targets:
            key = targets[element]
            if key != SOURCE_TYPE and (qualified or properties):
                raise FieldReviewRequired(key, "Qualified XMP property needs manual review")
            if not parent_is_description or not own_subject:
                raise FieldReviewRequired(key, "Nested or unrelated XMP field needs manual review")
            if properties.keys() - {(RDF, "resource")}:
                raise FieldReviewRequired(key, "Qualified XMP property needs manual review")
            closing = TAG_END.match(packet, cursor)
            if closing is None:
                raise ValueError("Unsupported XMP opening tag")
            active = _SimpleElement(key, offset, closing.end(), bool(closing[1]), properties.get((RDF, "resource")))

    def characters(value):
        if active is not None:
            active.text.append(value)

    def end(name):
        nonlocal active
        if active is not None:
            # For <p/> Expat calls end at the next byte. For <p>...</p>
            # CurrentByteIndex points to the '<' of the closing tag.
            end_offset = active.content_start
            if not active.self_closing:
                close_start = parser.CurrentByteIndex
                if b"<" in packet[active.content_start:close_start]:
                    raise FieldReviewRequired(active.key, "Markup inside XMP property needs manual review")
                end_offset = packet.index(b">", close_start) + 1
            value = "".join(active.text)
            if active.resource is not None:
                if value.strip(" \t\r\n"):
                    raise FieldReviewRequired(active.key, "Mixed XMP resource and text need manual review")
                value = active.resource
            record(active.key, active.start, end_offset, value)
            active = None
        ancestry.pop()
        qualified_scope.pop()

    parser.StartElementHandler = start
    parser.CharacterDataHandler = characters
    parser.EndElementHandler = end
    try:
        parser.Parse(packet, True)
    except expat.ExpatError as exc:
        raise ValueError("Malformed XMP") from exc
    # A second resource can follow the selected attribute in document order.
    if used_dji_privacy and top_records != 1:
        raise ValueError("DJI privacy correction requires a single top-level RDF record")
    return found
