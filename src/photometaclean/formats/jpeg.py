"""Strict JPEG traversal and validation of the supported two-image MP index."""
from dataclasses import dataclass, replace
import re
import struct
from xml.etree import ElementTree


@dataclass(frozen=True)
class Segment:
    marker: int
    start: int
    payload: int
    end: int


@dataclass(frozen=True)
class Codestream:
    start: int
    end: int
    parts: list[Segment]
    fixed_layout: bool = False


def _codestream(data, offset):
    if not data.startswith(b"\xff\xd8", offset):
        raise ValueError("Expected a JPEG SOI marker")
    result = []
    pos = offset + 2
    scans = 0
    frame = False
    while pos < len(data):
        start = pos
        if data[pos] != 255:
            raise ValueError("Invalid JPEG marker boundary")
        while pos < len(data) and data[pos] == 255:
            pos += 1
        if pos == len(data):
            break
        marker = data[pos]
        pos += 1
        if marker == 0xD9:
            if not scans:
                raise ValueError("Empty JPEG")
            return Codestream(offset, pos, result)
        if marker not in (0xc0, 0xc1, 0xc2, 0xc4, 0xda, 0xdb, 0xdd, 0xfe) and not 0xe0 <= marker <= 0xef:
            raise ValueError("Unsupported JPEG marker")
        size = int.from_bytes(data[pos:pos+2], "big")
        end = pos + size
        if size < 2 or end > len(data):
            raise ValueError("Invalid JPEG segment length")
        if len(result) >= 16384:
            raise ValueError("Too many JPEG segments")
        result.append(Segment(marker, start, pos + 2, end))
        pos = end
        if marker in (0xc0, 0xc1, 0xc2):
            if frame:
                raise ValueError("Multiple JPEG frames")
            frame = True
        if marker == 0xda:
            if not frame:
                raise ValueError("Missing JPEG frame")
            scans += 1
            for match in _entropy_markers.finditer(data, pos):
                code = match[1][0]
                if code and not 0xd0 <= code <= 0xd7:
                    break
            else:
                raise ValueError("Truncated JPEG scan")
            result.append(Segment(0, pos, pos, match.start()))
            pos = match.start()
    raise ValueError("Missing JPEG EOI")


_entropy_markers = re.compile(rb"\xff+([^\xff])")


MPF = b"MPF\0"
ISO_GAIN_MAP = b"urn:iso:std:iso:ts:21496:-1\0"
XMP_PACKET = b"http://ns.adobe.com/xap/1.0/\0"


def _mobile_gain_map(data, auxiliary):
    packets = [p for p in auxiliary.parts if p.marker == 0xe1 and data.startswith(XMP_PACKET, p.payload, p.end)]
    if len(packets) != 1:
        return False
    part = packets[0]
    packet = data[part.payload + len(XMP_PACKET):part.end]
    if b"<!DOCTYPE" in packet or b"\0" in packet:
        return False
    try:
        root = ElementTree.fromstring(packet)
    except ElementTree.ParseError:
        return False
    version = "{http://ns.adobe.com/hdr-gain-map/1.0/}Version"
    apple_type = "{http://ns.apple.com/pixeldatainfo/1.0/}AuxiliaryImageType"
    apple_version = "{http://ns.apple.com/HDRGainMap/1.0/}HDRGainMapVersion"
    from .xmp import RDF, XMP_META, locations
    locations(packet, ())  # Also rejects embedded XMP provenance references.
    rdf = root if root.tag == f"{{{RDF}}}RDF" else root.find(f"{{{RDF}}}RDF")
    if rdf is None or (root is not rdf and root.tag != f"{{{XMP_META}}}xmpmeta"):
        return False
    for desc in rdf.findall(f"{{{RDF}}}Description"):
        if desc.get(f"{{{RDF}}}about"):
            continue
        if desc.get(version, desc.findtext(version)) == "1.0":
            return True
        if (desc.findtext(apple_type) == "urn:com:apple:photo:2020:aux:hdrgainmap"
                and desc.findtext(apple_version) == "131072"):
            return True
    return False


def segments(data: bytes) -> list[Segment]:
    stream = _codestream(data, 0)
    if stream.end != len(data):
        raise ValueError("Additional JPEG data")
    return stream.parts


def _matching(data, stream, prefix):
    return [p for p in stream.parts if p.marker == 0xe2 and data.startswith(prefix, p.payload, p.end)]


def _verify_index(data, part, primary, auxiliary, allow_provenance=False):
    # Only the classic MPF 0100 three-tag IFD, two 16-byte entries and no next IFD.
    origin = part.payload + len(MPF)
    tiff = data[origin:part.end]
    if len(tiff) != 82 or tiff[:2] not in {b"MM", b"II"}:
        raise ValueError("Unsupported MP index")
    order = ">" if tiff[:2] == b"MM" else "<"
    expected = (struct.pack(order + "HIH", 42, 8, 3)
                + struct.pack(order + "HHI", 0xb000, 7, 4) + b"0100"
                + struct.pack(order + "HHII", 0xb001, 4, 1, 2)
                + struct.pack(order + "HHII", 0xb002, 7, 32, 50)
                + struct.pack(order + "I", 0))
    if tiff[2:50] != expected:
        raise ValueError("Unsupported MP index directory")
    first = struct.unpack_from(order + "IIIHH", tiff, 50)
    second = struct.unpack_from(order + "IIIHH", tiff, 66)
    if first[0] == 0x030000 and second[0] == 0:
        # Some phone encoders leave a stale primary size. Locate both streams by
        # parsing SOI through EOI, then independently verify the secondary index.
        # This layout is editable only at fixed offsets, with the exact MPF retained.
        first_scan = next(p.start for p in primary.parts if p.marker == 0)
        if (not first_scan < first[1] <= len(data) or first[2:] != (0, 0, 0)
                or second[1:] != (auxiliary.end - auxiliary.start, auxiliary.start - origin, 0, 0)
                or not _mobile_gain_map(data, auxiliary)):
            raise ValueError("Unverified mobile HDR index or gain-map description")
        return True
    primary_sizes = {primary.end}
    if allow_provenance:
        # Some signed Adobe exports inserted leading APP11 bytes after writing the MP index.
        prefix = primary.start + 2
        for item in primary.parts:
            if item.marker != 0xeb or item.start != prefix:
                break
            prefix = item.end
        primary_sizes.add(primary.end - (prefix - primary.start - 2))
    if (first[1] not in primary_sizes or first != (0x20030000, first[1], 0, 0, 0)
            or second != (0x50000, auxiliary.end - auxiliary.start, auxiliary.start - origin, 0, 0)):
        raise ValueError("MP index does not match the JPEG stream boundaries or gain-map image type")
    return False


def image_streams(data, *, allow_provenance=False):
    primary = _codestream(data, 0)
    if not allow_provenance and any(p.marker == 0xeb for p in primary.parts):
        raise ValueError("Possible signed provenance. Review and re-export from the original")
    indexes = _matching(data, primary, MPF)
    if primary.end == len(data):
        if indexes or _matching(data, primary, ISO_GAIN_MAP):
            raise ValueError("Missing indexed gain map")
        return [primary]
    if len(indexes) != 1:
        raise ValueError("Additional image data requires one supported MP index")
    auxiliary = _codestream(data, primary.end)
    if any(p.marker == 0xeb for p in auxiliary.parts):
        raise ValueError("Possible signed provenance in gain map. Review the original")
    if auxiliary.end != len(data) or _matching(data, auxiliary, MPF):
        raise ValueError("Unexpected additional data in gain-map container")
    if _verify_index(data, indexes[0], primary, auxiliary, allow_provenance):
        if any(p.marker == 0xeb for p in primary.parts):
            raise ValueError("Mobile HDR provenance requires review")
        if any(_matching(data, image, ISO_GAIN_MAP) for image in (primary, auxiliary)):
            raise ValueError("Mixed HDR descriptors require review")
        return [replace(primary, fixed_layout=True), auxiliary]
    for image in (primary, auxiliary):
        descriptors = _matching(data, image, ISO_GAIN_MAP)
        if len(descriptors) != 1:
            raise ValueError("Expected one ISO gain-map descriptor in each stream")
        descriptor = descriptors[0]
        payload = data[descriptor.payload + len(ISO_GAIN_MAP):descriptor.end]
        if image is primary:
            if payload != bytes(4):
                raise ValueError("Unsupported primary ISO gain-map descriptor")
        else:
            expected_size = {b"\x40": 61, b"\xc0": 141}.get(payload[4:5])
            if len(payload) != expected_size or payload[:4] != bytes(4):
                raise ValueError("Unsupported auxiliary ISO gain-map descriptor")
            if any(denominator == 0 for _, denominator in struct.iter_unpack(">II", payload[5:])):
                raise ValueError("Invalid ISO gain-map fraction")
    return [primary, auxiliary]


def is_thumbnail(data):
    if len(data) < 30:
        return False
    fmt, width, height, stride, raw_size, size, depth, planes = struct.unpack_from(">6I2H", data)
    if (fmt != 1 or not 0 < width < 65536 or not 0 < height < 65536 or stride != ((width * 3 + 3) // 4) * 4
            or raw_size != stride * height or size != len(data) - 28
            or (depth, planes) != (24, 1)):
        return False
    jpeg = data[28:]
    parts = segments(jpeg)
    sof = next(p for p in parts if p.marker in (0xc0, 0xc1, 0xc2))
    if jpeg[sof.payload:sof.payload + 6] != struct.pack(">BHHB", 8, height, width, 3):
        return False
    # Photoshop's plain RGB JPEG preview. Opaque application metadata needs review.
    return all(not (0xe1 <= part.marker <= 0xed or part.marker == 0xef) for part in parts)


def is_supported_photoshop_block(payload: bytes) -> bool:
    """Recognize supported Photoshop resources including the plain JPEG preview."""
    header = b"Photoshop 3.0\0"
    if not payload.startswith(header):
        return False
    pos = len(header)
    while pos < len(payload):
        if payload[pos:pos + 4] != b"8BIM" or pos + 7 > len(payload):
            return False
        resource = int.from_bytes(payload[pos + 4:pos + 6], "big")
        if resource not in {0x0404, 0x0425, 0x03ED, 0x040c}:
            return False
        name_size = 1 + payload[pos + 6]
        pos += 6 + name_size + (name_size % 2)
        if pos + 4 > len(payload):
            return False
        size = int.from_bytes(payload[pos:pos + 4], "big")
        if resource in {0x0425, 0x03ED} and size != 16:
            return False
        if resource == 0x040c and not is_thumbnail(payload[pos + 4:pos + 4 + size]):
            return False
        pos += 4 + size + (size % 2)
    return pos == len(payload) and pos > len(header)
