import base64
import hashlib
import struct

import pytest
from PIL import Image

from photometaclean.core.patch import patch_file
from photometaclean.formats.jpeg import image_streams
from photometaclean.formats.share import EXPORT, EXT, XMP, clean_packet, jpeg_changes
from photometaclean.verification.jpeg import fingerprint
from test_hdr_edit import indexed, jpeg, segment

RDF = b'http://www.w3.org/1999/02/22-rdf-syntax-ns#'
HEAD = b'<r:RDF xmlns:r="'+RDF+b'"><r:Description xmlns:c="http://ns.adobe.com/camera-raw-settings/1.0/" '
TAIL = b'</r:Description></r:RDF>'


def archive_roundtrip(result, data, original):
    recovered = bytearray(data)
    for item in reversed(result["audit"]["recovery"]):
        pos = item["output_offset"]
        recovered[pos:pos+item["output_length"]] = base64.b64decode(item["original_base64"], validate=True)
    assert recovered == original


def test_extended_xmp_spanning_two_segments_keeps_other_retouches(tmp_path):
    packet = (HEAD+b'><c:RetouchAreas><r:Seq><r:li><r:Description c:fill_method="firefly"/></r:li>'
              b'<r:li><r:Description c:fill_method="clone"/></r:li></r:Seq></c:RetouchAreas>'+TAIL)
    guid = hashlib.md5(packet, usedforsecurity=False).hexdigest().upper().encode()
    master = HEAD+b'xmlns:n="http://ns.adobe.com/xmp/note/" n:HasExtendedXMP="'+guid+b'">'+TAIL
    fragments = b"".join(segment(0xe1, EXT+guid+struct.pack(">II",len(packet),offset)+part)
                         for offset,part in ((0,packet[:180]),(180,packet[180:])))
    data = jpeg((12, 8),"red")
    src = tmp_path / "image.jpg"
    original = data[:2]+segment(0xe1,XMP+master)+fragments+data[2:]
    src.write_bytes(original)
    # Inspect the packet directly as well. ExifTool reports custom RDF prefixes differently by version.
    revised, fields = clean_packet(packet)
    assert b"firefly" not in revised and b"clone" in revised and fields == ["Firefly RetouchAreas"]
    pieces = jpeg_changes(original)
    output = bytearray(original)
    for a,b,content,_ in reversed(pieces):
        output[a:b] = content
    assert guid not in output and b"firefly" not in output and b"clone" in output
    assert fingerprint(bytes(output)) == fingerprint(original)
    with pytest.raises(ValueError, match="digest mismatch"):
        jpeg_changes(original.replace(b'"clone"', b'"clonE"'))


@pytest.mark.parametrize("order",[">","<"])
def test_gain_map_index_and_auxiliary_image_after_manifest_detachment(order):
    original = indexed(order)
    desc = b"jumd"+bytes.fromhex("6332706100110010800000aa00389b71")+b"\x03c2pa\0"
    box = struct.pack(">I",len(desc)+4)+desc
    meta = segment(0xeb,b"JP"+struct.pack(">HI",1,1)+struct.pack(">I4s",len(box)+8,b"jumb")+box)
    signed = original[:2]+meta+original[2:]
    a,b,raw,_ = jpeg_changes(signed)[0]
    restored_layout = signed[:a]+raw+signed[b:]
    assert restored_layout == original
    assert fingerprint(signed,allow_provenance=True,normalize_index=True) == fingerprint(original,normalize_index=True)
    assert len(image_streams(restored_layout)) == 2


def test_nongenerative_camera_credentials_and_source_are_preserved(tmp_path):
    p = tmp_path / "camera.jpg"
    Image.new("RGB",(15,10)).save(p)
    dest=tmp_path/"out.jpg"
    result=patch_file(p,dest,{EXPORT},True,camera_confirmation="owned")
    assert result.get("copy_only") and p.read_bytes()==dest.read_bytes()


def test_generator_in_simple_exif_software_and_user_comment(tmp_path):
    exif = Image.Exif()
    exif[305] = "ComfyUI"
    exif[0x8769] = {37510: b"ASCII\0\0\0Steps: 20, Sampler: Euler, CFG scale: 7, Seed: 42"}
    src, dst = tmp_path/"color.jpg", tmp_path/"copy.jpg"
    Image.new("RGB",(8,9)).save(src, exif=exif)
    original = src.read_bytes()
    result = patch_file(src,dst,{EXPORT}, False, camera_confirmation="own file")
    assert result.get("audit"), result.get("reason")
    assert not result["postcheck"]["signals"]
    assert b"ComfyUI" not in dst.read_bytes() and b"Steps:" not in dst.read_bytes()
    archive_roundtrip(result,dst.read_bytes(),original)


@pytest.mark.parametrize("after_index", [False, True])
def test_relocates_both_index_fields_as_needed(after_index):
    orig = indexed()
    origin = orig.index(b"MPF\0") + 4
    primary, aux = image_streams(orig)
    pos = origin + 82 if after_index else 2
    desc = b"jumd" + bytes.fromhex("6332706100110010800000aa00389b71") + b"\x03c2pa\0"
    box = struct.pack(">I", len(desc)+4) + desc
    app = segment(0xeb, b"JP" + struct.pack(">HI",1,1) + struct.pack(">I4s",len(box)+8,b"jumb") + box)
    signed = bytearray(orig[:pos] + app + orig[pos:])
    shifted = origin if after_index else origin+len(app)
    struct.pack_into(">I", signed, shifted+54, primary.end+len(app))
    struct.pack_into(">I", signed, shifted+74, aux.start+len(app)-shifted)
    changes = jpeg_changes(bytes(signed))
    for a,b,replacement,_ in reversed(changes):
        signed[a:b] = replacement
    assert bytes(signed) == orig
