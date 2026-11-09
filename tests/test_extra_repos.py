"""A Model whose Engine also loads an extra repo, such as a tokenizer: one `voxx install` fetches both."""

import json

import pytest
from conftest import FAKE_EXTRA_REVISION, FAKE_FILES, assert_error
from test_clone import write_recording

TOKENIZER = "voxx-test/fake-tokenizer"
NARRATION = {"language": "zh", "voice": "me", "lines": [{"id": "intro", "text": "这是一个新的发送流程。"}]}


@pytest.fixture
def recording(tmp_path):
    return write_recording(tmp_path / "me.wav")


def snapshot_dir(home, revision=FAKE_EXTRA_REVISION):
    return home / "hf-cache" / "models--voxx-test--fake-tokenizer" / "snapshots" / revision


def installed_ids(voxx):
    return {m["id"] for m in voxx("models", "--installed").result["data"]["models"]}


def test_install_downloads_the_extra_repo_with_the_model(voxx):
    run = voxx("install", "fake-clone-extra")

    assert run.exit_code == 0, run.result
    data = run.result["data"]
    assert data["size_bytes"] == 8192
    assert data["extra_repos"] == [{"repo": TOKENIZER, "revision": FAKE_EXTRA_REVISION, "size_bytes": 4096,
                                    "path": str(snapshot_dir(voxx.home))}]
    for name, content in FAKE_FILES.items():
        assert (voxx.home / "models" / "fake-clone-extra" / name).read_bytes() == content
        assert (snapshot_dir(voxx.home) / name).read_bytes() == content
    # Only the files the Engine loads.
    assert not (snapshot_dir(voxx.home) / "README.md").exists()
    manifest = json.loads((voxx.home / "models" / "fake-clone-extra" / "voxx-install.json").read_text())
    assert [(e["repo"], e["revision"]) for e in manifest["extra_repos"]] == [(TOKENIZER, FAKE_EXTRA_REVISION)]
    assert installed_ids(voxx) == {"fake-clone-extra"}


def test_installing_again_downloads_nothing_and_reports_the_recorded_revision(voxx, hub):
    first = voxx("install", "fake-clone-extra").result["data"]
    hub.requests.clear()

    again = voxx("install", "fake-clone-extra").result["data"]

    assert again == {**first, "already_installed": True}
    assert hub.requests == []


def test_the_engine_finds_the_extra_repo_offline(installed, recording, write_narration, tmp_path):
    assert installed("voice", "add", "me", "--ref", recording, "--model", "fake-clone-extra").exit_code == 0

    run = installed("narrate", write_narration(NARRATION), "--out", tmp_path / "out")

    assert run.exit_code == 0, run.result
    assert {line["model"] for line in run.result["data"]["narration"]["lines"]} == {"fake-clone-extra"}


def test_a_model_whose_extra_repo_lost_a_file_is_not_installed(installed, hub, recording, write_narration, tmp_path):
    assert installed("voice", "add", "me", "--ref", recording, "--model", "fake-clone-extra").exit_code == 0
    (snapshot_dir(installed.home) / "model.safetensors").unlink()

    assert "fake-clone-extra" not in installed_ids(installed)
    error = assert_error(installed("narrate", write_narration(NARRATION), "--out", tmp_path / "out"), 3,
                         "model_not_installed")
    assert [m["model"] for m in error["details"]["missing"]] == ["fake-clone-extra"]
    assert error["details"]["total_bytes"] == 8192
    assert "extra repo" in error["hint"]

    hub.requests.clear()
    run = installed("install", "fake-clone-extra")

    assert run.exit_code == 0, run.result
    assert run.result["data"]["already_installed"] is False
    # Only the missing file is downloaded again.
    assert [r.path for r in hub.requests if "/resolve/" in r.path] == [
        f"/{TOKENIZER}/resolve/{FAKE_EXTRA_REVISION}/model.safetensors"]
    assert "fake-clone-extra" in installed_ids(installed)


def test_the_extra_repo_is_installed_at_its_current_revision_whatever_its_size(voxx, hub):
    newer = "1" * 40
    hub.repos[TOKENIZER, newer] = {"config.json": b'{"model_type": "fake", "v": 2}', "model.safetensors": bytes(5000)}
    hub.main[TOKENIZER] = newer

    run = voxx("install", "fake-clone-extra")

    assert run.exit_code == 0, run.result
    assert [(e["revision"], e["size_bytes"]) for e in run.result["data"]["extra_repos"]] == [(newer, 5030)]
    assert run.result["data"]["size_bytes"] == 4096 + 5030
    assert (snapshot_dir(voxx.home, newer) / "model.safetensors").read_bytes() == bytes(5000)
    assert installed_ids(voxx) == {"fake-clone-extra"}


def test_an_interrupted_extra_repo_download_resumes_where_it_stopped(installed, hub):
    (snapshot_dir(installed.home) / "model.safetensors").unlink()
    hub.requests.clear()
    hub.cut_after["model.safetensors"] = 500
    assert_error(installed("install", "fake-clone-extra"), 1, "download_failed")
    assert "fake-clone-extra" not in installed_ids(installed)

    assert installed("install", "fake-clone-extra").exit_code == 0

    assert (snapshot_dir(installed.home) / "model.safetensors").read_bytes() == FAKE_FILES["model.safetensors"]
    assert [r.range for r in hub.requests if "/resolve/" in r.path] == [None, "bytes=500-"]
    assert "fake-clone-extra" in installed_ids(installed)


def test_models_and_doctor_name_the_extra_repos_before_install(voxx):
    model = next(m for m in voxx("models").result["data"]["models"] if m["id"] == "fake-clone-extra")

    assert model["size_bytes"] == 8192
    assert model["extra_repos"] == [{"repo": TOKENIZER, "size_bytes": 4096,
                                     "license": {"id": "Apache-2.0", "url": "https://huggingface.co/voxx-test/fake-tokenizer"}}]
    doctor = voxx("doctor", env={"VOXX_TEST_PLATFORM": "Darwin arm64"}).result["data"]
    summary = next(m for m in doctor["models"]["not_installed"] if m["model"] == "fake-clone-extra")
    assert summary["size_bytes"] == 8192
    assert summary["extra_repos"] == [{"repo": TOKENIZER, "size_bytes": 4096, "license": "Apache-2.0",
                                       "license_url": "https://huggingface.co/voxx-test/fake-tokenizer"}]
