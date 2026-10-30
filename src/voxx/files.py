"""Writing files so a reader never sees a half-written one."""

from contextlib import contextmanager


@contextmanager
def replacing(path):
    """Yields a temporary path next to `path`; on success it replaces `path`."""
    partial = path.with_name(path.name + ".partial")
    yield partial
    partial.replace(path)
