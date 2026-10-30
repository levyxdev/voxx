from conftest import FAKE_FILES


def assert_error(run, exit_code, code):
    assert run.exit_code == exit_code
    assert run.result["ok"] is False
    error = run.result["error"]
    assert error["code"] == code
    assert error["message"] and error["hint"]
    return error


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
    assert not any(r.path.endswith("/config.json") for r in hub.requests[-2:])


def test_a_corrupt_download_is_not_installed(voxx, hub):
    hub.corrupt.add("model.safetensors")

    error = assert_error(voxx("install", "fake-tts"), 1, "download_corrupt")

    assert error["details"]["file"] == "model.safetensors"
    assert installed_ids(voxx) == set()
    hub.corrupt.clear()
    assert voxx("install", "fake-tts").exit_code == 0
    assert (voxx.home / "models" / "fake-tts" / "model.safetensors").read_bytes() == FAKE_FILES["model.safetensors"]


def test_install_checks_free_disk_space_before_downloading(voxx, hub):
    hub.reported_sizes["model.safetensors"] = 10**18

    error = assert_error(voxx("install", "fake-tts"), 1, "insufficient_disk_space")

    assert error["details"]["required_bytes"] > error["details"]["free_bytes"]
    assert not any("/resolve/" in r.path for r in hub.requests)


def test_an_unreachable_hub_is_a_download_failure(voxx):
    error = assert_error(voxx("install", "fake-tts", env={"HF_ENDPOINT": "http://127.0.0.1:9"}), 1, "download_failed")

    assert "HF_ENDPOINT" in error["hint"]
