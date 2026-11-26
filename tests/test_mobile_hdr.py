import hashlib
import struct

import pytest

from photometaclean.core.edit import IPTC_DIGEST_WARNING, apply
from photometaclean.core.patch import patch_file
from photometaclean.formats.jpeg import image_streams
from photometaclean.formats.share import EXPORT, XMP, jpeg_changes
from test_hdr_edit import jpeg, segment

RDF = b'http://www.w3.org/1999/02/22-rdf-syntax-ns#'
LABEL = b' xmlns:i="http://iptc.org/std/Iptc4xmpExt/2008-02-29/" i:DigitalSourceType="trainedAlgorithmicMedia"'


def packet(attrs=b"", children=b""):
    return segment(0xe1, XMP + b'<r:RDF xmlns:r="' + RDF + b'"><r:Description' + attrs + b'>'
                   + children + b'</r:Description></r:RDF>')


def mobile(apple=False, displacement=0, extra=b"", aux_meta=None):
    main = jpeg((24, 16), "teal")
    gain = jpeg((6, 4), "gray")
    if aux_meta is None:
        if apple:
            aux_meta = packet(b' xmlns:a="http://ns.apple.com/pixeldatainfo/1.0/" xmlns:h="http://ns.apple.com/HDRGainMap/1.0/"',
                              b'<a:AuxiliaryImageType>urn:com:apple:photo:2020:aux:hdrgainmap</a:AuxiliaryImageType>'
                              b'<h:HDRGainMapVersion>131072</h:HDRGainMapVersion>')
        else:
            aux_meta = packet(b' xmlns:h="http://ns.adobe.com/hdr-gain-map/1.0/" h:Version="1.0"')
    gain = gain[:2] + aux_meta + gain[2:]
    metadata = packet(LABEL) + extra
    first_size = len(main) + len(metadata) + 90
    origin = 2 + len(metadata) + 8
    order = ">" if apple else "<"
    index = b"MPF\0" + (b"MM" if apple else b"II")
    index += struct.pack(order + "HIH", 42, 8, 3)
    index += struct.pack(order + "HHI4s", 0xb000, 7, 4, b"0100")
    index += struct.pack(order + "HHII", 0xb001, 4, 1, 2)
    index += struct.pack(order + "HHIII", 0xb002, 7, 32, 50, 0)
    index += struct.pack(order + "IIIHH", 0x030000, first_size + (12 if apple else -12), 0, 0, 0)
    index += struct.pack(order + "IIIHH", 0, len(gain), first_size-origin+displacement, 0, 0)
    return main[:2] + metadata + segment(0xe2, index) + main[2:] + gain


@pytest.mark.parametrize("apple", [True, False])
def test_mobile_marker_preserves_every_byte_outside_property(tmp_path, apple):
    raw = mobile(apple)
    source, copy = tmp_path/"image.jpg", tmp_path/"out.jpg"
    source.write_bytes(raw)
    audit = apply(source, copy, {EXPORT: None}, evidence="Controlled input")
    field = b' i:DigitalSourceType="trainedAlgorithmicMedia"'
    assert copy.read_bytes() == raw.replace(field, b' ' * len(field))
    assert source.read_bytes() == raw
    assert audit["integrity_before"] == audit["integrity_after"]
    primary, gain = image_streams(raw)
    assert audit["integrity_after"]["primary_bytes"] == primary.end
    assert audit["integrity_after"]["gain_map"]["stream_sha256"] == hashlib.sha256(raw[gain.start:]).hexdigest()


@pytest.mark.parametrize("raw", [
    mobile(displacement=1), mobile(aux_meta=packet()), mobile()+b"trailer",
    mobile(extra=segment(0xeb, b'JP')), mobile(aux_meta=packet(b' xmlns:h="http://example.org/" h:Version="1.0"')),
    mobile(aux_meta=packet(b' xmlns:h="http://ns.adobe.com/hdr-gain-map/1.0/" h:Version="1.0"'
                           b' xmlns:d="http://purl.org/dc/terms/" d:provenance="external"')),
])
def test_ambiguous_or_protected_mobile_layout_is_refused(raw):
    with pytest.raises(ValueError):
        jpeg_changes(raw)


@pytest.mark.parametrize("include_comment", [False, True])
def test_existing_iptc_warning_allows_only_one_independent_xmp_label(tmp_path, include_comment):
    # Two Photoshop image resources: legacy IPTC and a deliberately stale digest.
    def resource(tag, content):
        return b'8BIM' + struct.pack('>H', tag) + b'\0\0' + struct.pack('>I', len(content)) + content + bytes(len(content) % 2)
    iptc = b'\x1c\x02\x19\x00\x07fixture'
    photoshop = segment(0xed, b'Photoshop 3.0\0' + resource(0x0404, iptc) + resource(0x0425, b'A'*16))
    image = jpeg((20, 12), "navy")
    raw = image[:2] + photoshop + packet(LABEL) + segment(0xfe,b'test comment') + image[2:]
    src = tmp_path/'source.jpg'
    dst = tmp_path/'delivery'/'copy.jpg'
    src.write_bytes(raw)
    rules = {EXPORT, "JPEG:Comment"} if include_comment else {EXPORT}
    result = patch_file(src, dst, rules, True, camera_confirmation="Synthetic test")
    assert src.read_bytes() == raw
    if include_comment:
        assert result["copy_only"] and dst.read_bytes() == raw
    else:
        assert result["audit"]["existing_warning"] == IPTC_DIGEST_WARNING
        assert result["postcheck"]["state"] == "incomplete" and result["postcheck"]["issue"] == IPTC_DIGEST_WARNING
        assert photoshop in dst.read_bytes() and b'trainedAlgorithmicMedia' not in dst.read_bytes()
