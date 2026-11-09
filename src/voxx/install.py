"""`voxx install`: the only command that downloads anything (ADR 0003)."""

import fnmatch
import hashlib
import http.client
import json
import os
import re
import shutil
import time
import urllib.error
import urllib.parse
import urllib.request
from datetime import datetime, timezone
from pathlib import PurePosixPath

from voxx.files import nearest_existing
from voxx.models import (INSTALL_MANIFEST, extra_repo_dir, extra_repo_snapshot, find_model, is_installed, model_dir,
                         read_manifest)
from voxx.output import VoxxError, progress

DEFAULT_ENDPOINT = "https://huggingface.co"
CHUNK = 1 << 20
TIMEOUT = 60
# Raised while talking to the hub, as opposed to writing files locally.
NETWORK_ERRORS = (urllib.error.URLError, http.client.HTTPException, ConnectionError, TimeoutError)
RETRY_HINT = "Run the same `voxx install` again: it resumes where it stopped."
HUB_HINT = "Check HF_ENDPOINT: the hub it names is not serving this repo as Hugging Face does."
# Test-only: the free bytes the disk check sees.
FREE_BYTES_ENV = "VOXX_TEST_FREE_BYTES"


def install(model_id):
    model = find_model(model_id)
    path = model_dir(model)
    if is_installed(model):
        return _result(model, path, read_manifest(model), already_installed=True)

    partial = _partial_dir(model, path)
    files = _model_files(model)
    extras = [_extra_repo_files(model, extra) for extra in model.extra_repos]
    # One download for the Model and its extra repos, so the disk check and the progress cover them all.
    downloads = [(model.repo, model.revision, partial, f) for f in files]
    downloads += [(repo, revision, extra_repo_snapshot(repo, revision), f) for repo, revision, wanted in extras
                  for f in wanted]
    total = sum(f["size"] for *_, f in downloads)
    _check_free_space(partial, total - sum(_downloaded(folder, f) for _, _, folder, f in downloads))
    progress("download_started", model=model.id, files=len(downloads), bytes=total)
    for repo, revision, folder, file in downloads:
        _download(model, repo, revision, file, folder)
    for repo, revision, _ in extras:
        _point_main(repo, revision)
    manifest = {"model": model.id, "repo": model.repo, "revision": model.revision, "files": _sizes(files),
                "extra_repos": [{"repo": repo, "revision": revision, "files": _sizes(wanted)}
                                for repo, revision, wanted in extras],
                "installed_at": datetime.now(timezone.utc).isoformat(timespec="seconds")}
    (partial / INSTALL_MANIFEST).write_text(json.dumps(manifest, indent=2) + "\n", encoding="utf-8")
    if path.exists():
        shutil.rmtree(path)
    partial.replace(path)
    progress("download_done", model=model.id, path=str(path))
    return _result(model, path, manifest, already_installed=False)


def _partial_dir(model, path):
    """Where this install downloads the Model's own files before moving them into place."""
    # Downloads land in <id>.<revision>.partial/: a verified file under its own name, an unfinished one as
    # <name>.download. Naming the revision keeps an interrupted install of another revision from being reused.
    partial = path.with_name(f"{path.name}.{model.revision}.partial")
    stale_name = re.compile(re.escape(path.name) + r"\.[0-9a-f]{40}\.partial")
    for stale in path.parent.glob(f"{path.name}.*.partial"):
        if stale != partial and stale_name.fullmatch(stale.name):
            shutil.rmtree(stale)
    manifest = read_manifest(model)
    if manifest is not None and manifest.get("revision") == model.revision:
        # Only an extra repo is missing: keep the Model's own files, which the download then skips.
        if partial.exists():
            shutil.rmtree(partial)
        path.replace(partial)
    return partial


def _model_files(model):
    """The files of the Model's own repo at its pinned revision, which must add up to the size voxx verified."""
    files = _repo_files(model, model.repo, model.revision)
    total = sum(f["size"] for f in files)
    if total != model.repo_bytes:
        raise _invalid_repo(model, model.repo, model.revision,
                            f"The hub lists {total} bytes for {model.id}, not the {model.repo_bytes} voxx verified.")
    return files


def _extra_repo_files(model, extra):
    """An extra repo's current revision and the files of it the Engine loads. It is not pinned, so their size may
    differ from the one voxx checked (ADR 0003)."""
    revision = _main_revision(model, extra.repo)
    wanted = [f for f in _repo_files(model, extra.repo, revision)
              if any(fnmatch.fnmatchcase(f["path"], pattern) for pattern in extra.files)]
    if not wanted:
        raise _invalid_repo(model, extra.repo, revision,
                            f"The hub lists none of the files {model.id} loads from {extra.repo}.")
    return extra.repo, revision, wanted


def _sizes(files):
    return [{"path": f["path"], "size": f["size"]} for f in files]


def _result(model, path, manifest, already_installed):
    # The sizes installed, as the manifest records them: an extra repo's can differ from the one voxx checked, which
    # Model.download_bytes adds up.
    extras = [{"repo": e["repo"], "revision": e["revision"], "size_bytes": sum(f["size"] for f in e["files"]),
               "path": str(extra_repo_snapshot(e["repo"], e["revision"]))}
              for e in manifest.get("extra_repos", [])]
    result = {"model": model.id, "path": str(path), "size_bytes": model.repo_bytes + sum(e["size_bytes"] for e in extras),
              "already_installed": already_installed}
    return {**result, "extra_repos": extras} if extras else result


def _point_main(repo, revision):
    """Makes the downloaded snapshot the one Hugging Face's loader finds offline, then drops any other: a Model that
    recorded another revision of this repo counts as not installed until `voxx install` catches it up."""
    refs = extra_repo_dir(repo) / "refs"
    refs.mkdir(parents=True, exist_ok=True)
    # Without a trailing newline: huggingface_hub reads the ref as it is.
    (refs / "main.tmp").write_text(revision, encoding="utf-8")
    (refs / "main.tmp").replace(refs / "main")
    for snapshot in (extra_repo_dir(repo) / "snapshots").iterdir():
        if snapshot.name != revision:
            shutil.rmtree(snapshot)


def _endpoint():
    return (os.environ.get("HF_ENDPOINT") or DEFAULT_ENDPOINT).rstrip("/")


def _url(*parts):
    return _endpoint() + "/" + "/".join(urllib.parse.quote(p) for p in parts)


def _main_revision(model, repo):
    """The commit a repo's main branch points to now, from the hub's revision API."""
    url = _url("api", "models", repo, "revision", "main")
    try:
        with urllib.request.urlopen(url, timeout=TIMEOUT) as r:
            info = json.load(r)
    except NETWORK_ERRORS as e:
        raise _download_failed(model, url, e)
    except ValueError:
        info = None
    revision = info.get("sha") if isinstance(info, dict) else None
    if not (isinstance(revision, str) and re.fullmatch(r"[0-9a-f]{40}", revision)):
        raise _invalid_repo(model, repo, "main", f"The hub does not say which commit of {repo} is current.")
    return revision


def _repo_files(model, repo, revision):
    """The files of a repo at a revision, from the hub's tree API."""
    url = _url("api", "models", repo, "tree", revision) + "?recursive=true"
    try:
        with urllib.request.urlopen(url, timeout=TIMEOUT) as r:
            entries = json.load(r)
    except NETWORK_ERRORS as e:
        raise _download_failed(model, url, e)
    except ValueError:
        raise _invalid_repo(model, repo, revision, f"The hub's file list for {repo} is not JSON.")
    if not isinstance(entries, list) or not all(isinstance(e, dict) for e in entries):
        raise _invalid_repo(model, repo, revision, f"The hub's file list for {repo} is not a list of files.")
    files = [e for e in entries if e.get("type") == "file"]
    for file in files:
        lfs = file.get("lfs", {"oid": ""})
        if not (isinstance(file.get("path"), str) and isinstance(file.get("size"), int) and isinstance(file.get("oid"), str)
                and isinstance(lfs, dict) and isinstance(lfs.get("oid"), str)):
            raise _invalid_repo(model, repo, revision, f"The hub lists a file of {repo} without a path, size and checksum.")
        name = PurePosixPath(file["path"])
        if name.is_absolute() or ".." in name.parts or not name.parts:
            raise _invalid_repo(model, repo, revision, f"The hub lists an unsafe file path {file['path']!r} for {repo}.")
    return files


def _invalid_repo(model, repo, revision, message):
    return VoxxError("invalid_repo", message, HUB_HINT, {"model": model.id, "repo": repo, "revision": revision})


def _check_free_space(partial, required):
    existing = nearest_existing(partial)
    free = int(os.environ[FREE_BYTES_ENV]) if FREE_BYTES_ENV in os.environ else shutil.disk_usage(existing).free
    if required > free:
        raise VoxxError("insufficient_disk_space", f"Installing needs {required} more bytes but only {free} are free.",
                        "Free up disk space, or set VOXX_HOME to a volume with room, then install again.",
                        {"required_bytes": required, "free_bytes": free, "path": str(existing)})


def _downloaded(folder, file):
    """Bytes of this file already on disk from an earlier attempt."""
    if (folder / file["path"]).exists():
        return file["size"]
    unfinished = folder / (file["path"] + ".download")
    return unfinished.stat().st_size if unfinished.exists() else 0


def _checksum(file):
    """A hasher and the digest it must reach: SHA-256 for large (LFS) files, the git blob SHA-1 for the rest."""
    if "lfs" in file:
        return hashlib.sha256(), file["lfs"]["oid"]
    return hashlib.sha1(b"blob %d\0" % file["size"]), file["oid"]


def _download(model, repo, revision, file, folder):
    target = folder / file["path"]
    if target.exists():
        return
    unfinished = target.with_name(target.name + ".download")
    unfinished.parent.mkdir(parents=True, exist_ok=True)
    hasher, expected = _checksum(file)
    done = 0
    if unfinished.exists():
        with open(unfinished, "rb") as f:
            while chunk := f.read(CHUNK):
                hasher.update(chunk)
                done += len(chunk)
    url = _url(repo, "resolve", revision, file["path"])
    if done < file["size"]:
        request = urllib.request.Request(url, headers={"Range": f"bytes={done}-"} if done else {})
        try:
            with urllib.request.urlopen(request, timeout=TIMEOUT) as r:
                if done and r.status != 206:  # The hub ignored the Range: start over.
                    hasher, expected = _checksum(file)
                    done = 0
                with open(unfinished, "ab" if done else "wb") as out:
                    last = time.monotonic()
                    while chunk := r.read(CHUNK):
                        out.write(chunk)
                        hasher.update(chunk)
                        done += len(chunk)
                        if time.monotonic() - last >= 1:
                            last = time.monotonic()
                            progress("download_progress", model=model.id, repo=repo, file=file["path"],
                                     bytes_done=done, bytes_total=file["size"])
        except NETWORK_ERRORS as e:
            raise _download_failed(model, url, e)
        if done < file["size"]:  # The connection closed early; keep what arrived for the next attempt.
            raise _download_failed(model, url, ConnectionError(f"the hub sent {done} of {file['size']} bytes"))
    if done != file["size"] or hasher.hexdigest() != expected:
        unfinished.unlink()
        raise VoxxError("download_corrupt", f"{file['path']} of {repo} did not match the hub's checksum.",
                        "The file was deleted; " + RETRY_HINT,
                        {"model": model.id, "repo": repo, "file": file["path"], "bytes": done,
                         "expected_bytes": file["size"]})
    unfinished.replace(target)
    progress("download_progress", model=model.id, repo=repo, file=file["path"], bytes_done=done,
             bytes_total=file["size"])


def _download_failed(model, url, error):
    details = {"model": model.id, "url": url, "reason": str(getattr(error, "reason", error))}
    if isinstance(error, urllib.error.HTTPError):
        details["status"] = error.code
    return VoxxError("download_failed", f"Downloading {model.id} failed: {details['reason']}.",
                     f"Check the network, or set HF_ENDPOINT to a Hugging Face mirror. {RETRY_HINT}", details)
