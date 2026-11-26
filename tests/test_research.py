import io
import sys
from pathlib import Path

from PIL import Image

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))
import research
from photometaclean.metadata.analysis import analyze, jpeg_blocks


def jpeg(color):
    buffer = io.BytesIO()
    Image.new("RGB",(32,20),color).save(buffer,"JPEG",progressive=True)
    return buffer.getvalue()


def test_two_codestreams_and_trailer(tmp_path):
    data = jpeg("red")+jpeg("green")+b"other"
    path = tmp_path/"öffentliche Probe.jpg"
    path.write_bytes(data)
    r = analyze(path)
    assert r["metadata"] and r["resolution"] == [32,20]
    assert len(r["codestreams"]) == 2
    assert r["codestreams"][0]["pixels"] != r["codestreams"][1]["pixels"]
    assert r["blocks"][-1]["kind"] == "trailing bytes"
    assert sum(b["size"] for b in r["blocks"]) == len(data)
    assert path.read_bytes() == data


def test_ambiguous_candidates(tmp_path):
    path = tmp_path/"sample.jpg"
    path.write_bytes(jpeg("red"))
    a = analyze(path)
    pair = research.compare([a],[dict(a,path="after/sample.jpg")])
    assert pair[0]["status"] == "matched"
    pairs = research.compare([a,dict(a,path="other/sample.jpg")],[dict(a,path="after/sample.jpg")])
    assert all(p["status"]=="uncertain" for p in pairs)
    assert all("metadata_diff" in p for p in pairs)


def test_truncated_segment():
    import pytest
    with pytest.raises(ValueError):
        jpeg_blocks(b"\xff\xd8\xff\xe1\xff\xff")
