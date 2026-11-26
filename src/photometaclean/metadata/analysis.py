"""Read-only local evidence extraction. All return values are private."""
import hashlib
import io
import json
import re
import subprocess
import sys
import stat
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

from pi_heif import HeifImagePlugin  # registers the HEIC/HEIF decoder
from photometaclean.formats.limits import MAX_BYTES as MAX_INPUT, MAX_PIXELS, MAX_FRAME_PIXELS
from PIL import Image, ImageOps, UnidentifiedImageError


# Per-file budgets apply equally to research and user inputs.
MAX_STREAM_PIXELS = MAX_FRAME_PIXELS
MAX_BLOCKS = 32_768
MAX_METADATA = 16 * 1024**2


def exif_metadata(path, *, expand_xmp_lists=False):
    command = ["exiftool"]
    if getattr(sys, "frozen", False):
        vendor = Path(sys._MEIPASS) / "tools"
        command = ([str(vendor / "exiftool.exe")] if sys.platform == "win32"
                   else ["/usr/bin/perl", str(vendor / "exiftool")])
    args = [*command, "-config", "", "-j", "-struct", "-a", "-u", "-ee",
            "-G1:3:4", "-n"]
    if expand_xmp_lists:
        args.append("-m")
    # Perl's Windows argv goes through the legacy code page. ExifTool's UTF-8
    # argument-file reader accepts the complete filename through standard input.
    windows = sys.platform == "win32"
    if windows:
        args.extend(("-charset", "filename=UTF8", "-@", "-"))
    else:
        args.append(str(path))
    # A windowed Windows app should keep the metadata helper in the background.
    with subprocess.Popen(args, stdin=subprocess.PIPE if windows else subprocess.DEVNULL,
                          stdout=subprocess.PIPE, stderr=subprocess.PIPE,
                          creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0)) as proc:
        if windows:
            with proc.stdin as filenames:
                filenames.write(str(path.absolute()).encode("utf8") + b"\n")

        def collect(stream, limit):
            data = stream.read(limit + 1)
            if len(data) > limit:
                proc.kill()
                raise ValueError("ExifTool output exceeds analysis limit")
            return data

        with ThreadPoolExecutor(2) as pool:
            output = pool.submit(collect, proc.stdout, MAX_METADATA)
            errors = pool.submit(collect, proc.stderr, 64 * 1024)
            try:
                proc.wait(timeout=180)
            except subprocess.TimeoutExpired:
                proc.kill()
                raise
            raw = output.result()
            stderr = errors.result().decode(errors="replace").strip()
    records = json.loads(raw or b"[]")
    if not records or not isinstance(records[0], dict):
        raise ValueError(stderr or "ExifTool returned no metadata record")
    metadata = records[0]
    warnings = [stderr] if stderr else []
    for key, value in metadata.items():
        name = key.rsplit(":", 1)[-1]
        if name == "Error":
            raise ValueError(f"ExifTool: {value}")
        if name == "Warning":
            warnings.append(str(value))
    if proc.returncode:
        raise ValueError(f"ExifTool exited {proc.returncode}: {' '.join(warnings)}")
    if not expand_xmp_lists and warnings and all(
        re.fullmatch(r"\[Minor\] Extracted only 1000 [^\n]+ items\. Ignore minor errors to extract all", w, re.I)
        for w in warnings
    ):
        # Use the same byte and time budgets for the full list. Other warnings from
        # the first read must remain visible and never trigger the relaxed second read.
        return exif_metadata(path, expand_xmp_lists=True)
    return metadata, "\n".join(warnings)


def pixel_digest(image):
    """Hash raw rows in order without allocating a second full pixel buffer."""
    sha = hashlib.sha256()
    rows = max(1, 1024 * 1024 // max(1, image.width * 4))
    for top in range(0, image.height, rows):
        with image.crop((0, top, image.width, min(image.height, top + rows))) as strip:
            sha.update(strip.tobytes())
    return sha.hexdigest()


def digest(data):
    return hashlib.sha256(data).hexdigest()


PREFIXES = {
    b"Exif\0\0": "EXIF", b"http://ns.adobe.com/xap/1.0/\0": "XMP",
    b"http://ns.adobe.com/xmp/extension/\0": "Extended XMP",
    b"ICC_PROFILE\0": "ICC", b"MPF\0": "MPF", b"Photoshop 3.0\0": "Photoshop/IPTC",
    b"urn:iso:std:iso:ts:21496:-1\0": "ISO 21496-1",
    b"JP": "JUMBF fragment", b"JFIF\0": "JFIF", b"Adobe": "Adobe APP14",
}


def jpeg_blocks(data):
    """Walk every contiguous JPEG codestream, including progressive scans."""
    pos = 0
    blocks = []
    frame = 0

    def record(kind, start, end):
        if len(blocks) >= MAX_BLOCKS:
            raise ValueError("JPEG segment count exceeds analysis limit")
        blocks.append(dict(kind=kind, offset=start, size=end-start,
                           frame=frame, sha256=digest(memoryview(data)[start:end])))

    while data[pos:pos+2] == b'\xff\xd8':
        frame += 1
        record("SOI", pos, pos+2)
        pos += 2
        while True:
            start = pos
            if data[pos:pos+1] != b'\xff':
                raise ValueError(f"Missing JPEG marker at {pos}")
            while data[pos:pos+1] == b'\xff':
                pos += 1
            marker = data[pos]
            pos += 1
            if marker == 0xd9:
                record("EOI", start, pos)
                break
            length = int.from_bytes(data[pos:pos+2], 'big')
            end = pos + length
            if length < 2 or end > len(data):
                raise ValueError(f"Invalid segment length at {start}")
            kind = f"FF{marker:02X}"
            if 0xe0 <= marker <= 0xef:
                label = next((v for k,v in PREFIXES.items() if data.startswith(k,pos+2)), "unknown")
                kind = f"APP{marker-0xe0} {label}"
            record(kind,start,end)
            pos = end
            if marker == 0xda:
                match = re.compile(b'\xff+(?![\xff\x00\xd0-\xd7])').search(data,pos)
                if match is None:
                    raise ValueError("Unterminated JPEG scan")
                record("scan",pos,match.start())
                pos = match.start()
    if pos < len(data):
        record("trailing bytes",pos,len(data))
    return blocks


def analyze(path: Path) -> dict:
    path = Path(path).resolve(strict=True)

    info = path.stat()
    if not stat.S_ISREG(info.st_mode) or info.st_size > MAX_INPUT:
        raise ValueError("Analysis requires a regular file of at most 1 GiB")
    with path.open("rb") as stream:
        data = stream.read(min(info.st_size + 1, MAX_INPUT + 1))
    if len(data) != info.st_size:
        raise ValueError("File size changed during analysis")
    metadata, warnings = exif_metadata(path)
    from .editing import editing_signals
    result = dict(path=str(path), size=len(data), sha256=digest(data), metadata=metadata,
                  editing_signals=editing_signals(metadata),
                  warnings=warnings, blocks=[], frames=[])
    if data.startswith(b'\xff\xd8'):
        result["blocks"] = jpeg_blocks(data)
    try:
        with Image.open(path) as im:
            result.update(format=im.format, resolution=list(im.size))
            count = getattr(im, "n_frames", 1)
            if count > 512:
                raise ValueError("Frame count exceeds analysis limit")
            remaining = MAX_FRAME_PIXELS
            for index in range(count):
                im.seek(index)
                remaining -= im.width * im.height
                if remaining < 0 or im.width * im.height > MAX_PIXELS:
                    raise ValueError("Decoded pixel count exceeds analysis limit")
                result["frames"].append(dict(size=list(im.size), mode=im.mode,
                    pixels=pixel_digest(im),icc=digest(im.info["icc_profile"]) if im.info.get("icc_profile") else None))
                if index == 0:
                    oriented = ImageOps.exif_transpose(im) if im.getexif().get(274, 1) != 1 else im
                    thumb = oriented.convert("L").resize((16,16),Image.Resampling.LANCZOS)
                    del oriented
                    result["fingerprint"] = thumb.tobytes().hex()
            result["pixel_status"] = "decoded"
    except UnidentifiedImageError:
        result["pixel_status"] = "metadata only / nur Metadaten"
        result["format"] = next((value for key, value in metadata.items() if key.endswith(":FileType")), path.suffix)
    starts = [b["offset"] for b in result["blocks"] if b["kind"] == "SOI"]
    ends = [b["offset"]+b["size"] for b in result["blocks"] if b["kind"] == "EOI"]
    result["codestreams"] = []
    if len(starts) > 128:
        raise ValueError("Codestream count exceeds analysis limit")
    stream_pixels = 0
    for start, end in zip(starts, ends, strict=True):
        with Image.open(io.BytesIO(data[start:end])) as frame:
            stream_pixels += frame.width * frame.height
            if frame.width * frame.height > MAX_PIXELS or stream_pixels > MAX_STREAM_PIXELS:
                raise ValueError("Decoded codestream pixel count exceeds analysis limit")
            result["codestreams"].append(dict(offset=start,size=end-start,
                resolution=list(frame.size),mode=frame.mode,pixels=pixel_digest(frame)))
    from .provenance import inspect_provenance
    inspect_provenance(result, path, data)
    return result
