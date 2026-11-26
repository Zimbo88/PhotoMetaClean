"""Independent scan, color-profile and decoded-sample checks for each image."""
import hashlib
import io

from PIL import Image

from photometaclean.formats.limits import MAX_PIXELS, MAX_FRAME_PIXELS

from photometaclean.formats.jpeg import ISO_GAIN_MAP, MPF, image_streams


def _image_fingerprint(data, stream, normalize_index=False):
    scan = hashlib.sha256()
    descriptors = []
    for part in stream.parts:
        if part.marker == 0:
            scan.update((part.end - part.start).to_bytes(8, "big"))
            scan.update(memoryview(data)[part.start:part.end])
        if part.marker == 0xe2 and data.startswith((MPF, ISO_GAIN_MAP), part.payload, part.end):
            raw = data[part.start:part.end]
            if normalize_index and data.startswith(MPF, part.payload):
                # Index validity is checked independently against both codestream boundaries.
                raw = bytearray(raw)
                origin = part.payload + len(MPF) - part.start
                for pos in (origin + 54, origin + 74):
                    raw[pos:pos+4] = bytes(4)
            descriptors.append(hashlib.sha256(raw).hexdigest())
    pixels = hashlib.sha256()
    with Image.open(io.BytesIO(data[stream.start:stream.end])) as image:
        if image.width * image.height > MAX_PIXELS:
            raise ValueError("Decoded image exceeds the supported safety limit")
        for top in range(0, image.height, 128):
            pixels.update(image.crop((0, top, image.width, min(top + 128, image.height))).tobytes())
        return dict(size=list(image.size), mode=image.mode, scans=scan.hexdigest(),
                    pixels=pixels.hexdigest(), icc=hashlib.sha256(image.info.get("icc_profile") or b"").hexdigest(),
                    descriptors=descriptors)


def fingerprint(data, *, allow_provenance=False, normalize_index=False):
    primary, *others = image_streams(data, allow_provenance=allow_provenance)
    result = _image_fingerprint(data, primary, normalize_index and not primary.fixed_layout)
    if primary.fixed_layout:
        result["primary_bytes"] = primary.end
    for auxiliary in others:
        result["gain_map"] = _image_fingerprint(data, auxiliary)
        result["gain_map"]["stream_sha256"] = hashlib.sha256(memoryview(data)[auxiliary.start:]).hexdigest()
    return result

def raster_fingerprint(data, compressed):
    from photometaclean.metadata.analysis import pixel_digest

    frames = []
    total = 0
    with Image.open(io.BytesIO(data)) as image:
        for index in range(getattr(image, "n_frames", 1)):
            if index >= 512:
                raise ValueError("Frame count exceeds verification limit")
            image.seek(index)
            count = image.width * image.height
            total += count
            if count > MAX_PIXELS or total > MAX_FRAME_PIXELS:
                raise ValueError("Decoded pixel count exceeds verification limit")
            # Resolve indexed colors, transparency and compositing for display.
            with image.convert("RGBA") as rgba:
                frames.append(dict(size=list(image.size), mode=image.mode,
                                   samples=pixel_digest(image), rgba=pixel_digest(rgba),
                                   duration=image.info.get("duration")))
        return dict(frames=frames, compressed=compressed, loop=image.info.get("loop"),
                    icc=hashlib.sha256(image.info.get("icc_profile") or b"").hexdigest())
