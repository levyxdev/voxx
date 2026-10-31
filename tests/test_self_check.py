"""The self-check: voxx transcribes every Line it read and reports how far the transcript is from the text."""

import json
import shutil

from conftest import assert_error

HEARD = "VOXX_TEST_FAKE_HEARD"


def narrate(installed, write_narration, tmp_path, narration, heard=None):
    env = {HEARD: json.dumps(heard, ensure_ascii=False)} if heard else None
    run = installed("narrate", write_narration(narration), "--out", tmp_path / "out", env=env)
    assert run.exit_code == 0, run.result
    return run.result["data"]["narration"]["lines"]


def test_a_line_transcribed_as_written_has_an_error_rate_of_zero(installed, write_narration, tmp_path):
    narration = {"language": "zh", "voice": "fake-alice", "lines": [{"id": "intro", "text": "这是一个新的发送流程。"}]}
    [line] = narrate(installed, write_narration, tmp_path, narration)

    assert line["transcript"] == "这是一个新的发送流程。"
    assert line["error_rate"] == 0


def test_a_chinese_line_is_scored_per_character(installed, write_narration, tmp_path):
    # 10 characters; one swapped and one dropped.
    narration = {"language": "zh", "voice": "fake-alice", "lines": [{"id": "a", "text": "这是一个新的发送流程。"}]}
    [line] = narrate(installed, write_narration, tmp_path, narration, heard={"这是一个新的发送流程。": "这是一个心的发流程"})

    assert line["transcript"] == "这是一个心的发流程"
    assert line["error_rate"] == 0.2


def test_an_english_line_is_scored_per_word(installed, write_narration, tmp_path):
    # 7 words; one swapped.
    narration = {"language": "en", "voice": "fake-bob", "lines": [{"id": "a", "text": "This is the new way to send."}]}
    [line] = narrate(installed, write_narration, tmp_path, narration, heard={"This is the new way to send.": "This is the knew way to send."})

    assert line["error_rate"] == round(1 / 7, 4)


def test_punctuation_spacing_and_case_do_not_count(installed, write_narration, tmp_path):
    narration = {"language": "en", "voice": "fake-bob", "lines": [
        {"id": "en", "text": "Press send, and you're done!"},
        {"id": "zh", "text": "点一下「发送」，就完成了。"},
    ]}
    heard = {"Press send, and you're done!": "press SEND and youre done", "点一下「发送」，就完成了。": "点一下 发送 就完成了!"}
    lines = narrate(installed, write_narration, tmp_path, narration, heard=heard)

    assert [l["error_rate"] for l in lines] == [0, 0]


def test_an_english_word_in_a_chinese_line_counts_once(installed, write_narration, tmp_path):
    # 点 一 下 Send 按 钮: 6 units, and the misheard word is one of them.
    narration = {"language": "zh", "voice": "fake-alice", "lines": [{"id": "a", "text": "点一下 Send 按钮"}]}
    [line] = narrate(installed, write_narration, tmp_path, narration, heard={"点一下 Send 按钮": "点一下 Sand 按钮"})

    assert line["error_rate"] == round(1 / 6, 4)


def test_extra_words_heard_can_push_the_error_rate_above_one(installed, write_narration, tmp_path):
    narration = {"language": "en", "voice": "fake-bob", "lines": [{"id": "a", "text": "Hi."}]}
    [line] = narrate(installed, write_narration, tmp_path, narration, heard={"Hi.": "Oh, hi there, friend."})

    assert line["error_rate"] == 3


def test_a_line_in_a_language_no_model_transcribes_is_read_but_not_checked(installed, write_narration, tmp_path):
    narration = {"language": "fr", "voice": "fake-alice", "lines": [{"id": "a", "text": "Bonjour."}]}
    [line] = narrate(installed, write_narration, tmp_path, narration)

    assert (tmp_path / "out" / "a.wav").exists()
    assert "transcript" not in line and "error_rate" not in line
    assert [w["code"] for w in line["warnings"]] == ["not_checked"]


def test_a_line_in_a_language_no_model_transcribes_does_not_need_the_transcriber_installed(installed, write_narration, tmp_path):
    shutil.rmtree(installed.home / "models" / "fake-asr")
    narration = {"language": "fr", "voice": "fake-alice", "lines": [{"id": "a", "text": "Bonjour."}]}

    assert narrate(installed, write_narration, tmp_path, narration)[0]["warnings"][0]["code"] == "not_checked"


def test_narrate_without_the_transcriber_installed_fails_without_downloading(installed, write_narration, tmp_path, hub):
    shutil.rmtree(installed.home / "models" / "fake-asr")
    out = tmp_path / "out"
    narration = {"language": "zh", "voice": "fake-alice", "lines": [{"id": "a", "text": "一"}]}
    run = installed("narrate", write_narration(narration), "--out", out)

    error = assert_error(run, 3, "model_not_installed")
    assert [m["model"] for m in error["details"]["missing"]] == ["fake-asr"]
    assert "voxx install fake-asr" in error["hint"]
    assert hub.requests == []
    assert not out.exists()


def test_a_high_error_rate_is_reported_not_retried(installed, write_narration, tmp_path):
    narration = {"language": "zh", "voice": "fake-alice", "lines": [{"id": "a", "text": "点一下发送"}]}
    run = installed("narrate", write_narration(narration), "--out", tmp_path / "out",
                    env={HEARD: json.dumps({"点一下发送": "完全不对的话"})})

    assert run.exit_code == 0
    [line] = run.result["data"]["narration"]["lines"]
    assert line["error_rate"] > 1
    assert [e["id"] for e in run.events if e["event"] == "line_started"] == ["a"]


def test_a_line_read_as_silence_is_transcribed_as_nothing(installed, write_narration, tmp_path):
    # Seed 5 makes the fake Engine read too quietly to survive as 16-bit samples.
    narration = {"language": "zh", "voice": "fake-alice", "lines": [{"id": "a", "text": "点一下发送", "seed": 5}]}
    [line] = narrate(installed, write_narration, tmp_path, narration)

    assert line["transcript"] == ""
    assert line["error_rate"] == 1


def test_a_worker_that_crashes_while_transcribing_is_a_structured_internal_error(installed, write_narration, tmp_path):
    narration = {"language": "zh", "voice": "fake-alice", "lines": [{"id": "a", "text": "一"}]}
    run = installed("narrate", write_narration(narration), "--out", tmp_path / "out", env={"VOXX_TEST_FAKE_CRASH": "transcribe"})

    assert assert_error(run, 1, "worker_crashed")["details"]["signal"] == "SIGKILL"
    assert not (tmp_path / "out" / "narration.json").exists()
