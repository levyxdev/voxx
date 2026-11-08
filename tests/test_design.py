import json
import wave

import numpy as np
import pyloudnorm
from conftest import assert_error

TEXT = "大家好，这是一段试读稿。"
WARM = "温和的中年女声，语速偏慢"
BRIGHT = "明亮的年轻男声，语气轻快"


def design(voxx, out, *describes, takes=None, model: str | None = "fake-clone", language="zh", env=None):
    args = ["voice", "design", *(a for d in describes for a in ("--describe", d)), "--text", TEXT,
            "--language", language, "--out", out]
    if takes is not None:
        args += ["--takes", takes]
    if model is not None:
        args += ["--model", model]
    return voxx(*args, env=env)


def read_wav(path):
    with wave.open(str(path)) as audio:
        return audio.getframerate(), np.frombuffer(audio.readframes(audio.getnframes()), "<i2") / 32768


def test_voice_design_reads_the_text_once_per_take_of_each_description(installed, tmp_path):
    out = tmp_path / "design"
    run = design(installed, out, WARM, BRIGHT, takes=2)

    assert run.exit_code == 0, run.result
    data = run.result["data"]
    assert data["path"] == str(out / "design.json")
    written = json.loads((out / "design.json").read_text(encoding="utf-8"))
    assert written == data["design"]
    assert (written["model"], written["language"], written["text"]) == ("fake-clone", "zh", TEXT)
    takes = written["takes"]
    # Numbered in the order of the descriptions, each description's takes together.
    assert [(t["take"], t["description"], t["audio"]) for t in takes] == [
        (1, WARM, "take-1.wav"), (2, WARM, "take-2.wav"), (3, BRIGHT, "take-3.wav"), (4, BRIGHT, "take-4.wav")]
    assert sorted(p.name for p in out.iterdir()) == ["design.json", "take-1.wav", "take-2.wav", "take-3.wav", "take-4.wav"]
    assert len({t["seed"] for t in takes}) == 4
    sounds = set()
    for take in takes:
        rate, samples = read_wav(out / take["audio"])
        assert rate == 48_000
        # Finished as a Line is: at -18 LUFS, with 50 ms of silence at each end.
        assert abs(pyloudnorm.Meter(rate).integrated_loudness(samples) - -18) <= 0.5
        sound = np.flatnonzero(np.abs(samples) > 0.01 * np.abs(samples).max())
        assert abs(sound[0] / rate - 0.05) < 0.005 and abs((len(samples) - sound[-1] - 1) / rate - 0.05) < 0.005
        sounds.add(samples.tobytes())
        # Each take is heard back, as a Line is.
        assert (take["transcript"], take["error_rate"], take["warnings"]) == (TEXT, 0, [])
    assert len(sounds) == 4


def test_voice_design_uses_voxcpm2_unless_model_names_another_and_fails_until_it_is_installed(voxx, tmp_path):
    run = design(voxx, tmp_path / "design", WARM, model=None)

    error = assert_error(run, 3, "model_not_installed")
    assert [m["model"] for m in error["details"]["missing"]] == ["voxcpm2"]
    assert not (tmp_path / "design").exists()


def test_voice_design_can_use_qwen3_voicedesign_in_a_language_voxcpm2_does_not_read(voxx, tmp_path):
    run = design(voxx, tmp_path / "design", WARM, model="qwen3-tts-1.7b-voicedesign", language="ja")

    error = assert_error(run, 3, "model_not_installed")
    assert [m["model"] for m in error["details"]["missing"]] == ["qwen3-tts-1.7b-voicedesign"]


def test_voice_design_needs_a_model_that_designs(installed, tmp_path):
    error = assert_error(design(installed, tmp_path / "design", WARM, model="fake-clone-alt"), 4, "capability_unsupported")

    assert error["details"]["capability"] == "design"


def test_voice_design_needs_a_language_the_model_reads(installed, tmp_path):
    error = assert_error(design(installed, tmp_path / "design", WARM, language="fr"), 4, "unsupported_language")

    assert error["details"]["languages"] == ["zh", "en"]
    error = assert_error(design(installed, tmp_path / "design", WARM, language="ZH"), 2, "invalid_language")
    assert "'zh'" in error["message"]


def test_voice_design_never_overwrites_the_takes_of_an_earlier_run(installed, tmp_path):
    out = tmp_path / "design"
    assert design(installed, out, WARM).exit_code == 0
    before = {p.name: p.read_bytes() for p in out.iterdir()}

    assert_error(design(installed, out, BRIGHT), 2, "design_exists")
    assert {p.name: p.read_bytes() for p in out.iterdir()} == before


def test_an_earlier_run_is_refused_before_anything_else_is_checked(voxx, installed, tmp_path):
    out = tmp_path / "design"
    assert design(installed, out, WARM).exit_code == 0

    # Not "model_not_installed": the takes in --out are what matters to the user.
    assert_error(design(voxx, out, WARM, model=None), 2, "design_exists")


def test_a_run_that_fails_leaves_no_design_json(installed, tmp_path):
    out = tmp_path / "design"
    run = design(installed, out, WARM, BRIGHT, env={"VOXX_TEST_FAKE_CRASH": "synthesize:2"})

    assert_error(run, 1, "worker_crashed")
    assert list(out.iterdir()) == []
    # So the same --out can be used again.
    assert design(installed, out, WARM).exit_code == 0


def test_voice_design_without_the_transcriber_installed_gives_takes_a_warning_instead_of_a_check(installed, tmp_path):
    (installed.home / "models" / "fake-asr" / "voxx-install.json").unlink()

    run = design(installed, tmp_path / "design", WARM)

    assert run.exit_code == 0, run.result
    [take] = run.result["data"]["design"]["takes"]
    assert "transcript" not in take and "error_rate" not in take
    [warning] = take["warnings"]
    assert warning["code"] == "checker_not_installed"
    assert warning["details"]["command"] == "voxx install fake-asr"


def test_voice_design_needs_a_description_text_and_one_take_or_more(installed, tmp_path):
    assert_error(design(installed, tmp_path / "a", " "), 2, "invalid_arguments")
    assert_error(design(installed, tmp_path / "b", WARM, takes=0), 2, "invalid_arguments")
    assert_error(installed("voice", "design", "--text", TEXT, "--language", "zh", "--out", tmp_path / "c"),
                 2, "invalid_arguments")
