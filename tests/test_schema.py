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
    for where in (narrate["input"]["properties"], narrate["input"]["properties"]["lines"]["items"]["properties"]):
        assert where["emotion"]["enum"] == ["happy", "sad", "angry", "fearful", "disgusted", "surprised", "neutral"]
        assert where["speed"]["enum"] == ["slow", "medium", "fast"]
        assert where["pitch"]["enum"] == where["volume"]["enum"] == ["low", "medium", "high"]
    line = narrate["result"]["properties"]["narration"]["properties"]["lines"]["items"]
    assert {"audio", "model", "voice", "seed", "sample_rate", "warnings"} <= set(line["required"])
    assert {"unknown_voice", "unknown_model", "capability_unsupported", "voice_unsupported",
            "unsupported_language"} <= set(narrate["errors"])
    assert set(data["exit_codes"]) == {"0", "1", "2", "3", "4"}


def test_schema_describes_models_install_and_doctor(voxx):
    commands = voxx("schema").result["data"]["commands"]

    assert set(commands["models"]["arguments"]["properties"]["capability"]["enum"]) == {"preset_voice", "clone", "design", "align", "transcribe"}
    model = commands["models"]["result"]["properties"]["models"]["items"]
    assert {"id", "capabilities", "size_bytes", "weights_license", "installed"} <= set(model["required"])
    assert commands["install"]["arguments"]["required"] == ["model"]
    assert {"model", "path", "already_installed"} <= set(commands["install"]["result"]["required"])
    assert {"platform", "disk", "models"} <= set(commands["doctor"]["result"]["required"])
    preset, cloned, designed = commands["voices"]["result"]["properties"]["voices"]["items"]["oneOf"]
    assert {"name", "kind", "native_language", "description", "languages", "models"} <= set(preset["required"])
    assert {"name", "kind", "reference_text", "model", "languages", "models", "path"} <= set(cloned["required"])
    assert (cloned["properties"]["kind"]["const"], designed["properties"]["kind"]["const"]) == ("cloned", "designed")
    assert {"description", "design_model", "take", "seed"} <= set(designed["required"]) - set(cloned["required"])
    assert set(commands["voices"]["arguments"]["properties"]) == {"model", "language"}
    assert {"voices", "unlisted"} <= set(commands["voices"]["result"]["required"])
    assert "missing" in commands["narrate"]["errors"]["model_not_installed"]["properties"]
    assert {"unknown_model", "download_failed", "download_corrupt", "invalid_repo", "insufficient_disk_space"} <= set(commands["install"]["errors"])
    # Extra repos, where a Model has any: in the listing, in what the user is told before install, and in its result.
    assert {"repo", "size_bytes", "license"} <= set(model["properties"]["extra_repos"]["items"]["required"])
    summary = commands["narrate"]["errors"]["model_not_installed"]["properties"]["missing"]["items"]
    assert {"repo", "size_bytes", "license", "license_url"} <= set(summary["properties"]["extra_repos"]["items"]["required"])
    assert {"repo", "revision", "size_bytes", "path"} <= set(
        commands["install"]["result"]["properties"]["extra_repos"]["items"]["required"])


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


def test_schema_describes_the_warnings_for_a_missing_aligner_or_transcriber(voxx):
    narrate = voxx("schema", "narrate").result["data"]["narrate"]
    warnings = narrate["result"]["properties"]["narration"]["properties"]["lines"]["items"]["properties"]["warnings"]

    assert "aligner_not_installed" in warnings["description"]
    assert "checker_not_installed" in warnings["description"]
    # The Model to offer the user, as model_not_installed lists it, and how to install it.
    details = warnings["items"]["properties"]["details"]
    assert set(narrate["errors"]["model_not_installed"]["properties"]["missing"]["items"]["required"]) < set(details["required"])
    assert "command" in details["required"]


def test_schema_describes_voice_add(voxx):
    run = voxx("schema", "voice", "add")

    assert run.exit_code == 0
    voice_add = run.result["data"]["voice add"]
    assert voice_add["arguments"]["required"] == ["name"]
    # A Cloned Voice from --ref, or a Designed Voice from --from-design and --take.
    assert [set(o["required"]) for o in voice_add["arguments"]["oneOf"]] == [{"ref"}, {"from_design", "take"}]
    assert {"ref_text", "model", "overwrite"} <= set(voice_add["arguments"]["properties"])
    assert [o["properties"]["kind"]["const"] for o in voice_add["result"]["oneOf"]] == ["cloned", "designed"]
    assert all({"reference_text", "model", "path", "warnings"} <= set(o["required"]) for o in voice_add["result"]["oneOf"])
    assert {"model_not_installed", "voice_exists", "unreadable_reference", "capability_unsupported", "design_not_found",
            "invalid_design", "take_not_found"} <= set(voice_add["errors"])


def test_schema_describes_voice_design(voxx):
    run = voxx("schema", "voice", "design")

    assert run.exit_code == 0
    voice_design = run.result["data"]["voice design"]
    assert set(voice_design["arguments"]["required"]) == {"describe", "text", "language", "out"}
    assert {"takes", "model"} <= set(voice_design["arguments"]["properties"])
    assert set(voice_design["result"]["required"]) == {"path", "design"}
    take = voice_design["result"]["properties"]["design"]["properties"]["takes"]["items"]
    assert {"take", "description", "seed", "audio", "warnings"} <= set(take["required"])
    assert {"transcript", "error_rate"} <= set(take["properties"])
    assert {"model_not_installed", "capability_unsupported", "unsupported_language", "invalid_language",
            "design_exists", "invalid_out"} <= set(voice_design["errors"])


def test_schema_describes_voice_default_and_which_voices_are_defaults(voxx):
    commands = voxx("schema").result["data"]["commands"]

    voice_default = commands["voice default"]
    assert voice_default["arguments"]["required"] == ["language"]
    assert {"name", "language", "clear"} == set(voice_default["arguments"]["properties"])
    assert set(voice_default["result"]["required"]) == {"language", "voice"}
    assert {"unknown_voice", "unsupported_language", "invalid_language"} <= set(voice_default["errors"])
    assert "defaults" in commands["voices"]["result"]["required"]
    for kind in commands["voices"]["result"]["properties"]["voices"]["items"]["oneOf"]:
        assert "default_for" in kind["required"]
    assert "default_voice" in commands["narrate"]["errors"]["unknown_voice"]["description"]
