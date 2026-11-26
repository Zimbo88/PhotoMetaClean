"""Preview and publish a verified, fixed-length image metadata edit."""
from hashlib import sha256
import os
from pathlib import Path
import tempfile

from photometaclean.core.publish import publish_new
from photometaclean.formats.history import HISTORY, HISTORY_RASTERS, JPEG_EXTENSIONS, history_fields, signed_edit
from photometaclean.formats.jpeg import ISO_GAIN_MAP, MPF, image_streams, is_supported_photoshop_block
from photometaclean.formats.raster import PARSERS, inspect_raster
from photometaclean.formats.limits import MAX_BYTES
from photometaclean.formats.recipes import PNG_FIELDS
from photometaclean.formats.share import EXPORT, ai_indicators, jpeg_changes, recovery_data, recovered_digest
from photometaclean.formats.xmp import FIELDS, PRIVACY_FIELDS, SOURCE_TYPE, FieldReviewRequired, locations
from photometaclean.verification.jpeg import fingerprint

XMP = b"http://ns.adobe.com/xap/1.0/\0"
IPTC_DIGEST_WARNING = "IPTCDigest is not current. XMP may be out of sync"
ALLOWED_APP = {
    0xe0: (b"JFIF\0",),
    0xe1: (b"Exif\0\0", XMP),
    0xe2: (b"ICC_PROFILE\0", MPF, ISO_GAIN_MAP),
    0xee: (b"Adobe",),
}



def _check_sidecars(path):
    names = {path.with_suffix(".c2pa").name.casefold(), (path.name + ".c2pa").casefold()}
    if any(entry.name.casefold() in names for entry in path.parent.iterdir()):
        raise ValueError("External manifest present. Review and re-export from the original")


def _only_primary_source_label(data, changeset):
    if len(changeset) != 1:
        return False
    start, end, replacement, label = changeset[0]
    if label != "XMP · DigitalSourceType" or data[start-len(XMP):start] != XMP:
        return False
    packet = data[start:end]
    spans = locations(packet, {SOURCE_TYPE})
    if len(spans) != 1:
        return False
    _, a, b, _ = spans[0]
    return replacement == packet[:a] + b" " * (b-a) + packet[b:]


def _jpeg_edits(data, changes):
    edits = []
    comment_bytes = 0
    for stream in image_streams(data):
        seen_xmp = False
        for part in stream.parts:
            if not (0xe0 <= part.marker <= 0xef or part.marker == 0xfe):
                continue
            payload = data[part.payload:part.end]
            if part.marker == 0xfe:
                if "JPEG:Comment" in changes and payload.strip(b" "):
                    if stream.start:
                        raise ValueError("Comment in the auxiliary image requires manual review")
                    comment_bytes += len(payload)
                    if comment_bytes > 4 * 1024**2:
                        raise ValueError("Comment data exceeds audit limit")
                    edits.append(("JPEG:Comment", part.payload, part.end, payload.hex()))
                continue
            if part.marker == 0xeb or b"c2pa" in payload.lower():
                raise ValueError("Possible signed provenance. Review and re-export from the original")
            if part.marker == 0xed and is_supported_photoshop_block(payload):
                continue
            if not payload.startswith(ALLOWED_APP.get(part.marker, ())):
                raise ValueError("Unsupported metadata container. Review and re-export from the original")
            if part.marker == 0xe1 and payload.startswith(XMP):
                if seen_xmp or b"HasExtendedXMP" in payload:
                    raise ValueError("Multiple or extended XMP packets require review")
                seen_xmp = True
                offset = part.payload + len(XMP)
                for key, start, end, old in locations(payload[len(XMP):], changes.keys() & FIELDS.keys()):
                    if stream.start:
                        raise FieldReviewRequired(key, "Selected field in auxiliary image requires manual review")
                    edits.append((key, offset + start, offset + end, old))
    return edits, []


def _prepare(path, changes, evidence):
    if not isinstance(changes, dict) or not changes or set(changes) - (FIELDS.keys() | PNG_FIELDS | {EXPORT, HISTORY, "JPEG:Comment", "PNG:Comment", "GIF:Comment", "TIFF:ImageDescription"}):
        raise ValueError("Choose one or more supported metadata fields")
    if any(value is not None for value in changes.values()):
        raise ValueError("Supported changes require a null value")
    if "XMP-iptcExt:DigitalSourceType" in changes and not evidence.strip():
        raise ValueError("Document ownership and independent evidence of the incorrect declaration")
    if path.suffix.lower() not in ({".jpeg", ".jpg", ".jpe", ".jfif"} | PARSERS.keys()):
        raise ValueError("Analysis only for this format / Für dieses Format ist nur die Analyse verfügbar")
    if path.is_symlink() or not path.is_file():
        raise ValueError("Choose a regular image file")
    _check_sidecars(path)
    with path.open("rb") as source:
        size = os.fstat(source.fileno()).st_size
        if size > MAX_BYTES:
            raise ValueError("File exceeds 1 GiB edit size limit")
        data = source.read(size + 1)
    if len(data) != size:
        raise ValueError("File size changed during processing")
    suffix = path.suffix.lower()
    if HISTORY in changes and (suffix not in JPEG_EXTENSIONS | HISTORY_RASTERS or not evidence.strip()):
        raise ValueError("Choose a supported image and document the requested history removal")
    if EXPORT in changes or (HISTORY in changes and suffix in JPEG_EXTENSIONS):
        if set(changes) - (PRIVACY_FIELDS | {EXPORT, HISTORY, "JPEG:Comment"}) or suffix not in JPEG_EXTENSIONS or not evidence.strip():
            raise ValueError("Choose an authorized JPEG export and document the basis")
        from photometaclean.core.batch import analyze_one
        analysis = analyze_one(path)
        digest = sha256(data).hexdigest()
        if analysis.get("sha256") != digest or analysis.get("validation_error"):
            raise ValueError("JPEG metadata could not be verified")
        history = HISTORY in changes
        clean_ai = EXPORT in changes and (bool(ai_indicators(analysis)) or (history and signed_edit(analysis)))
        if not clean_ai and not history:
            raise ValueError("No verified, supported AI records in this image")
        clean_exif = any(s["field"].split(":")[0] in {"ExifIFD", "IFD0"} for s in analysis.get("editing_signals", ()))
        has_provenance = bool(analysis.get("manifest") or any(analysis.get("provenance_references", {}).values()))
        if not clean_ai and has_provenance:
            raise ValueError("Existing provenance protects this history / Herkunftsnachweis schützt diesen Verlauf")
        clean_exif = (clean_ai and clean_exif) or (history and "IFD0:Software" in history_fields(analysis["metadata"]))
        changeset = jpeg_changes(data, set(changes)-{EXPORT, HISTORY}, clean_exif=clean_exif,
                                 history=history, clean_ai=clean_ai, has_provenance=has_provenance)
        if not changeset:
            raise ValueError("The detected record has no supported lossless export")
        patches = [(s, e, v) for s, e, v, _ in changeset]
        out = sha256()
        for block in _output_blocks(data, patches):
            out.update(block)
        audit = dict(source=str(path), source_sha256=digest, output_sha256=out.hexdigest(),
                     evidence=evidence, signature_status=analysis.get("signature", "unchecked"),
                     changes=[dict(field=HISTORY if history else EXPORT, before=label, after=None, offset=s, length=e-s)
                              for s, e, _, label in changeset],
                     recovery=recovery_data(data, changeset))
        # DigitalSourceType exists only in XMP. A same-length edit to that
        # property cannot change the legacy IPTC block or its stored digest.
        if (not has_provenance and analysis.get("warnings") == IPTC_DIGEST_WARNING
                and _only_primary_source_label(data, changeset)):
            audit["existing_warning"] = IPTC_DIGEST_WARNING
        return data, patches, audit
    if HISTORY in changes:
        from photometaclean.core.batch import analyze_one
        initial = analyze_one(path)
        if (initial.get("sha256") != sha256(data).hexdigest() or initial.get("validation_error")
                or initial.get("manifest") or any(initial.get("provenance_references", {}).values())):
            raise ValueError("Protected or unverified editing history")
    parser = PARSERS.get(suffix)
    if parser:
        edits, checksums, _ = inspect_raster(parser, data, changes.keys())
    else:
        edits, checksums = _jpeg_edits(data, changes)
    for key in changes.keys() & FIELDS.keys():
        if sum(edit[0] == key for edit in edits) > 1:
            raise FieldReviewRequired(key, "Repeated XMP property requires manual review")
    found = {key for key, *_ in edits}
    if HISTORY in changes and "PNG:Software" in found:
        found.add(HISTORY)
    missing = sorted(set(changes) - found)
    if missing:
        raise FieldReviewRequired(missing[0], "One or more selected fields are missing or already blank")
    patches = [(start, end, b"" if key in PNG_FIELDS else b" " * (end - start))
               for key, start, end, _ in edits]
    patches.extend((offset, offset + len(value), value) for offset, value in checksums)
    patches.sort()
    output_hash = sha256()
    for block in _output_blocks(data, patches):
        output_hash.update(block)
    audit = dict(source=str(path), source_sha256=sha256(data).hexdigest(),
                 output_sha256=output_hash.hexdigest(), evidence=evidence,
                 signature_status="no embedded manifest detected; external status unknown",
                 changes=[dict(field=key, before=old, after=None, offset=start, length=end-start)
                          for key, start, end, old in edits])
    if HISTORY in changes:
        labels = {(start, end): key for key, start, end, _ in edits}
        audit["recovery"] = recovery_data(data, [(a, b, value, labels.get((a, b), "CRC"))
                                                  for a, b, value in patches])
    if checksums:
        audit["checksum_offsets"] = [offset for offset, _ in checksums]
    return data, patches, audit


def _output_blocks(data, patches):
    view = memoryview(data)
    pos = 0
    for start, end, replacement in patches:
        if start < pos or not start <= end <= len(view):
            raise ValueError("Overlapping or out-of-bounds metadata patch")
        yield view[pos:start]
        yield replacement
        pos = end
    yield view[pos:]


def _integrity(data, path, *, sharing=False, original=False):
    parser = PARSERS.get(path.suffix.lower())
    if parser is None:
        if sharing:
            return fingerprint(data, allow_provenance=original, normalize_index=True)
        return fingerprint(data)
    from photometaclean.verification.jpeg import raster_fingerprint
    return raster_fingerprint(data, inspect_raster(parser, data, set())[2])


def plan(path: Path, changes: dict, evidence: str = "") -> dict:
    data, _, audit = _prepare(Path(path), changes, evidence)
    audit["integrity_before"] = _integrity(data, path, sharing=EXPORT in changes or HISTORY in changes, original=True)
    return audit


def apply(path: Path, destination: Path, changes: dict, evidence: str = "", *, reviewed=None) -> dict:
    path, destination = Path(path), Path(destination)
    root = Path(__file__).resolve().parents[3]
    if any(destination.resolve().is_relative_to(root / name) for name in ("vorm Update", "Nach Update", "AI KI VERSUCH")):
        raise ValueError("Research directories are read-only")
    if os.path.lexists(destination):
        raise FileExistsError(destination)
    data, edited, audit = _prepare(path, changes, evidence)
    if reviewed is not None and any(reviewed.get(k) != audit[k] for k in audit):
        raise ValueError("Quelldatei oder Freigabe geändert / Source or approval changed")
    sharing = EXPORT in changes or HISTORY in changes
    before = _integrity(data, path, sharing=sharing, original=True)
    destination.parent.mkdir(parents=True, exist_ok=True)
    temp = None
    try:
        with tempfile.NamedTemporaryFile(dir=destination.parent, suffix=path.suffix, delete=False) as output:
            temp = Path(output.name)
            for block in _output_blocks(data, edited):
                output.write(block)
            del block
            output.flush()
            os.fsync(output.fileno())
        del data, edited
        persisted = temp.read_bytes()
        after = _integrity(persisted, path, sharing=sharing)
        output_digest = sha256(persisted).hexdigest()
        if sharing and recovered_digest(persisted, audit["recovery"]) != audit["source_sha256"]:
            raise ValueError("Recovery data does not reproduce the signed original")
        del persisted
        if output_digest != audit["output_sha256"] or after != before:
            raise ValueError("Output integrity check failed")
        if sharing:
            from photometaclean.core.batch import analyze_one
            clean = analyze_one(temp)
            if clean.get("warnings") and clean["warnings"] != audit.get("existing_warning"):
                raise ValueError("Metadatenprüfung offen / Metadata warning: " + str(clean["warnings"]))
            if (clean.get("sha256") != output_digest or clean.get("validation_error") or clean.get("manifest")
                    or any(clean.get("provenance_references", {}).values())
                    or (EXPORT in changes and ai_indicators(clean))
                    or (HISTORY in changes and history_fields(clean.get("metadata", {})))):
                raise ValueError("Saved image still has selected records or could not be checked")
            _check_sidecars(destination)
        with path.open("rb") as source:
            digest = sha256()
            for chunk in iter(lambda: source.read(1024 * 1024), b""):
                digest.update(chunk)
        if digest.hexdigest() != audit["source_sha256"]:
            raise ValueError("Source changed during processing")
        _check_sidecars(path)
        publish_new(temp, destination)
    finally:
        if temp is not None:
            temp.unlink(missing_ok=True)
    return dict(audit, destination=str(destination), integrity_before=before, integrity_after=after)
