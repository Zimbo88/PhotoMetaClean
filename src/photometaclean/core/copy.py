"""Create independently verified file copies without replacing existing files."""
import hashlib
import os
from pathlib import Path
import shutil
import stat
import tempfile

from photometaclean.core.publish import publish_new
from .review import destination_path


def digest_file(path):
    with path.open("rb") as stream:
        return hashlib.file_digest(stream, "sha256").hexdigest()


def copy_exact(source, destination, expected=None):
    source, target = Path(source), destination_path(destination)
    source_stat = source.lstat()
    if not stat.S_ISREG(source_stat.st_mode) or source.resolve() != source.absolute():
        raise ValueError("A regular source file is required")
    target.parent.mkdir(parents=True, exist_ok=True)
    temp = None
    try:
        digest = hashlib.sha256()
        with source.open("rb") as src, tempfile.NamedTemporaryFile(dir=target.parent, delete=False) as out:
            temp = Path(out.name)
            if not os.path.samestat(source_stat, os.fstat(src.fileno())):
                raise ValueError("Source file changed")
            for block in iter(lambda: src.read(1024 * 1024), b""):
                out.write(block)
                digest.update(block)
            out.flush()
            os.fsync(out.fileno())
        actual = digest.hexdigest()
        if (expected and actual != expected) or digest_file(temp) != actual or digest_file(source) != actual:
            raise ValueError("Copy verification failed or source changed")
        os.utime(temp, ns=(source_stat.st_atime_ns, source_stat.st_mtime_ns))
        publish_new(temp, target)
        return dict(copy_only=True, source_sha256=actual, output_sha256=actual, destination=str(target))
    finally:
        if temp:
            temp.unlink(missing_ok=True)


def mirror_directories(source, output, *, exclude=None, stopped=lambda: False):
    """Retain empty folders and check space for one complete copy before writing photos."""
    from .batch import walk_tree
    required_bytes = 0
    for parent, names in walk_tree(Path(source), True, exclude or output, delivery=True):
        if stopped():
            return
        target = output / parent.relative_to(source)
        if target.resolve() != target:
            raise ValueError("Linked output directory")
        target.mkdir(parents=True, exist_ok=True)
        for name in names:
            if stopped():
                return
            path = parent / name
            info = path.lstat()
            if stat.S_ISREG(info.st_mode):
                required_bytes += info.st_size
    if not stopped() and required_bytes > shutil.disk_usage(output).free:
        raise OSError("Zu wenig Platz für den vollständigen Kundenordner / Not enough space for the complete customer folder")
