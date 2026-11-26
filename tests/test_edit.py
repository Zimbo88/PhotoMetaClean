from concurrent.futures import ThreadPoolExecutor
from hashlib import sha256
import io

from PIL import Image
import pytest

from photometaclean.core.edit import apply, plan, XMP
from photometaclean.formats.jpeg import segments
from photometaclean.verification.jpeg import fingerprint

COMMENT = {"JPEG:Comment": None}
FIELD = "XMP-iptcExt:DigitalSourceType"
PACKET = b"""<r:RDF xmlns:r="http://www.w3.org/1999/02/22-rdf-syntax-ns#">
<r:Description xmlns:i="http://iptc.org/std/Iptc4xmpExt/2008-02-29/"
 xmlns:e="http://ns.adobe.com/exif/1.0/" e:GPSLatitude=''
 i:DigitalSourceType="declared" /></r:RDF>"""


def segment(marker, payload):
    return bytes([255, marker]) + (2 + len(payload)).to_bytes(2, "big") + payload


def fixture(path, *extra, progressive=False):
    stream = io.BytesIO()
    exif = Image.Exif()
    exif[271] = "Synthetic"
    exif[34665] = {37500: b"SONY DSC synthetic opaque bytes", 36867: "2000:01:01 00:00:00"}
    Image.new("RGB", (33, 19), "teal").save(stream, "JPEG", progressive=progressive,
                                            exif=exif, icc_profile=b"synthetic ICC payload")
    raw = stream.getvalue()
    path.write_bytes(raw[:2] + b"".join(extra) + raw[2:])
    return path


@pytest.mark.parametrize("progressive", [False, True])
def test_verified_edit(tmp_path, progressive):
    src = fixture(tmp_path / "Ü original.jpg", segment(254, b"private"), segment(225, XMP + PACKET),
                  progressive=progressive)
    dest = tmp_path / "a" / ("long " * 22 + "folder") / src.name
    original = src.read_bytes()
    changes = {**COMMENT, FIELD: None}
    preview = plan(src, changes, "owner's camera original and edit log")
    assert src.read_bytes() == original
    result = apply(src, dest, changes, preview["evidence"])
    output = dest.read_bytes()
    assert preview["changes"] == result["changes"]
    assert original == src.read_bytes()
    assert result["output_sha256"] == sha256(output).hexdigest()
    assert fingerprint(original) == fingerprint(output)
    assert b"private" not in output and b"DigitalSourceType" not in output
    assert b"SONY DSC" in output and b"2000:01:01" in output and b"GPSLatitude" in output
    expected = bytearray(original)
    for change in result["changes"]:
        start, size = change["offset"], change["length"]
        expected[start:start + size] = b" " * size
    assert output == expected
    with pytest.raises(FileExistsError):
        apply(src, dest, changes, preview["evidence"])


@pytest.mark.parametrize("extra", [segment(235, b"box"), segment(225, b"unknown"),
                                   segment(226, b"MPF\0"), segment(225, XMP + b"<broken"),
                                   segment(225, XMP + b"<!DOCTYPE x><x/>")])
def test_block_layouts(tmp_path, extra):
    src = fixture(tmp_path / "in.jpg", extra, segment(254, b"secret"))
    dest = tmp_path / "out.jpg"
    with pytest.raises(ValueError):
        apply(src, dest, COMMENT)
    assert not dest.exists()


@pytest.mark.parametrize("raw", [b"", b"\xff\xd8\xff", b"\xff\xd8\xff\xe1\x00\xff", b"PNG"])
def test_corruption(raw):
    with pytest.raises(ValueError):
        segments(raw)


def test_secondary_image_and_sidecar(tmp_path):
    src = fixture(tmp_path / "in.jpg", segment(254, b"comment"))
    src.with_suffix(".c2pa").touch()
    with pytest.raises(ValueError, match="manifest"):
        plan(src, COMMENT)
    src.with_suffix(".c2pa").unlink()
    src.write_bytes(src.read_bytes() * 2)
    with pytest.raises(ValueError, match="Additional"):
        plan(src, COMMENT)


@pytest.mark.parametrize("changes", [{FIELD: None}, {}, {"unknown": None}, {"JPEG:Comment": "new"},
                                     dict.fromkeys(["XMP-aux:LensSerialNumber"])])
def test_invalid_requests(tmp_path, changes):
    src = fixture(tmp_path / "in.jpg", segment(225, XMP + PACKET))
    with pytest.raises(ValueError):
        plan(src, changes)


def test_concurrent_publication(tmp_path):
    src = fixture(tmp_path / "in.jpg", segment(254, b"comment"))
    dest = tmp_path / "out.jpg"

    def publish(_):
        try:
            apply(src, dest, COMMENT)
            return True
        except FileExistsError:
            return False

    with ThreadPoolExecutor(4) as pool:
        assert sum(pool.map(publish, range(8))) == 1
    assert set(tmp_path.iterdir()) == {src, dest}


def test_failed_verification_cleans_temp(tmp_path, monkeypatch):
    src = fixture(tmp_path / "in.jpg", segment(254, b"comment"))
    monkeypatch.setattr("photometaclean.core.edit.fingerprint", lambda data: sha256(data).hexdigest())
    with pytest.raises(ValueError, match="integrity"):
        apply(src, tmp_path / "out.jpg", COMMENT)
    assert list(tmp_path.iterdir()) == [src]


def test_iptc_and_hdr_metadata_are_byte_exact(tmp_path):
    iptc = b"Photoshop 3.0\0" + b"8BIM\x04\x04\0\0\0\0\0\x08\x1c\x02\x78\x00\x03abc"
    hdr = PACKET.replace(b'i:DigitalSourceType', b'xmlns:h="http://ns.adobe.com/hdr-gain-map/1.0/" h:Version="1.0" i:DigitalSourceType')
    src = fixture(tmp_path / "input.jpg", segment(237, iptc), segment(225, XMP + hdr), segment(254, b"private"))
    dest = tmp_path / "copy.jpg"
    apply(src, dest, COMMENT)
    assert iptc in dest.read_bytes() and hdr in dest.read_bytes()


def test_nested_claim_is_protected(tmp_path):
    nested = PACKET.replace(b"<r:Description", b"<r:Description><r:Description").replace(
        b"</r:RDF>", b"</r:Description></r:RDF>")
    src = fixture(tmp_path / "claim.jpg", segment(225, XMP + nested))
    with pytest.raises(ValueError, match="Nested"):
        plan(src, {FIELD: None}, "original and history")


def test_dji_named_subject_privacy_preserves_hdr_and_origin(tmp_path):
    field = "XMP-aux:SerialNumber"
    local_name = field.split(":")[1]
    serial = f" a:{local_name}='synthetic'".encode()
    packet = PACKET.replace(b"<r:Description", b"""<r:Description r:about='DJI Meta Data'
 xmlns:h='http://ns.adobe.com/hdr-gain-map/1.0/' h:Version='1.0'
 xmlns:a='http://ns.adobe.com/exif/1.0/aux/'""" + serial)
    src = fixture(tmp_path / "dji.jpg", segment(225, XMP + packet))
    original = src.read_bytes()
    dest = tmp_path / "reviewed.jpg"
    changes = {field: None}
    preview = plan(src, changes)
    audit = apply(src, dest, changes, reviewed=preview)
    assert audit["changes"] == [dict(field="XMP-aux:SerialNumber", before="synthetic",
                                     after=None, offset=original.index(serial), length=len(serial))]
    assert dest.read_bytes() == original.replace(serial, b" " * len(serial), 1)
    assert fingerprint(dest.read_bytes()) == fingerprint(original)
    assert src.read_bytes() == original
    with pytest.raises(ValueError, match="unrelated"):
        plan(src, {FIELD: None}, "camera original and edit log")


@pytest.mark.parametrize("element", [
    b"<i:DigitalSourceType>urn:example:E&#xE9;</i:DigitalSourceType>",
    b'<i:DigitalSourceType r:resource="urn:example:E&#xE9;"/>',
])
def test_reviewed_element_property_only_blanks_selected_bytes(tmp_path, element):
    packet = PACKET.replace(b'i:DigitalSourceType="declared" />',
                            b'>' + element + b'</r:Description>')
    src = fixture(tmp_path / "claim.jpg", segment(225, XMP + packet))
    original = src.read_bytes()
    dest = tmp_path / "reviewed.jpg"
    evidence = "owner's camera original and edit log"
    with pytest.raises(ValueError, match="evidence"):
        plan(src, {FIELD: None})
    preview = plan(src, {FIELD: None}, evidence)
    result = apply(src, dest, {FIELD: None}, evidence, reviewed=preview)
    assert result["evidence"] == evidence
    assert result["changes"] == preview["changes"] == [
        dict(field=FIELD, before="urn:example:Eé", after=None,
             offset=original.index(element), length=len(element))]
    assert src.read_bytes() == original
    assert dest.read_bytes() == original.replace(element, b" " * len(element), 1)
    assert fingerprint(dest.read_bytes()) == fingerprint(original)


@pytest.mark.parametrize("protection", ["APP11", "sidecar", "remote"])
def test_element_edit_respects_provenance(tmp_path, protection):
    body = b'<i:DigitalSourceType r:resource="declared"/>'
    if protection == "remote":
        body += b'<d:provenance xmlns:d="http://purl.org/dc/terms/">https://example.invalid/store</d:provenance>'
    packet = PACKET.replace(b'i:DigitalSourceType="declared" />', b">" + body + b"</r:Description>")
    extra = [segment(225, XMP + packet)]
    if protection == "APP11":
        extra.append(segment(235, b"JUMBF"))
    src = fixture(tmp_path / "claim.jpg", *extra)
    if protection == "sidecar":
        src.with_suffix(".c2pa").write_bytes(b"manifest")
    dest = tmp_path / "copy.jpg"
    original = src.read_bytes()
    with pytest.raises(ValueError, match="provenance|manifest"):
        apply(src, dest, {FIELD: None}, "owner's camera original and edit log")
    assert not dest.exists()
    assert src.read_bytes() == original


@pytest.mark.parametrize("identifier,length,allowed", [
    (0x0425, 16, True), (0x03ED, 16, True), (0x0425, 15, False), (0x0424, 16, False)])
def test_photoshop_resource_list(tmp_path, identifier, length, allowed):
    def resource(key, value):
        return (b"8BIM" + key.to_bytes(2, "big") + b"\x01r" +
                len(value).to_bytes(4, "big") + value + b"\0" * (len(value) % 2))

    app13 = segment(237, b"Photoshop 3.0\0" + resource(0x0404, b"\x1c\x02\x78\0\x02ab")
                    + resource(identifier, bytes(length)))
    src = fixture(tmp_path / "photo.jpg", app13, segment(254, b"note"))
    dest = tmp_path / "copy.jpg"
    if allowed:
        apply(src, dest, COMMENT)
        assert dest.read_bytes() == src.read_bytes().replace(b"\xff\xfe\0\x06note", b"\xff\xfe\0\x06    ")
    else:
        with pytest.raises(ValueError):
            apply(src, dest, COMMENT)
        assert not dest.exists()
