"""Fixed-length metadata changes in supported PNG, WebP and GIF containers."""
from hashlib import sha256
from struct import pack
from zlib import crc32

from photometaclean.formats.history import EDITOR, HISTORY
from photometaclean.formats.recipes import PNG_KEYS, png_recipe
from photometaclean.formats.xmp import FIELDS, locations

PACKET_LIMIT = 4 * 1024**2
PNG_SIGNATURE = b"\x89PNG\r\n\x1a\n"
PNG_RENDER = set(b"IHDR IDAT IEND PLTE tRNS cHRM gAMA iCCP sBIT sRGB bKGD hIST pHYs tIME acTL fcTL fdAT cICP mDCV cLLI".split())
WEBP_RENDER = set(b"VP8X VP8L ALPH ICCP ANIM ANMF".split()) | {b"VP8 "}


def packet_edits(raw, offset, wanted):
    if len(raw) > PACKET_LIMIT or b"c2pa" in raw.lower() or b"HasExtendedXMP" in raw:
        raise ValueError("Unsupported or protected XMP packet")
    edits = [(key, offset + start, offset + end, old)
            for key, start, end, old in locations(raw, wanted & FIELDS.keys())]
    if HISTORY in wanted:
        from .share import packet_spans
        for start, end, label in packet_spans(raw, clean_ai=False, history=True):
            edits.append((HISTORY, offset + start, offset + end, label))
    return edits


def png(data, wanted, media):
    if not data.startswith(PNG_SIGNATURE):
        raise ValueError("Invalid PNG signature")
    edits, checksums = [], []
    seen_xmp = False
    recipe_bytes = 0
    comment_bytes = 0
    pos = len(PNG_SIGNATURE)
    while pos + 12 <= len(data):
        size = int.from_bytes(data[pos:pos+4], "big")
        kind = data[pos+4:pos+8]
        start, end = pos + 8, pos + 8 + size
        if end + 4 > len(data) or crc32(memoryview(data)[pos+4:end]) != int.from_bytes(data[end:end+4], "big"):
            raise ValueError("Invalid PNG chunk or checksum")
        if kind in PNG_RENDER:
            media.update(memoryview(data)[pos:end+4])
        elif kind == b"caBX":
            raise ValueError("Possible signed PNG provenance")
        elif kind in {b"tEXt", b"iTXt", b"zTXt"} and size <= PACKET_LIMIT:
            text = data[start:end]
            key, sep, value = text.partition(b"\0")
            if not sep:
                raise ValueError("Invalid PNG text")
            changes = []
            if key == b"XML:com.adobe.xmp" and kind == b"iTXt" and value.startswith(bytes(4)) and not seen_xmp:
                seen_xmp = True
                changes = packet_edits(value[4:], start + len(key) + 5, wanted)
            elif key in PNG_KEYS:
                record = png_recipe(kind, key, value, history=HISTORY in wanted)
                if record and record[0] in wanted:
                    field, contents = record
                    recipe_bytes += len(contents)
                    if recipe_bytes > PACKET_LIMIT or len(edits) >= 16384:
                        raise ValueError("PNG processing settings exceed audit limit")
                    # PNG chunks are self-contained. Remove the complete record, CRC included.
                    edits.append(("PNG:Software" if field == HISTORY else field, pos, end + 4, contents))
            elif key in {b"Title", b"Author", b"Copyright", b"Description",
                         b"Creation Time", b"Disclaimer", b"Warning", b"Source"}:
                pass  # Descriptive fields and attribution travel with the copy.
            elif key == b"Comment" and kind == b"tEXt":
                if "PNG:Comment" in wanted and value.strip(b" "):
                    comment_bytes += len(value)
                    if comment_bytes > PACKET_LIMIT or len(edits) >= 16384:
                        raise ValueError("Comment data exceeds audit limit")
                    changes.append(("PNG:Comment", end-len(value), end, value.hex()))
            else:
                raise ValueError("Unreviewed PNG text or provenance container")
            if changes:
                replacement = bytearray(data[pos+4:end])
                for _, a, b, _ in changes:
                    replacement[a-pos-4:b-pos-4] = b" " * (b-a)
                checksums.append((end, pack(">I", crc32(replacement))))
                edits.extend(changes)
        else:
            raise ValueError("Unsupported PNG metadata container")
        pos = end + 4
        if kind == b"IEND":
            if size or pos != len(data):
                raise ValueError("Additional PNG data")
            return edits, checksums
    raise ValueError("Incomplete PNG")


def webp(data, wanted, media):
    if data[:4] != b"RIFF" or data[8:12] != b"WEBP" or int.from_bytes(data[4:8], "little") + 8 != len(data):
        raise ValueError("Invalid WebP container")
    edits = []
    seen_xmp = False
    pos = 12
    while pos < len(data):
        kind = data[pos:pos+4]
        size = int.from_bytes(data[pos+4:pos+8], "little")
        start, end = pos + 8, pos + 8 + size
        after = end + size % 2
        if after > len(data):
            raise ValueError("Invalid WebP chunk length")
        if kind == b"XMP " and not seen_xmp and size <= PACKET_LIMIT:
            edits.extend(packet_edits(data[start:end], start, wanted))
            seen_xmp = True
        elif kind in WEBP_RENDER:
            if kind == b"ANMF":
                # Only frame-local alpha and compressed raster chunks are understood.
                sub = start + 16
                while sub + 8 <= end and data[sub:sub+4] in {b"ALPH", b"VP8 ", b"VP8L"}:
                    length = int.from_bytes(data[sub+4:sub+8], "little")
                    sub += 8 + length + length % 2
                if sub != end:
                    raise ValueError("Unrecognized WebP animation frame layout")
            media.update(memoryview(data)[pos:after])
        else:
            raise ValueError("Protected or unsupported WebP container")
        pos = after
    return edits, []


def gif(data, wanted, media):
    if data[:6] not in (b"GIF87a", b"GIF89a") or len(data) < 14:
        raise ValueError("Invalid GIF header")
    def table(flags):
        return 3 * (2 << (flags & 7)) if flags & 128 else 0

    pos = 13 + table(data[10])
    media.update(data[:pos])
    edits = []
    while pos < len(data):
        start = pos
        block = data[pos:pos+1]
        if block == b";" and pos + 1 == len(data):
            return edits, []
        comment = False
        if block == b"," and pos + 10 < len(data):
            pos += 11 + table(data[pos+9])
        elif block == b"!" and pos + 2 < len(data):
            kind = data[pos+1]
            pos += 2
            comment = kind == 0xfe
            if kind == 0xff and data[pos:pos+12] not in (b"\x0bNETSCAPE2.0", b"\x0bANIMEXTS1.0"):
                raise ValueError("Protected or unsupported GIF application extension")
            if kind not in (0xff, 0xf9, 0xfe):
                raise ValueError("Unsupported GIF extension")
        else:
            raise ValueError("Invalid GIF block")
        while pos < len(data) and data[pos]:
            size = data[pos]
            a, b = pos + 1, pos + 1 + size
            if b > len(data):
                raise ValueError("Truncated GIF block")
            if comment and "GIF:Comment" in wanted and data[a:b].strip(b" "):
                if len(edits) >= 16384:
                    raise ValueError("Comment data exceeds audit limit")
                edits.append(("GIF:Comment", a, b, data[a:b].hex()))
            pos = b
        if pos >= len(data):
            raise ValueError("Truncated GIF")
        pos += 1
        if not comment:
            media.update(memoryview(data)[start:pos])
    raise ValueError("Missing GIF trailer")


def tiff(data, wanted, media):
    """Classic single-IFD TIFF with disjoint metadata and independently hashed strips."""
    if data[:4] not in (b"II*\0", b"MM\0*"):
        raise ValueError("Unsupported TIFF header")
    order = "little" if data[:2] == b"II" else "big"

    def number(start, width):
        return int.from_bytes(data[start:start+width], order)

    ifd = number(4, 4)
    count = number(ifd, 2)
    end = ifd + 2 + 12 * count
    if ifd < 8 or not count or end+4 > len(data) or number(end, 4):
        raise ValueError("Multiple or invalid TIFF directories require review")
    # Private tags, SubIFDs, EXIF trees and opaque Photoshop resources require review.
    allowed = {256, 257, 258, 259, 262, 266, 270, 273, 274, 277, 278, 279,
               282, 283, 284, 296, 305, 306, 315, 317, 320, 338, 339, 700, 33432, 34675}
    widths = {1: 1, 2: 1, 3: 2, 4: 4, 5: 8, 7: 1}
    ranges = [(0, 8), (ifd, end+4)]
    tags = {}
    edits = []
    for pos in range(ifd+2, end, 12):
        tag, typ, entries = number(pos, 2), number(pos+2, 2), number(pos+4, 4)
        if tag not in allowed or tag in tags or typ not in widths or not entries:
            raise ValueError("Protected or unsupported TIFF tag")
        size = widths[typ] * entries
        start = pos+8 if size <= 4 else number(pos+8, 4)
        if start+size > len(data):
            raise ValueError("Truncated TIFF field")
        if size > 4:
            ranges.append((start, start+size))
        tags[tag] = (typ, entries, start)
        if tag == 700:
            if typ != 1 or size > PACKET_LIMIT:
                raise ValueError("Unsupported TIFF XMP")
            edits.extend(packet_edits(data[start:start+size], start, wanted))
        if tag == 305 and typ == 2 and HISTORY in wanted:
            text = data[start:start+size]
            if text.endswith(b"\0") and EDITOR.search(text[:-1].decode("ascii", "replace")):
                edits.append((HISTORY, start, start+size-1, "IFD0:Software"))
        if tag == 270:
            text = data[start:start+size] if size <= PACKET_LIMIT else b""
            if (typ != 2 or not text.endswith(b"\0") or b"\0" in text[:-1]
                    or b"<" in text or b"c2pa" in text.lower()):
                raise ValueError("Structured TIFF description requires review")
            if "TIFF:ImageDescription" in wanted and text[:-1].strip(b" "):
                edits.append(("TIFF:ImageDescription", start, start+size-1, text[:-1].hex()))

    def integers(tag):
        if tag not in tags:
            raise ValueError("Missing TIFF strip or compression tag")
        typ, count, start = tags[tag]
        if typ not in {3, 4} or count > 131072:
            raise ValueError("Unsupported TIFF strip layout")
        width = widths[typ]
        return [number(start+i*width, width) for i in range(count)]

    if integers(259) not in ([1], [5], [8], [32946], [32773]):
        raise ValueError("Unsupported TIFF compression")
    for offset, size in zip(integers(273), integers(279), strict=True):
        if not size or offset+size > len(data):
            raise ValueError("Invalid TIFF strip")
        ranges.append((offset, offset+size))
        media.update(size.to_bytes(8, "big"))
        media.update(memoryview(data)[offset:offset+size])
    previous = 0
    for start, stop in sorted(ranges):
        if start < previous:
            raise ValueError("Overlapping TIFF storage")
        previous = stop
    return edits, []


def heif(data, wanted, media):
    from photometaclean.formats.heif import xmp_item

    (start, end), (picture, stop) = xmp_item(data)
    if end - start > PACKET_LIMIT:
        raise ValueError("HEIF XMP exceeds limit")
    media.update(memoryview(data)[picture:stop])
    return packet_edits(data[start:end], start, wanted), []


PARSERS = {".png": png, ".apng": png, ".webp": webp, ".gif": gif, ".tif": tiff, ".tiff": tiff,
           ".heic": heif, ".heif": heif, ".hif": heif, ".avif": heif}


def inspect_raster(parser, data, wanted):
    media = sha256()
    edits, checksums = parser(data, wanted, media)
    return edits, checksums, media.hexdigest()
