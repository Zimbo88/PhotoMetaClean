"""Publish a complete sibling temporary file atomically without replacing any entry."""
import ctypes
import errno
import os
import sys


def publish_new(temp, target):
    if os.name == "nt":
        os.rename(temp, target)
        return
    try:
        os.link(temp, target)
        return
    except OSError as exc:
        if exc.errno not in {errno.EPERM, errno.EOPNOTSUPP, errno.ENOSYS, errno.EMLINK}:
            raise
    rename_new(temp, target)


def rename_new(temp, target):
    """Atomically move a complete file or directory into an unoccupied name."""
    if os.name == "nt":
        os.rename(temp, target)
        return
    # FAT/exFAT have no hard links. Each supported OS has a no-replace rename.
    libc = ctypes.CDLL(None, use_errno=True)
    source, dest = os.fsencode(temp), os.fsencode(target)
    if sys.platform == "darwin" and hasattr(libc, "renamex_np"):
        result = libc.renamex_np(source, dest, 4)  # RENAME_EXCL
    elif sys.platform.startswith("linux") and hasattr(libc, "renameat2"):
        result = libc.renameat2(-100, source, -100, dest, 1)  # AT_FDCWD, RENAME_NOREPLACE
    else:
        raise OSError(errno.ENOTSUP, "Atomic no-replace publication unavailable", str(target))
    if result:
        code = ctypes.get_errno()
        raise OSError(code, os.strerror(code), str(target))
