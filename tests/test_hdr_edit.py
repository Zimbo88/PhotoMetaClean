"""Generate indexed gain maps with controlled structure and known source pixels."""
import hashlib
import io
import struct

from PIL import Image
import pytest

from photometaclean.core.edit import apply, plan
from photometaclean.formats.jpeg import ISO_GAIN_MAP, image_streams
from photometaclean.verification.jpeg import fingerprint


def segment(marker, contents):
    return bytes((255, marker)) + struct.pack(">H", len(contents) + 2) + contents


def jpeg(size, color):
    with io.BytesIO() as buffer:
        Image.new("RGB", size, color).save(buffer, format="JPEG", progressive=True)
        return buffer.getvalue()


def indexed(order=">", extra=b"", incorrect_offset=False, descriptor=None):
    primary = jpeg((20, 16), "gray")
    auxiliary = jpeg((5, 4), "orange")
    if descriptor is None:
        descriptor = bytes(4) + b"\x40" + struct.pack(">II", 1, 1) * 7
    auxiliary = auxiliary[:2] + segment(0xe2, ISO_GAIN_MAP + descriptor) + extra + auxiliary[2:]
    primary_meta = segment(0xfe, b"private") + segment(0xe2, ISO_GAIN_MAP + bytes(4))
    origin = 2 + len(primary_meta) + 4 + len(b"MPF\0")
    first_size = len(primary) + len(primary_meta) + 90
    index = b"MPF\0" + (b"MM" if order == ">" else b"II")
    index += struct.pack(order + "HIH", 42, 8, 3)
    index += struct.pack(order + "HHI4s", 0xb000, 7, 4, b"0100")
    index += struct.pack(order + "HHII", 0xb001, 4, 1, 2)
    index += struct.pack(order + "HHIII", 0xb002, 7, 32, 50, 0)
    index += struct.pack(order + "IIIHH", 0x20030000, first_size, 0, 0, 0)
    index += struct.pack(order + "IIIHH", 0x50000, len(auxiliary), first_size - origin + incorrect_offset, 0, 0)
    return primary[:2] + primary_meta + segment(0xe2, index) + primary[2:] + auxiliary


@pytest.mark.parametrize("order", ["<", ">"])
def test_primary_only_edit_preserves_index_and_gain_map(tmp_path, order):
    src, dest = tmp_path / "hdr.jpg", tmp_path / "copy.jpg"
    raw = indexed(order)
    src.write_bytes(raw)
    preview = plan(src, {"JPEG:Comment": None})
    record = apply(src, dest, {"JPEG:Comment": None}, reviewed=preview)
    assert src.read_bytes() == raw
    output = dest.read_bytes()
    assert output == raw.replace(b"private", b"       ", 1)
    _, gain = image_streams(raw)
    before = record["integrity_before"]
    assert before == record["integrity_after"] == fingerprint(output)
    assert before["gain_map"]["stream_sha256"] == hashlib.sha256(raw[gain.start:]).hexdigest()
    assert before["gain_map"]["size"] == [5, 4] and before["size"] == [20, 16]
    assert before["gain_map"]["pixels"] != before["pixels"]


@pytest.mark.parametrize("data,message", [
    (indexed(incorrect_offset=True), "MP index"),
    (indexed(extra=segment(0xeb,b"JP")), "provenance"),
    (indexed(extra=segment(0xef,b"opaque")), "Unsupported metadata"),
    (indexed(extra=segment(0xfe,b"more")), "auxiliary"),
    (indexed(descriptor=bytes(5)), "descriptor"),
    (indexed(descriptor=bytes(4) + b"\x40" + bytes(56)), "fraction"),
    (indexed() + b"tail", "additional data"),
])
def test_uncertain_gain_map_refused(tmp_path, data, message):
    src, dest = tmp_path / "hdr.jpg", tmp_path / "out.jpg"
    src.write_bytes(data)
    with pytest.raises(ValueError, match=message):
        apply(src, dest, {"JPEG:Comment": None})
    assert not dest.exists()
    assert src.read_bytes() == data


def test_photoshop_thumbnail_preserved(tmp_path):
    thumb = jpeg((9, 7), "navy")
    header = struct.pack(">6I2H", 1, 9, 7, 28, 196, len(thumb), 24, 1)
    block = header + thumb
    resource = b"8BIM\x04\x0c\0\0" + struct.pack(">I", len(block)) + block + bytes(len(block) % 2)
    metadata = segment(0xed, b"Photoshop 3.0\0" + resource)
    raw = jpeg((20, 16), "gray")
    src, dest = tmp_path / "photo.jpg", tmp_path / "out.jpg"
    src.write_bytes(raw[:2] + metadata + segment(0xfe,b"private") + raw[2:])
    apply(src, dest, {"JPEG:Comment": None})
    assert metadata in dest.read_bytes()
