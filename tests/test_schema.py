import os
import subprocess
import sys


def test_schema_describes_narrate(voxx):
    run = voxx("schema")

    assert run.exit_code == 0
    data = run.result["data"]
    narrate = data["commands"]["narrate"]
    assert set(narrate["arguments"]["required"]) == {"narration", "out"}
    assert {"model", "line"} <= set(narrate["arguments"]["properties"])
    assert "--line" in narrate["usage"]
    assert narrate["input"]["properties"]["language"]["pattern"] == "^[a-z]{2,3}(-[A-Z][a-z]{3})?(-([A-Z]{2}|[0-9]{3}))?$"
    assert {"voice", "style", "seed"} <= set(narrate["input"]["properties"]["lines"]["items"]["properties"])
    line = narrate["result"]["properties"]["narration"]["properties"]["lines"]["items"]
    assert {"audio", "model", "voice", "seed", "sample_rate", "warnings"} <= set(line["required"])
    assert {"unknown_voice", "unknown_model", "capability_unsupported", "voice_unsupported",
            "unsupported_language"} <= set(narrate["errors"])
    assert set(data["exit_codes"]) == {"0", "1", "2", "3", "4"}


def test_schema_describes_models_install_and_doctor(voxx):
    commands = voxx("schema").result["data"]["commands"]

    assert set(commands["models"]["arguments"]["properties"]["capability"]["enum"]) == {"preset_voice", "clone", "align", "transcribe"}
    model = commands["models"]["result"]["properties"]["models"]["items"]
    assert {"id", "capabilities", "size_bytes", "weights_license", "installed"} <= set(model["required"])
    assert commands["install"]["arguments"]["required"] == ["model"]
    assert {"model", "path", "already_installed"} <= set(commands["install"]["result"]["required"])
    assert {"platform", "disk", "models"} <= set(commands["doctor"]["result"]["required"])
    voice = commands["voices"]["result"]["properties"]["voices"]["items"]
    assert {"name", "kind", "native_language", "description", "languages", "models"} <= set(voice["required"])
    assert "missing" in commands["narrate"]["errors"]["model_not_installed"]["properties"]
    assert {"unknown_model", "download_failed", "download_corrupt", "invalid_repo", "insufficient_disk_space"} <= set(commands["install"]["errors"])


def test_schema_describes_one_command(voxx):
    run = voxx("schema", "narrate")

    assert list(run.result["data"]) == ["narrate"]


def test_schema_of_an_unknown_command_is_an_argument_error(voxx):
    run = voxx("schema", "dance")

    assert run.exit_code == 2
    assert run.result["error"]["code"] == "unknown_command"


def test_the_cli_does_not_import_mlx(voxx, tmp_path):
    # A stand-in mlx package that leaves a mark if anything imports it.
    marker = tmp_path / "mlx-imported"
    (tmp_path / "shadow" / "mlx").mkdir(parents=True)
    (tmp_path / "shadow" / "mlx" / "__init__.py").write_text(f"open({str(marker)!r}, 'w').close()\n")

    run = voxx("schema", env={"PYTHONPATH": str(tmp_path / "shadow")})

    assert run.exit_code == 0
    assert not marker.exists()
    # The stand-in works: importing mlx under the same environment leaves the mark.
    subprocess.run([sys.executable, "-c", "import mlx"], env={**os.environ, "PYTHONPATH": str(tmp_path / "shadow")}, check=True)
    assert marker.exists()


def test_schema_describes_the_self_check(voxx):
    line = voxx("schema", "narrate").result["data"]["narrate"]["result"]["properties"]["narration"]["properties"]["lines"]["items"]

    assert line["properties"]["transcript"]["type"] == "string"
    assert line["properties"]["error_rate"]["type"] == "number"
    # A Line in a language the transcriber cannot hear has neither.
    assert not {"transcript", "error_rate"} & set(line["required"])


def test_schema_describes_word_timing(voxx):
    line = voxx("schema", "narrate").result["data"]["narrate"]["result"]["properties"]["narration"]["properties"]["lines"]["items"]

    assert set(line["properties"]["words"]["items"]["required"]) == {"text", "start", "end"}
    # A Line the aligner could not time has a not_aligned warning instead.
    assert "words" not in line["required"]
    assert "not_aligned" in line["properties"]["warnings"]["description"]
