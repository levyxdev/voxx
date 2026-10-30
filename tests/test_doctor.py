import shutil

import pytest


def doctor(voxx, platform):
    run = voxx("doctor", env={"VOXX_TEST_PLATFORM": platform})
    assert run.exit_code == 0
    return run.result["data"]


def test_doctor_supports_apple_silicon_macs(voxx):
    assert doctor(voxx, "Darwin arm64")["platform"] == {"system": "Darwin", "machine": "arm64", "apple_silicon": True,
                                                        "supported": True}


@pytest.mark.parametrize("platform", ["Linux x86_64", "Linux aarch64", "Windows AMD64", "Darwin x86_64"])
def test_doctor_says_plainly_when_the_platform_is_not_supported(voxx, platform):
    reported = doctor(voxx, platform)["platform"]

    assert reported["apple_silicon"] is False
    assert reported["supported"] is False
    assert "Apple Silicon" in reported["reason"]


def test_doctor_tells_apart_an_x86_python_on_an_apple_silicon_mac(voxx):
    reported = doctor(voxx, "Darwin x86_64 rosetta")["platform"]

    assert reported["apple_silicon"] is True
    assert reported["supported"] is False
    assert "arm64" in reported["reason"]


def test_doctor_reports_installed_models_and_free_disk_space(installed):
    data = doctor(installed, "Darwin arm64")

    assert data["home"] == str(installed.home)
    assert data["models"]["installed"] == ["fake-tts"]
    not_installed = {m["model"]: m["size_bytes"] for m in data["models"]["not_installed"]}
    assert not_installed["voxcpm2"] == 3_226_617_581
    assert "fake-tts" not in not_installed
    assert 0 < data["disk"]["free_bytes"] <= shutil.disk_usage(installed.home).total


def test_doctor_works_before_voxx_home_exists(voxx):
    data = doctor(voxx, "Darwin arm64")

    assert not voxx.home.exists()
    assert data["models"]["installed"] == []
    assert data["disk"]["free_bytes"] > 0


def test_doctor_reads_the_real_platform(voxx):
    data = voxx("doctor").result["data"]

    assert isinstance(data["platform"]["supported"], bool)
