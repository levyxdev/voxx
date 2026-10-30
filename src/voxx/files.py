"""Files and directories: writing so a reader never sees a half-written file, and finding where a path would live."""

from contextlib import contextmanager


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


def nearest_existing(path):
    """`path` if it exists, else its closest existing parent: where its disk space would come from."""
    return next(p for p in (path, *path.parents) if p.exists())
