"""Synthetic round trips through the same approval and publication path as the GUI."""
from hashlib import sha256
from pathlib import Path
import struct
from zlib import crc32

from PIL import Image, PngImagePlugin, TiffImagePlugin
import pytest

from photometaclean.core.edit import apply, plan
from photometaclean.core.review import apply_reviewed, review
from photometaclean.metadata.analysis import analyze
from photometaclean.formats.heif import xmp_item


SERIAL = "XMP-aux:SerialNumber"
XMP = (b'<r:RDF xmlns:r="http://www.w3.org/1999/02/22-rdf-syntax-ns#">'
       b'<r:Description xmlns:a="http://ns.adobe.com/exif/1.0/aux/" a:%s="synthetic"/>'
       b'</r:RDF>') % SERIAL.split(":")[1].encode()


def generate(path, key, animated=False):
    one = Image.new("RGB", (20, 16), "teal")
    options = {}
    if animated:
        options.update(save_all=True, append_images=[Image.new("RGB", one.size, "yellow")],
                       duration=[110, 240], loop=2)
    if path.suffix in {".png", ".apng"}:
        info = PngImagePlugin.PngInfo()
        if key == SERIAL:
            info.add_itxt("XML:com.adobe.xmp", XMP.decode())
        else:
            info.add_text("Comment", "synthetic")
        options["pnginfo"] = info
    elif path.suffix == ".gif":
        options["comment"] = b"synthetic" * 40
    elif path.suffix == ".tif":
        tags = TiffImagePlugin.ImageFileDirectory_v2()
        tags[270] = "synthetic TIFF"
        tags[700] = XMP
        options.update(tiffinfo=tags, compression="tiff_adobe_deflate")
    else:
        options["xmp"] = XMP
    one.save(path, **options)


@pytest.mark.parametrize("suffix,key,animated", [
    (".png", "PNG:Comment", False), (".apng", SERIAL, True), (".png", SERIAL, False),
    (".webp", SERIAL, False), (".webp", SERIAL, True), (".gif", "GIF:Comment", True),
    (".tif", "TIFF:ImageDescription", False), (".tif", SERIAL, False), (".avif", SERIAL, False),
])
def test_raster_round_trip(tmp_path, suffix, key, animated):
    path = tmp_path / ("Nacht Test" + suffix)
    generate(path, key, animated)
    original = path.read_bytes()
    approved = review(path, {key: None})
    dest = tmp_path / "output" / path.name
    audit = apply_reviewed(approved, dest)["audit"]
    assert audit["integrity_before"] == audit["integrity_after"]
    assert len(audit["integrity_after"]["frames"]) == (2 if animated else 1)
    assert path.read_bytes() == original and dest.read_bytes() != original
    permitted = set()
    for change in audit["changes"]:
        permitted.update(range(change["offset"], change["offset"] + change["length"]))
    for offset in audit.get("checksum_offsets", []):
        permitted.update(range(offset, offset + 4))
    assert all(i in permitted for i, (a,b) in enumerate(zip(original, dest.read_bytes(), strict=True)) if a != b)
    result = analyze(dest)
    assert result["sha256"] == sha256(dest.read_bytes()).hexdigest()
    assert result["pixel_status"] == "decoded"
    if key == SERIAL:
        assert not any(k.endswith(":SerialNumber") and v for k,v in result["metadata"].items())
    with pytest.raises(ValueError, match="missing|blank"):
        plan(dest, {key: None})
    path.with_suffix(".C2PA").touch()
    with pytest.raises(ValueError, match="manifest"):
        plan(path, {key: None})


@pytest.mark.parametrize("suffix,format", [(".avif", "AVIF"), (".bmp", "BMP"), (".jp2", "JPEG2000"),
                                          (".tiff", "TIFF"), (".gif", "GIF"), (".webp", "WEBP")])
def test_analysis_image_types(tmp_path, suffix, format):
    path = tmp_path / ("image" + suffix)
    Image.new("RGB", (13, 19)).save(path)
    record = analyze(path)
    assert (record["format"], record["resolution"]) == (format, [13, 19])
    assert record["frames"][0]["pixels"]


def test_heif_container_alias_or_signature_blocks(tmp_path):
    p = tmp_path / "photo.avif"
    generate(p, SERIAL)
    data = p.read_bytes()
    (start, end), (primary, stop) = xmp_item(data)
    assert data[start:end] == XMP and stop > primary
    with pytest.raises(ValueError):
        xmp_item(data + struct.pack(">I4s", 8, b"uuid"))
    iloc = data.index(b"iloc") + 4
    # Version zero, 32-bit offsets. Force the XMP item to overlap the frame.
    changed = bytearray(data)
    changed[iloc+28:iloc+32] = changed[iloc+14:iloc+18]
    with pytest.raises(ValueError):
        xmp_item(changed)


@pytest.mark.parametrize("suffix,key", [(".png", "PNG:Comment"), (".gif", "GIF:Comment"), (".webp", SERIAL)])
def test_embedded_opaque_provenance_blocks_edit(tmp_path, suffix, key):
    p = tmp_path / ("img" + suffix)
    generate(p, key)
    raw = p.read_bytes()
    if suffix == ".png":
        box = b"caBX" + b"signature"
        raw = raw[:33] + struct.pack(">I", 9) + box + struct.pack(">I", crc32(box)) + raw[33:]
    elif suffix == ".gif":
        raw = raw[:-1] + b"!\xff\x0bC2PA_GIF123\x00;"
    else:
        raw += b"C2PA\x04\0\0\0test"
        raw = raw[:4] + (len(raw)-8).to_bytes(4,"little") + raw[8:]
    p.write_bytes(raw)
    with pytest.raises(ValueError):
        apply(p, tmp_path / "out" / p.name, {key: None})
    assert p.read_bytes() == raw and not (tmp_path / "out").exists()


def test_gif_truncation_and_png_crc(tmp_path):
    for suffix, key in [(".gif", "GIF:Comment"), (".png", "PNG:Comment")]:
        p = tmp_path / ("sample" + suffix)
        generate(p, key)
        data = p.read_bytes()
        p.write_bytes(data[:-1] if suffix == ".gif" else data.replace(b"synthetic", b"changed!!"))
        with pytest.raises(ValueError):
            plan(p, {key: None})
