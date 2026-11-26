"""Check the complete staged snapshot before publication. Requires Git and Python 3."""
import os
from pathlib import PurePosixPath
import re
import subprocess
import sys

MAX_BYTES = 4 * 1024 * 1024
PRIVATE_ROOTS = {"vorm update", "nach update", "ai ki versuch", "private", "reports", "output"}
SUFFIXES = set("""
.gif .apng .bmp .jp2 .j2k .jxl .jfif .hif .ico .svgz .jpg .jpeg .jpe .png .webp .tif .tiff .heic .heif .avif .arw .dng .nef .cr2 .cr3
.raf .orf .rw2 .xmp .exif .icc .icm .c2pa .json .csv .jsonl .tsv .zip .gz .pdf
""".split())
# Look for assignments in common ExifTool, JSON and XMP serializations.
PERSONAL = re.compile(
    r"""(?ix)(?:gps[ _]?(?:latitude|longitude|position)|(?:camera|body|lens)?[ _]?serial[ _]?number|
    ownername|cameraownername|sourcefile)["']?\s*[:=>]\s*["']?[^\s"'<>}{,]+"""
)
HOME_PATH = re.compile(r"""(?:/(?:home|Users)/|[A-Za-z]:[\\/]Users[\\/])[\w.-]+""")
PHOTO_MAGIC = (b'\xff\xd8\xff', b'\x89PNG', b'II*\0', b'MM\0*', b'RIFF')


def git(*args, data=None):
    return subprocess.run(["git", *args], input=data, stdout=subprocess.PIPE,
                          check=True).stdout


def path_reason(name):
    path = PurePosixPath(name.casefold())
    parts = path.parts
    if parts[0] in PRIVATE_ROOTS or (
        parts[0] == "research" and len(parts) > 1 and parts[1].startswith(("local", "private"))
    ):
        return "private directory"
    if path.suffix == ".svg" and path.as_posix() != "src/photometaclean/gui/photometaclean.svg":
        return "unreviewed vector image"
    if path.suffix in SUFFIXES or path.suffix.startswith(".tif"):
        return "media, sidecar or local report"
    return None


def content_reason(data):
    if data.startswith(PHOTO_MAGIC) or data[4:8] == b'ftyp' or b'\0' in data:
        return "binary payload"
    try:
        text = data.decode("utf-8")
    except UnicodeDecodeError:
        return "non-UTF-8 payload"
    if PERSONAL.search(text) or HOME_PATH.search(text):
        return "possible personal metadata"
    return None


def main():
    entries = git("ls-files", "--full-name", "--stage", "-z", "--", ":/").split(b"\0")
    failed = False
    for number, entry in enumerate(filter(None, entries), 1):
        header, raw_name = entry.split(b"\t", 1)
        mode, oid, stage = header.split()
        name = os.fsdecode(raw_name)
        reason = path_reason(name)
        if stage != b"0" or mode not in (b"100644", b"100755"):
            reason = "unmerged or non-regular entry"
        if reason is None:
            obj = oid.decode("ascii")
            if int(git("cat-file", "-s", obj)) > MAX_BYTES:
                reason = "file exceeds review limit"
            else:
                reason = content_reason(git("cat-file", "blob", obj))
        if reason:
            # CI logs may be public. Even a filename can identify a photographer.
            label = "entry " + str(number)
            if sys.stderr.isatty():
                label = ascii(name)
            print(f"Privacy guard: {label}: {reason}", file=sys.stderr)
            failed = True
    return int(failed)


if __name__ == "__main__":
    try:
        sys.exit(main())
    except (ValueError, OSError, subprocess.CalledProcessError):
        sys.exit("Privacy guard: unable to verify Git index")
