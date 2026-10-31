"""Files and directories: writing so a reader never sees a half-written file, and finding where a path would live."""

import shutil
import tempfile
from contextlib import contextmanager
from pathlib import Path


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
