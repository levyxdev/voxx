import json

import pytest
from conftest import FAKE_FILES, assert_error

from voxx.models import FAKE_MODEL


def installed_ids(voxx):
    return {m["id"] for m in voxx("models", "--installed").result["data"]["models"]}


def test_install_downloads_the_model_into_voxx_home(voxx):
    run = voxx("install", "fake-tts")

    assert run.exit_code == 0
    path = voxx.home / "models" / "fake-tts"
    assert run.result["data"] == {"model": "fake-tts", "path": str(path), "size_bytes": 4096, "already_installed": False}
    for name, content in FAKE_FILES.items():
        assert (path / name).read_bytes() == content
    assert installed_ids(voxx) == {"fake-tts"}


def test_install_reports_download_progress_on_stderr(voxx):
    run = voxx("install", "fake-tts")

    finished = {e["file"]: e for e in run.events if e["event"] == "download_progress" and e["bytes_done"] == e["bytes_total"]}
    assert set(finished) == set(FAKE_FILES)
    assert run.events[-1]["event"] == "download_done"


def test_installing_again_downloads_nothing(voxx, hub):
    voxx("install", "fake-tts")
    hub.requests.clear()

    run = voxx("install", "fake-tts")

    assert run.exit_code == 0
    assert run.result["data"]["already_installed"] is True
    assert hub.requests == []


def test_an_unknown_model_is_an_argument_error(voxx, hub):
    error = assert_error(voxx("install", "nobody-tts"), 2, "unknown_model")

    assert "voxcpm2" in error["details"]["known_models"]
    assert hub.requests == []


def test_an_interrupted_install_resumes_where_it_stopped(voxx, hub):
    hub.cut_after["model.safetensors"] = 1000

    error = assert_error(voxx("install", "fake-tts"), 1, "download_failed")
    assert installed_ids(voxx) == set()
    assert "again" in error["hint"]

    run = voxx("install", "fake-tts")

    assert run.exit_code == 0
    assert (voxx.home / "models" / "fake-tts" / "model.safetensors").read_bytes() == FAKE_FILES["model.safetensors"]
    resumed = [r for r in hub.requests if r.path.endswith("/model.safetensors")][-1]
    assert resumed.range == "bytes=1000-"
    assert sum(r.path.endswith("/config.json") for r in hub.requests) == 1


def test_a_resumed_install_starts_over_when_the_hub_ignores_the_range(voxx, hub):
    hub.cut_after["model.safetensors"] = 1000
    voxx("install", "fake-tts")
    hub.ignore_range = True

    assert voxx("install", "fake-tts").exit_code == 0
    assert (voxx.home / "models" / "fake-tts" / "model.safetensors").read_bytes() == FAKE_FILES["model.safetensors"]


def test_a_leftover_download_of_another_revision_is_cleaned_up(voxx):
    models = voxx.home / "models"
    stale = models / "fake-tts.fedcba9876543210fedcba9876543210fedcba98.partial"
    stale.mkdir(parents=True)
    (stale / "model.safetensors").write_bytes(b"weights of another revision")
    # A Model whose id merely starts with "fake-tts." keeps its download.
    other = models / "fake-tts.v2.fedcba9876543210fedcba9876543210fedcba98.partial"
    other.mkdir()

    assert voxx("install", "fake-tts").exit_code == 0
    assert (models / "fake-tts" / "model.safetensors").read_bytes() == FAKE_FILES["model.safetensors"]
    assert not stale.exists()
    assert other.exists()


def test_a_model_installed_at_another_revision_is_not_installed(installed):
    manifest = installed.home / "models" / "fake-tts" / "voxx-install.json"
    manifest.write_text(json.dumps({**json.loads(manifest.read_text()), "revision": "f" * 40}))

    assert installed_ids(installed) == {"fake-tts-small", "fake-asr", "fake-aligner", "fake-clone", "fake-clone-alt"}
    assert installed("install", "fake-tts").result["data"]["already_installed"] is False
    assert installed_ids(installed) == {"fake-tts", "fake-tts-small", "fake-asr", "fake-aligner", "fake-clone", "fake-clone-alt"}


@pytest.mark.parametrize("size", [len(FAKE_FILES["config.json"]) + 1, 10**18])
def test_a_hub_that_does_not_serve_the_pinned_files_is_refused(voxx, hub, size):
    hub.reported_sizes["config.json"] = size

    error = assert_error(voxx("install", "fake-tts"), 1, "invalid_repo")

    assert "HF_ENDPOINT" in error["hint"]
    assert not any("/resolve/" in r.path for r in hub.requests)
    assert installed_ids(voxx) == set()


@pytest.mark.parametrize("tree", [
    b"<html>Mirror maintenance</html>",
    b'{"error": "busy"}',
    b'["config.json"]',
    b'[{"type": "file", "path": "config.json"}]',
    b'[{"type": "file", "path": "../config.json", "size": 4096, "oid": "0"}]',
    b'[{"type": "file", "path": "model.safetensors", "size": 4096, "oid": "0", "lfs": {"size": 4096}}]',
])
def test_a_hub_that_answers_with_a_malformed_file_list_is_refused(voxx, hub, tree):
    hub.tree_body = tree

    assert_error(voxx("install", "fake-tts"), 1, "invalid_repo")


def test_a_corrupt_download_is_not_installed(voxx, hub):
    hub.corrupt.add("model.safetensors")

    error = assert_error(voxx("install", "fake-tts"), 1, "download_corrupt")

    assert error["details"]["file"] == "model.safetensors"
    assert installed_ids(voxx) == set()
    hub.corrupt.clear()
    assert voxx("install", "fake-tts").exit_code == 0
    assert (voxx.home / "models" / "fake-tts" / "model.safetensors").read_bytes() == FAKE_FILES["model.safetensors"]


def test_install_checks_free_disk_space_before_downloading(voxx, hub):
    error = assert_error(voxx("install", "fake-tts", env={"VOXX_TEST_FREE_BYTES": "4095"}), 1, "insufficient_disk_space")

    assert error["details"]["required_bytes"] == 4096
    assert error["details"]["free_bytes"] == 4095
    assert not any("/resolve/" in r.path for r in hub.requests)


def test_an_unreachable_hub_is_a_download_failure(voxx):
    error = assert_error(voxx("install", "fake-tts", env={"HF_ENDPOINT": "http://127.0.0.1:9"}), 1, "download_failed")

    assert "HF_ENDPOINT" in error["hint"]
