"""Files and directories: writing so a reader never sees a half-written file, and finding where a path would live."""

import errno
import os
import shutil
import tempfile
from contextlib import contextmanager
from pathlib import Path

from voxx.output import USAGE, VoxxError


@contextmanager
def replacing(path):
    """Yields a temporary path next to `path`; on success it replaces `path`, on failure it is removed."""
    partial = path.with_name(path.name + ".partial")
    try:
        yield partial
    except BaseException:
        partial.unlink(missing_ok=True)
        raise
    partial.replace(path)


@contextmanager
def staging(directory):
    """Yields a new hidden directory inside `directory`, so a file written there moves into `directory` with one atomic
    rename; on the way out it is removed with whatever is still in it."""
    stage = Path(tempfile.mkdtemp(prefix=".voxx-staging-", dir=directory))
    try:
        yield stage
    finally:
        shutil.rmtree(stage, ignore_errors=True)


def nearest_existing(path):
    """`path` if it exists, else its closest existing parent: where its disk space would come from."""
    return next(p for p in (path, *path.parents) if p.exists())


def writable_out(out):
    """Creates the output directory `out` if missing, and fails unless voxx can write in it."""
    try:
        out.mkdir(parents=True, exist_ok=True)
        if not os.access(out, os.W_OK):
            raise PermissionError(errno.EACCES, "Permission denied")
    except OSError as e:
        raise VoxxError("invalid_out", f"Cannot use {out} as the output directory: {e.strerror}.",
                        "Pass a writable directory for --out.", {"out": str(out)}, USAGE)
