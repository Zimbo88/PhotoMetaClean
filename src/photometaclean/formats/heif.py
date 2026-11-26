"""Resolve an uncompressed XMP item describing a single HEVC or AV1 still image."""
import struct


def boxes(data, start, end):
    count = 0
    while start < end:
        if start + 8 > end or count >= 256:
            raise ValueError("Invalid HEIF box table")
        size, kind = struct.unpack_from(">I4s", data, start)
        if size < 8 or start + size > end:
            raise ValueError("Unsupported HEIF box length")
        yield kind, start + 8, start + size
        start += size
        count += 1


def directory(data, start, end, required):
    result = {}
    for kind, begin, stop in boxes(data, start, end):
        if kind not in required or kind in result:
            raise ValueError("Protected or unsupported HEIF box")
        result[kind] = (begin, stop)
    if set(result) != required:
        raise ValueError("Incomplete HEIF item directory")
    return result


def xmp_item(data):
    top = directory(data, 0, len(data), {b"ftyp", b"meta", b"mdat"})
    start, end = top[b"meta"]
    if data[start:start+4] != bytes(4):
        raise ValueError("Unsupported HEIF metadata version")
    meta = directory(data, start+4, end, {b"hdlr", b"pitm", b"iloc", b"iinf", b"iref", b"iprp"})

    def payload(kind):
        begin, stop = meta[kind]
        if stop - begin > 65536:
            raise ValueError("HEIF item directory exceeds limit")
        return data[begin:stop]

    primary = payload(b"pitm")
    if len(primary) != 6 or primary[:4] != bytes(4):
        raise ValueError("Unsupported primary item")
    primary_id = int.from_bytes(primary[4:], "big")
    begin, stop = meta[b"iinf"]
    if data[begin:begin+6] != b"\0\0\0\0\0\x02":
        raise ValueError("Only a single still image and its XMP item are supported")
    image_ids, xmp_ids = [], []
    for kind, begin, end in boxes(data, begin+6, stop):
        if kind != b"infe" or end-begin > 256 or end-begin < 13:
            raise ValueError("Invalid HEIF item description")
        info = data[begin:end]
        if info[:4] not in (b"\x02\0\0\0", b"\x02\0\0\x01") or info[6:8] != bytes(2):
            raise ValueError("Protected HEIF item")
        item = int.from_bytes(info[4:6], "big")
        if info[8:12] in (b"hvc1", b"av01"):
            image_ids.append(item)
        elif info[8:12] == b"mime" and info[12:].split(b"\0")[1:] in (
                [b"application/rdf+xml", b""], [b"application/rdf+xml", b"", b""]):
            xmp_ids.append(item)
        else:
            raise ValueError("Unsupported HEIF item type")
    if image_ids != [primary_id] or len(xmp_ids) != 1 or primary_id in xmp_ids:
        raise ValueError("Ambiguous HEIF items")
    xmp_id = xmp_ids[0]

    ref = payload(b"iref")
    if ref != struct.pack(">II4sHHH", 0, 14, b"cdsc", xmp_id, 1, primary_id):
        raise ValueError("XMP must describe the primary image only")
    begin, end = meta[b"iprp"]
    props = directory(data, begin, end, {b"ipma", b"ipco"})
    for kind, _, _ in boxes(data, *props[b"ipco"]):
        if kind not in {b"av1C", b"hvcC", b"ispe", b"colr", b"pixi", b"clap", b"irot", b"imir", b"pasp"}:
            raise ValueError("Unsupported HEIF image property")

    loc = payload(b"iloc")
    if loc[:5] != b"\0\0\0\0\x44" or loc[5:6] not in (b"\0", b"\x40") or loc[6:8] != b"\0\x02":
        raise ValueError("Unsupported HEIF item offsets")
    base_size = loc[5] >> 4
    if len(loc) != 8 + 2 * (14 + base_size):
        raise ValueError("Invalid HEIF offsets or extent count")
    extents = {}
    pos = 8
    for _ in range(2):
        item, reference = struct.unpack_from(">HH", loc, pos)
        base = int.from_bytes(loc[pos+4:pos+4+base_size], "big")
        count, offset, length = struct.unpack_from(">HII", loc, pos+4+base_size)
        if count != 1 or reference or not length or item in extents:
            raise ValueError("Invalid HEIF item extent")
        extents[item] = (base + offset, base + offset + length)
        pos += 14 + base_size
    if set(extents) != {primary_id, xmp_id}:
        raise ValueError("Missing HEIF item")
    first, second = sorted(extents.values())
    if (first[0], second[1]) != top[b"mdat"] or first[1] != second[0]:
        raise ValueError("Overlapping or unaccounted HEIF image data")
    return extents[xmp_id], extents[primary_id]
