import hashlib

from PIL import Image, PngImagePlugin
import pytest

from photometaclean.core.patch import patch_file
from photometaclean.core.review import apply_reviewed, review
from photometaclean.formats.history import HISTORY, signed_edit
from photometaclean.formats.share import EXPORT, XMP, clean_packet, recovered_digest
from test_hdr_edit import jpeg, segment
import test_image_formats as raster_samples

XML = b"""<rdf:RDF xmlns:rdf="http://www.w3.org/1999/02/22-rdf-syntax-ns#"><rdf:Description
 xmlns:mm="http://ns.adobe.com/xap/1.0/mm/" xmlns:c="http://ns.adobe.com/camera-raw-settings/1.0/"
 xmlns:a="http://ns.adobe.com/exif/1.0/aux/" a:Lens="fixture-camera" c:HDREditMode="1"
 c:Exposure2012="+0.55"><mm:History><rdf:Seq><rdf:li rdf:parseType="Resource"
 xmlns:e="http://ns.adobe.com/xap/1.0/sType/ResourceEvent#" e:action="saved"
 e:softwareAgent="Photoshop"/></rdf:Seq></mm:History>
 <c:Look rdf:parseType="Resource" c:Exposure2012="keep-look"/>
 </rdf:Description></rdf:RDF>"""


def test_xml_history_default_and_subjects():
    assert clean_packet(XML) == (XML, [])
    out, fields = clean_packet(XML, history=True, clean_ai=False)
    assert b"+0.55" not in out and b"Photoshop" not in out
    assert b"fixture-camera" in out and b"keep-look" in out and b'HDREditMode="1"' in out
    assert fields == ["crs:Exposure2012", "xmpMM:History"]
    foreign = XML.replace(b'<rdf:Description', b'<rdf:Description rdf:about="urn:other-image"')
    assert clean_packet(foreign, history=True, clean_ai=False) == (foreign, [])


@pytest.mark.parametrize("suffix", [".jpg", ".png", ".apng", ".tif", ".webp", ".avif"])
def test_history_readback_and_recovery(tmp_path, monkeypatch, suffix):
    src, dest = (tmp_path/(stem+suffix) for stem in ("input", "output"))
    if suffix == ".jpg":
        pic = jpeg((18, 9), "green")
        src.write_bytes(pic[:2]+segment(0xe1, XMP+XML)+pic[2:])
    else:
        monkeypatch.setattr(raster_samples, "XMP", XML)
        raster_samples.generate(src, raster_samples.SERIAL, animated=suffix == ".apng")
    original = src.read_bytes()
    result = apply_reviewed(review(src, {HISTORY: None}, "Export requested"), dest)
    audit = result["audit"]
    assert audit["integrity_before"] == audit["integrity_after"]
    assert recovered_digest(dest.read_bytes(), audit["recovery"]) == hashlib.sha256(original).hexdigest()
    assert src.read_bytes() == original and b"+0.55" not in dest.read_bytes() and b"keep-look" in dest.read_bytes()
    assert b"fixture-camera" in dest.read_bytes()
    assert result["postcheck"]["state"] == "clear"


@pytest.mark.parametrize("compressed", [True, False])
def test_png_software_and_recipe_together(tmp_path, compressed):
    src, dest = tmp_path/"in.png", tmp_path/"folder/out.png"
    meta = PngImagePlugin.PngInfo()
    meta.add_text("Software", "Adobe Photoshop", zip=compressed)
    meta.add_text("parameters","Steps: 12, Sampler: Euler, CFG scale: 7, Seed: 42")
    meta.add_text("Author","Attribution")
    Image.new("RGB",(11,14)).save(src,pnginfo=meta)
    r = patch_file(src,dest,{HISTORY,"PNG:Parameters"},True,camera_confirmation="Export requested")
    assert r.get("audit"),r.get("reason")
    assert r["postcheck"]["state"] == "clear"
    with Image.open(dest) as im:
        assert im.info.get("Author") == "Attribution" and "Software" not in im.info and "parameters" not in im.info


def test_only_active_signed_edit_enables_combined_export():
    def assertion(op):
        return {"assertions":[{"label":"c2pa.actions.v2","data":{"actions":[{"action":op}]}}]}
    store={"active_manifest":"current","manifests":{"current":assertion("c2pa.created"), "prior":assertion("c2pa.cropped")}}
    assert not signed_edit({"manifest":store})
    store["active_manifest"]="prior"
    assert signed_edit({"manifest":store})


def test_combined_raster_export_checks_source_label_and_workflow(tmp_path):
    src, dest = tmp_path/"source.png", tmp_path/"out.png"
    metadata = PngImagePlugin.PngInfo()
    packet = XML.replace(b'c:Exposure2012="+0.55"', b'xmlns:i="http://iptc.org/std/Iptc4xmpExt/2008-02-29/" '
                         b'i:DigitalSourceType="http://cv.iptc.org/newscodes/digitalsourcetype/compositeWithTrainedAlgorithmicMedia" '
                         b'c:Exposure2012="+0.55"')
    metadata.add_itxt("XML:com.adobe.xmp",packet.decode())
    metadata.add_text("parameters","Steps: 20, Sampler: Euler, CFG scale: 7, Seed: 42")
    Image.new("RGB",(11,14)).save(src,pnginfo=metadata)
    result = patch_file(src,dest,{HISTORY, EXPORT, "PNG:Parameters"},True,camera_confirmation="Combined export requested")
    assert result["postcheck"]["state"] == "clear"
    data = dest.read_bytes()
    assert b"compositeWithTrainedAlgorithmicMedia" not in data and b"Steps:" not in data and b"+0.55" not in data
    assert b"fixture-camera" in data and b"keep-look" in data
