"""Locate editable tool fields and exclude shared EXIF storage and JPEG previews."""
from .history import EDITOR
from photometaclean.metadata.generators import generator_signal


def generator_fields(data, start, end, *, clean_ai=True, history=False):
    raw = data[start:end]
    order = {b"II": "little", b"MM": "big"}.get(raw[:2])
    if not order:
        raise ValueError("Unknown EXIF byte order")

    def integer(pos, length):
        if pos < 0 or pos + length > len(raw):
            raise ValueError("Truncated EXIF directory")
        return int.from_bytes(raw[pos:pos + length], order)

    if integer(2, 2) != 42:
        raise ValueError("Unsupported EXIF header")
    ranges, edits = [(0, 8)], []
    widths = {1:1, 2:1, 3:2, 4:4, 5:8, 6:1, 7:1, 8:2, 9:4, 10:8, 11:4, 12:8}
    visited = set()

    def directory(pos, group):
        if pos in visited or len(visited) >= 8:
            raise ValueError("Unexpected EXIF directory chain")
        visited.add(pos)
        count = integer(pos, 2)
        stop = pos+2+12*count
        following = integer(stop, 4)
        pointers = []
        thumbnail = {}
        ranges.append((pos, stop+4))
        seen = set()
        for idx in range(count):
            row = pos+2+12*idx
            tag, typ, n = integer(row,2), integer(row+2,2), integer(row+4,4)
            if tag in seen or typ not in widths or tag in {0x014a,0x111,0x144}:
                raise ValueError("Complex EXIF layout needs review")
            seen.add(tag)
            size = n*widths[typ]
            off = integer(row+8,4) if size>4 else row+8
            if off+size>len(raw):
                raise ValueError("Invalid EXIF field size")
            if tag in {0x8769, 0x8825, 0xa005}:
                parent, child = {0x8769: ("IFD0", "ExifIFD"), 0x8825: ("IFD0", "GPS"),
                                 0xa005: ("ExifIFD", "InteropIFD")}[tag]
                if group != parent or typ != 4 or n != 1:
                    raise ValueError("Invalid EXIF directory pointer")
                pointers.append((integer(row+8,4), child))
            if tag in {0x201, 0x202}:
                if group != "IFD1" or typ != 4 or n != 1:
                    raise ValueError("Unsupported EXIF preview")
                thumbnail[tag] = integer(row+8,4)
            if size > 4:
                ranges.append((off, off+size))
            field = None
            if group=="IFD0" and tag==305 and typ==2:
                field = "IFD0:Software"
                text = raw[off:off+size].rstrip(b"\0").decode("ascii",errors="replace")
            elif group=="ExifIFD" and tag==37510 and typ in {1, 7} and size>=8:
                field = "ExifIFD:UserComment"
                prefix = raw[off:off+8]
                payload = raw[off+8:off+size]
                if prefix==b"UNICODE\0":
                    enc = "utf-16" if payload[:2] in (b"\xff\xfe",b"\xfe\xff") else "utf-16-be"
                    text = payload.decode(enc,errors="replace").rstrip("\0")
                elif prefix==b"ASCII\0\0\0":
                    text = payload.rstrip(b"\0").decode("ascii",errors="replace")
                else:
                    continue
            if field and ((clean_ai and generator_signal(field,text)) or
                          (history and field == "IFD0:Software" and EDITOR.search(text))):
                if size <= 4:
                    raise ValueError("Inline EXIF tool record needs review")
                edits.append((start+off,start+off+size,bytes(size),field))
        if thumbnail:
            location, length = thumbnail.get(0x201), thumbnail.get(0x202)
            if location is None or length is None or location+length > len(raw):
                raise ValueError("Incomplete EXIF preview")
            ranges.append((location, location+length))
        if following:
            if group != "IFD0":
                raise ValueError("Unsupported EXIF directory chain")
            pointers.append((following, "IFD1"))
        for target, child in pointers:
            directory(target, child)
    directory(integer(4,4),"IFD0")
    for a, b, _, _ in edits:
        if sum(left < b-start and a-start < right for left, right in ranges) != 1:
            raise ValueError("Overlapping EXIF storage")
    return edits
