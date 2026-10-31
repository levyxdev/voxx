import json
import os
import wave

import pytest
from conftest import assert_error

TWO_LINES = {
    "language": "zh",
    "voice": "fake-alice",
    "lines": [
        {"id": "intro", "text": "这是一个新的发送流程。"},
        {"id": "send", "text": "点一下发送就完成了。", "style": "语气兴奋"},
    ],
}


def test_narrate_writes_a_wav_per_line_and_the_completed_narration(installed, write_narration, tmp_path):
    out = tmp_path / "out"
    run = installed("narrate", write_narration(TWO_LINES), "--out", out)

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


def test_narrate_reports_progress_for_each_line(installed, write_narration, tmp_path):
    run = installed("narrate", write_narration(TWO_LINES), "--out", tmp_path / "out")

    done = [e["id"] for e in run.events if e["event"] == "line_done"]
    assert done == ["intro", "send"]


def test_a_line_voice_overrides_the_narration_voice(installed, write_narration, tmp_path):
    narration = {**TWO_LINES, "voice": "fake-bob", "lines": [TWO_LINES["lines"][0], {**TWO_LINES["lines"][1], "voice": "fake-alice"}]}
    run = installed("narrate", write_narration(narration), "--out", tmp_path / "out")

    assert [l["voice"] for l in run.result["data"]["narration"]["lines"]] == ["fake-bob", "fake-alice"]


def test_a_line_id_can_be_any_safe_file_name(installed, write_narration, tmp_path):
    out = tmp_path / "out"
    longest = "开" * 81  # 243 bytes, so `<id>.wav.partial` is 255
    narration = {"language": "zh", "voice": "fake-alice",
                 "lines": [{"id": "开场", "text": "一"}, {"id": "step 1", "text": "二"}, {"id": longest, "text": "三"}]}
    run = installed("narrate", write_narration(narration), "--out", out)

    assert run.exit_code == 0
    assert all((out / f"{id}.wav").exists() for id in ("开场", "step 1", longest))


@pytest.mark.parametrize("narration", [
    {"language": "zh"},
    {"language": "zh", "lines": []},
    {"language": "zh", "lines": [{"id": "a", "text": "一"}, {"id": "a", "text": "二"}]},
    {"language": "zh", "lines": [{"id": "Intro", "text": "一"}, {"id": "intro", "text": "二"}]},
    {"language": "japanese", "lines": [{"id": "a", "text": "一"}]},
    {"language": "ZH", "lines": [{"id": "a", "text": "一"}]},
    {"language": "zh-hk", "lines": [{"id": "a", "text": "一"}]},
    {"language": "zh-HANT", "lines": [{"id": "a", "text": "一"}]},
    {"language": "zh_CN", "lines": [{"id": "a", "text": "一"}]},
    {"language": "en-", "lines": [{"id": "a", "text": "一"}]},
    {"language": "zh", "seed": -1, "lines": [{"id": "a", "text": "一"}]},
    {"language": "zh", "seed": 2**31, "lines": [{"id": "a", "text": "一"}]},
    {"language": "zh", "lines": [{"id": "a", "text": "一", "seed": "7"}]},
    {"language": "zh", "lines": [{"id": "a", "text": "一", "seed": 7.5}]},
    {"language": "zh", "lines": [{"id": "a", "text": "一", "seed": True}]},
    {"language": "zh", "lines": [{"id": "../a", "text": "一"}]},
    {"language": "zh", "lines": [{"id": "a\\b", "text": "一"}]},
    {"language": "zh", "lines": [{"id": ".hidden", "text": "一"}]},
    {"language": "zh", "lines": [{"id": "a\n", "text": "一"}]},
    {"language": "zh", "lines": [{"id": "", "text": "一"}]},
    {"language": "zh", "lines": [{"id": " ", "text": "一"}]},
    {"language": "zh", "lines": [{"id": "caf\u00e9", "text": "一"}, {"id": "cafe\u0301", "text": "二"}]},
    {"language": "zh", "lines": [{"id": "a\u200bb", "text": "一"}]},
    {"language": "zh", "lines": [{"id": "\u202eabc", "text": "一"}]},
    {"language": "zh", "lines": [{"id": "a\u2028b", "text": "一"}]},
    {"language": "zh", "lines": [{"id": "开" * 82, "text": "一"}]},
    {"language": "zh", "lines": [{"id": "a", "text": ""}]},
])
def test_an_invalid_narration_is_an_argument_error(installed, write_narration, tmp_path, narration):
    out = tmp_path / "out"
    run = installed("narrate", write_narration(narration), "--out", out)

    assert_error(run, 2, "invalid_narration")
    assert not out.exists()


def test_a_language_in_another_case_names_its_canonical_form(installed, write_narration, tmp_path):
    narration = {"language": "zh-hant-hk", "voice": "fake-alice", "lines": [{"id": "a", "text": "一"}]}
    error = assert_error(installed("narrate", write_narration(narration), "--out", tmp_path / "out"), 2, "invalid_narration")

    assert "zh-Hant-HK" in error["message"]


@pytest.mark.parametrize("language", ["en-US", "zh-Hant-HK", "zh-CN"])
def test_a_language_tag_a_model_has_not_registered_is_unsupported_even_if_its_language_is(installed, write_narration,
                                                                                            tmp_path, language):
    narration = {"language": language, "voice": "fake-alice", "lines": [{"id": "a", "text": "一"}]}
    error = assert_error(installed("narrate", write_narration(narration), "--out", tmp_path / "out"), 4, "unsupported_language")

    assert error["details"]["language"] == language
    assert "zh" in error["details"]["languages"]


def test_a_language_can_be_any_tag_a_model_registers(installed, write_narration, tmp_path):
    narration = {"language": "yue", "voice": "fake-alice", "lines": [{"id": "a", "text": "撳一下發送"}]}
    run = installed("narrate", write_narration(narration), "--out", tmp_path / "out")

    assert run.exit_code == 0, run.result
    [line] = lines_of(run)
    assert run.result["data"]["narration"]["language"] == "yue"
    assert line["error_rate"] == 0


def test_a_line_id_that_is_not_valid_unicode_is_an_argument_error(installed, tmp_path):
    path = tmp_path / "narration.json"
    path.write_text(json.dumps({"language": "zh", "lines": [{"id": "\ud800", "text": "一"}]}), encoding="utf-8")

    assert_error(installed("narrate", path, "--out", tmp_path / "out"), 2, "invalid_narration")


def test_a_missing_narration_file_is_an_argument_error(installed, tmp_path):
    assert_error(installed("narrate", tmp_path / "nope.json", "--out", tmp_path / "out"), 2, "narration_not_found")


def test_missing_arguments_are_an_argument_error(installed, write_narration):
    assert_error(installed("narrate", write_narration(TWO_LINES)), 2, "invalid_arguments")
    assert_error(installed(), 2, "invalid_arguments")


def test_an_unusable_out_is_an_argument_error(installed, write_narration, tmp_path):
    a_file = tmp_path / "a-file"
    a_file.write_text("")
    locked = tmp_path / "locked"
    locked.mkdir(mode=0o500)

    for out in (a_file, locked / "out", locked):
        assert_error(installed("narrate", write_narration(TWO_LINES), "--out", out), 2, "invalid_out")


def test_an_unknown_voice_is_an_argument_error(installed, write_narration, tmp_path):
    error = assert_error(installed("narrate", write_narration({**TWO_LINES, "voice": "nobody"}), "--out", tmp_path / "out"), 2, "unknown_voice")
    assert "fake-alice" in error["details"]["known_voices"]


@pytest.mark.parametrize("step", ["load", "synthesize", "align"])
def test_a_crashed_worker_is_a_structured_internal_error(installed, write_narration, tmp_path, step):
    run = installed("narrate", write_narration(TWO_LINES), "--out", tmp_path / "out", env={"VOXX_TEST_FAKE_CRASH": step})

    error = assert_error(run, 1, "worker_crashed")
    assert error["details"]["signal"] == "SIGKILL"
    with pytest.raises(ProcessLookupError):
        os.kill(error["details"]["worker_pid"], 0)
    assert not (tmp_path / "out" / "narration.json").exists()


def test_narrate_without_the_model_installed_fails_without_downloading(voxx, write_narration, tmp_path, hub):
    out = tmp_path / "out"
    run = voxx("narrate", write_narration(TWO_LINES), "--out", out)

    error = assert_error(run, 3, "model_not_installed")
    assert error["details"] == {
        "missing": [{"model": "fake-tts", "size_bytes": 4096, "license": "Apache-2.0",
                     "license_url": "https://huggingface.co/voxx-test/fake-tts"},
                    {"model": "fake-aligner", "size_bytes": 4096, "license": "Apache-2.0",
                     "license_url": "https://huggingface.co/voxx-test/fake-aligner"},
                    {"model": "fake-asr", "size_bytes": 4096, "license": "Apache-2.0",
                     "license_url": "https://huggingface.co/voxx-test/fake-asr"}],
        "total_bytes": 12288,
    }
    assert "`voxx install fake-tts` and `voxx install fake-aligner` and `voxx install fake-asr`" in error["hint"]
    assert hub.requests == []
    assert not out.exists()


def lines_of(run):
    return run.result["data"]["narration"]["lines"]


def audio_of(out, line_id):
    return (out / f"{line_id}.wav").read_bytes()


def test_model_picks_which_model_reads_the_narration(installed, write_narration, tmp_path):
    run = installed("narrate", write_narration(TWO_LINES), "--out", tmp_path / "out", "--model", "fake-tts-small")

    assert run.exit_code == 0
    assert [l["model"] for l in lines_of(run)] == ["fake-tts-small", "fake-tts-small"]


@pytest.mark.parametrize("language, voice", [("zh", "fake-alice"), ("en", "fake-bob"), ("fr", "fake-alice")])
def test_without_a_voice_the_model_reads_with_a_native_voice_of_the_language(installed, write_narration, tmp_path,
                                                                             language, voice):
    narration = {"language": language, "lines": [{"id": "a", "text": "一"}]}
    run = installed("narrate", write_narration(narration), "--out", tmp_path / "out", "--model", "fake-tts")

    assert lines_of(run)[0]["voice"] == voice


def test_without_a_voice_or_model_the_default_preset_model_reads_and_qwen3_models_listen(voxx, write_narration, tmp_path):
    run = voxx("narrate", write_narration({"language": "en", "lines": [{"id": "a", "text": "Hi."}]}), "--out", tmp_path / "out")

    error = assert_error(run, 3, "model_not_installed")
    assert [m["model"] for m in error["details"]["missing"]] == ["qwen3-tts-1.7b-customvoice", "qwen3-forcedaligner-0.6b",
                                                                 "qwen3-asr-0.6b"]


def test_an_unknown_model_is_an_argument_error(installed, write_narration, tmp_path):
    error = assert_error(installed("narrate", write_narration(TWO_LINES), "--out", tmp_path / "out", "--model", "nope"),
                         2, "unknown_model")
    assert "fake-tts" in error["details"]["known_models"]


@pytest.mark.parametrize("model, narration, code", [
    ("qwen3-tts-1.7b-base", TWO_LINES, "capability_unsupported"),
    ("fake-tts", {**TWO_LINES, "voice": "vivian"}, "voice_unsupported"),
    ("fake-tts-small", {**TWO_LINES, "language": "fr"}, "unsupported_language"),
])
def test_asking_a_model_for_what_it_cannot_do_is_unsupported(voxx, write_narration, tmp_path, model, narration, code):
    out = tmp_path / "out"
    run = voxx("narrate", write_narration(narration), "--out", out, "--model", model)

    error = assert_error(run, 4, code)
    assert error["details"]["model"] == model
    assert not out.exists()


def test_a_model_that_ignores_style_reads_the_line_without_it_and_warns(installed, write_narration, tmp_path):
    narration = {"language": "zh", "voice": "fake-alice", "seed": 7,
                 "lines": [{"id": "plain", "text": "一样的话"}, {"id": "styled", "text": "一样的话", "style": "语气兴奋"}]}
    small, full = tmp_path / "small", tmp_path / "full"
    small_run = installed("narrate", write_narration(narration), "--out", small, "--model", "fake-tts-small")
    full_run = installed("narrate", write_narration(narration), "--out", full, "--model", "fake-tts")

    assert audio_of(small, "styled") == audio_of(small, "plain")
    assert audio_of(full, "styled") != audio_of(full, "plain")
    plain, styled = lines_of(small_run)
    assert plain["warnings"] == []
    assert [w["code"] for w in styled["warnings"]] == ["style_ignored"]
    assert styled["style"] == "语气兴奋"
    assert [l["warnings"] for l in lines_of(full_run)] == [[], []]


def test_a_given_seed_is_used_and_reproduces_the_line(installed, write_narration, tmp_path):
    narration = {"language": "zh", "voice": "fake-alice", "seed": 7,
                 "lines": [{"id": "a", "text": "同一句话"}, {"id": "b", "text": "同一句话", "seed": 8}]}
    first, second = tmp_path / "first", tmp_path / "second"
    run = installed("narrate", write_narration(narration), "--out", first)
    installed("narrate", write_narration(narration), "--out", second)

    assert [l["seed"] for l in lines_of(run)] == [7, 8]
    assert audio_of(first, "a") == audio_of(second, "a")
    assert audio_of(first, "a") != audio_of(first, "b")


def test_the_completed_narration_reads_again_to_the_same_audio(installed, write_narration, tmp_path):
    first, second = tmp_path / "first", tmp_path / "second"
    installed("narrate", write_narration(TWO_LINES), "--out", first)
    installed("narrate", first / "narration.json", "--out", second)

    for line_id in ("intro", "send"):
        assert audio_of(first, line_id) == audio_of(second, line_id)


def test_the_completed_narration_reads_again_to_the_same_audio_with_the_same_model(installed, write_narration, tmp_path):
    first, second = tmp_path / "first", tmp_path / "second"
    installed("narrate", write_narration(TWO_LINES), "--out", first, "--model", "fake-tts-small")
    installed("narrate", first / "narration.json", "--out", second, "--model", "fake-tts-small")

    for line_id in ("intro", "send"):
        assert audio_of(first, line_id) == audio_of(second, line_id)
