import json
import os
import wave

import pytest

TWO_LINES = {
    "language": "zh",
    "lines": [
        {"id": "intro", "text": "这是一个新的发送流程。"},
        {"id": "send", "text": "点一下发送就完成了。", "style": "语气兴奋"},
    ],
}


def assert_error(run, exit_code, code):
    assert run.exit_code == exit_code
    assert run.result["ok"] is False
    error = run.result["error"]
    assert error["code"] == code
    assert error["message"] and error["hint"]
    return error


def test_narrate_writes_a_wav_per_line_and_the_completed_narration(voxx, write_narration, tmp_path):
    out = tmp_path / "out"
    run = voxx("narrate", write_narration(TWO_LINES), "--out", out)

    assert run.exit_code == 0
    assert run.result["ok"] is True
    path = out / "narration.json"
    assert run.result["data"]["path"] == str(path)
    written = json.loads(path.read_text(encoding="utf-8"))
    assert written == run.result["data"]["narration"]
    assert written["language"] == "zh"
    assert [(l["id"], l["text"]) for l in written["lines"]] == [(l["id"], l["text"]) for l in TWO_LINES["lines"]]
    for line in written["lines"]:
        assert line["audio"] == f"{line['id']}.wav"
        assert line["model"] == "fake-tts"
        assert line["voice"] == "fake-alice"
        assert isinstance(line["seed"], int)
        with wave.open(str(path.parent / line["audio"])) as audio:
            assert audio.getnchannels() == 1
            assert audio.getframerate() == line["sample_rate"]
            assert audio.getnframes() > 0
    assert written["lines"][1]["style"] == "语气兴奋"


def test_narrate_reports_progress_for_each_line(voxx, write_narration, tmp_path):
    run = voxx("narrate", write_narration(TWO_LINES), "--out", tmp_path / "out")

    done = [e["id"] for e in run.events if e["event"] == "line_done"]
    assert done == ["intro", "send"]


def test_a_line_voice_overrides_the_narration_voice(voxx, write_narration, tmp_path):
    narration = {**TWO_LINES, "voice": "fake-bob", "lines": [TWO_LINES["lines"][0], {**TWO_LINES["lines"][1], "voice": "fake-alice"}]}
    run = voxx("narrate", write_narration(narration), "--out", tmp_path / "out")

    assert [l["voice"] for l in run.result["data"]["narration"]["lines"]] == ["fake-bob", "fake-alice"]


@pytest.mark.parametrize("narration", [
    {"language": "zh"},
    {"language": "zh", "lines": []},
    {"language": "zh", "lines": [{"id": "a", "text": "一"}, {"id": "a", "text": "二"}]},
    {"language": "zh", "lines": [{"id": "Intro", "text": "一"}, {"id": "intro", "text": "二"}]},
    {"language": "ja", "lines": [{"id": "a", "text": "一"}]},
    {"language": "zh", "lines": [{"id": "../a", "text": "一"}]},
    {"language": "zh", "lines": [{"id": "a", "text": ""}]},
])
def test_an_invalid_narration_is_an_argument_error(voxx, write_narration, tmp_path, narration):
    out = tmp_path / "out"
    run = voxx("narrate", write_narration(narration), "--out", out)

    assert_error(run, 2, "invalid_narration")
    assert not out.exists()


def test_a_missing_narration_file_is_an_argument_error(voxx, tmp_path):
    assert_error(voxx("narrate", tmp_path / "nope.json", "--out", tmp_path / "out"), 2, "narration_not_found")


def test_missing_arguments_are_an_argument_error(voxx, write_narration):
    assert_error(voxx("narrate", write_narration(TWO_LINES)), 2, "invalid_arguments")
    assert_error(voxx(), 2, "invalid_arguments")


def test_an_unusable_out_is_an_argument_error(voxx, write_narration, tmp_path):
    a_file = tmp_path / "a-file"
    a_file.write_text("")
    locked = tmp_path / "locked"
    locked.mkdir(mode=0o500)

    for out in (a_file, locked / "out", locked):
        assert_error(voxx("narrate", write_narration(TWO_LINES), "--out", out), 2, "invalid_out")


def test_an_unknown_voice_is_an_argument_error(voxx, write_narration, tmp_path):
    error = assert_error(voxx("narrate", write_narration({**TWO_LINES, "voice": "nobody"}), "--out", tmp_path / "out"), 2, "unknown_voice")
    assert "fake-alice" in error["details"]["known_voices"]


@pytest.mark.parametrize("step", ["load", "synthesize"])
def test_a_crashed_worker_is_a_structured_internal_error(voxx, write_narration, tmp_path, step):
    run = voxx("narrate", write_narration(TWO_LINES), "--out", tmp_path / "out", env={"VOXX_TEST_FAKE_CRASH": step})

    error = assert_error(run, 1, "worker_crashed")
    assert error["details"]["signal"] == "SIGKILL"
    with pytest.raises(ProcessLookupError):
        os.kill(error["details"]["worker_pid"], 0)
    assert not (tmp_path / "out" / "narration.json").exists()
