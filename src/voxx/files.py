"""Writing files so a reader never sees a half-written one."""

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
