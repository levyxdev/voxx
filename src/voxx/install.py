"""`voxx install`: the only command that downloads anything (ADR 0003)."""

import hashlib
import http.client
import json
import os
import shutil
import time
import urllib.error
import urllib.parse
import urllib.request
from datetime import datetime, timezone
from pathlib import PurePosixPath

from voxx.models import INSTALL_MANIFEST, find_model, is_installed, model_dir
from voxx.output import VoxxError, progress

DEFAULT_ENDPOINT = "https://huggingface.co"
CHUNK = 1 << 20
TIMEOUT = 60
# Raised while talking to the hub, as opposed to writing files locally.
NETWORK_ERRORS = (urllib.error.URLError, http.client.HTTPException, ConnectionError, TimeoutError)
RETRY_HINT = "Run the same `voxx install` again: it resumes where it stopped."


def install(model_id):
    model = find_model(model_id)
    path = model_dir(model)
    if is_installed(model):
        return _result(model, path, already_installed=True)

    # Downloads land in <id>.partial/: a verified file under its own name, an unfinished one as <name>.download.
    partial = path.with_name(path.name + ".partial")
    files = _tree(model)
    _check_free_space(partial, sum(f["size"] - _downloaded(partial, f) for f in files))
    progress("download_started", model=model.id, files=len(files), bytes=sum(f["size"] for f in files))
    for file in files:
        _download(model, file, partial)
    manifest = {"model": model.id, "repo": model.repo, "revision": model.revision,
                "files": [{"path": f["path"], "size": f["size"]} for f in files],
                "installed_at": datetime.now(timezone.utc).isoformat(timespec="seconds")}
    (partial / INSTALL_MANIFEST).write_text(json.dumps(manifest, indent=2) + "\n", encoding="utf-8")
    if path.exists():
        shutil.rmtree(path)
    partial.replace(path)
    progress("download_done", model=model.id, path=str(path))
    return _result(model, path, already_installed=False)


def _result(model, path, already_installed):
    return {"model": model.id, "path": str(path), "size_bytes": model.size_bytes, "already_installed": already_installed}


def _endpoint():
    return (os.environ.get("HF_ENDPOINT") or DEFAULT_ENDPOINT).rstrip("/")


def _url(*parts):
    return _endpoint() + "/" + "/".join(urllib.parse.quote(p) for p in parts)


def _tree(model):
    url = _url("api", "models", model.repo, "tree", model.revision) + "?recursive=true"
    try:
        with urllib.request.urlopen(url, timeout=TIMEOUT) as r:
            entries = json.load(r)
    except NETWORK_ERRORS as e:
        raise _download_failed(model, url, e)
    files = [e for e in entries if e.get("type") == "file"]
    for file in files:
        name = PurePosixPath(file["path"])
        if name.is_absolute() or ".." in name.parts or not name.parts:
            raise VoxxError("invalid_repo", f"The repo of {model.id} lists an unsafe file path {file['path']!r}.",
                            "Check HF_ENDPOINT: the hub it names is not serving this repo correctly.",
                            {"model": model.id, "repo": model.repo, "path": file["path"]})
    return files


def _check_free_space(partial, required):
    existing = next(p for p in (partial, *partial.parents) if p.exists())
    free = shutil.disk_usage(existing).free
    if required > free:
        raise VoxxError("insufficient_disk_space", f"Installing needs {required} more bytes but only {free} are free.",
                        "Free up disk space, or set VOXX_HOME to a volume with room, then install again.",
                        {"required_bytes": required, "free_bytes": free, "path": str(existing)})


def _downloaded(partial, file):
    """Bytes of this file already on disk from an earlier attempt."""
    if (partial / file["path"]).exists():
        return file["size"]
    unfinished = partial / (file["path"] + ".download")
    return unfinished.stat().st_size if unfinished.exists() else 0


def _hasher(file):
    """The hub's checksum: SHA-256 for large (LFS) files, the git blob SHA-1 for the rest."""
    if "lfs" in file:
        return hashlib.sha256(), file["lfs"]["oid"]
    return hashlib.sha1(b"blob %d\0" % file["size"]), file["oid"]


def _download(model, file, partial):
    target = partial / file["path"]
    if target.exists():
        return
    unfinished = target.with_name(target.name + ".download")
    unfinished.parent.mkdir(parents=True, exist_ok=True)
    hasher, expected = _hasher(file)
    done = 0
    if unfinished.exists():
        with open(unfinished, "rb") as f:
            while chunk := f.read(CHUNK):
                hasher.update(chunk)
                done += len(chunk)
    url = _url(model.repo, "resolve", model.revision, file["path"])
    if done < file["size"]:
        request = urllib.request.Request(url, headers={"Range": f"bytes={done}-"} if done else {})
        try:
            with urllib.request.urlopen(request, timeout=TIMEOUT) as r:
                if done and r.status != 206:  # The hub ignored the Range: start over.
                    hasher, expected = _hasher(file)
                    done = 0
                with open(unfinished, "ab" if done else "wb") as out:
                    last = time.monotonic()
                    while chunk := r.read(CHUNK):
                        out.write(chunk)
                        hasher.update(chunk)
                        done += len(chunk)
                        if time.monotonic() - last >= 1:
                            last = time.monotonic()
                            progress("download_progress", model=model.id, file=file["path"], bytes_done=done,
                                     bytes_total=file["size"])
        except NETWORK_ERRORS as e:
            raise _download_failed(model, url, e)
        if done < file["size"]:  # The connection closed early; keep what arrived for the next attempt.
            raise _download_failed(model, url, ConnectionError(f"the hub sent {done} of {file['size']} bytes"))
    if done != file["size"] or hasher.hexdigest() != expected:
        unfinished.unlink()
        raise VoxxError("download_corrupt", f"{file['path']} of {model.id} did not match the hub's checksum.",
                        "The file was deleted; " + RETRY_HINT,
                        {"model": model.id, "file": file["path"], "bytes": done, "expected_bytes": file["size"]})
    unfinished.replace(target)
    progress("download_progress", model=model.id, file=file["path"], bytes_done=done, bytes_total=file["size"])


def _download_failed(model, url, error):
    details = {"model": model.id, "url": url, "reason": str(getattr(error, "reason", error))}
    if isinstance(error, urllib.error.HTTPError):
        details["status"] = error.code
    return VoxxError("download_failed", f"Downloading {model.id} failed: {details['reason']}.",
                     f"Check the network, or set HF_ENDPOINT to a Hugging Face mirror. {RETRY_HINT}", details)
