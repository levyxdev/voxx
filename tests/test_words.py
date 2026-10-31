"""Word Timing: every Line comes back with when each of its words is spoken in the audio voxx wrote."""

import json
import math
import shutil
import wave

import pytest

ALIGNED = "VOXX_TEST_FAKE_ALIGNED"


def one_line(text, language="zh", **fields):
    return {"language": language, "voice": "fake-alice", "lines": [{"id": "a", "text": text, **fields}]}


def narrate(installed, write_narration, tmp_path, narration, aligned=None):
    env = {ALIGNED: json.dumps(aligned, ensure_ascii=False)} if aligned else None
    run = installed("narrate", write_narration(narration), "--out", tmp_path / "out", env=env)
    assert run.exit_code == 0, run.result
    return run.result["data"]["narration"]["lines"]


def duration(tmp_path, line):
    with wave.open(str(tmp_path / "out" / line["audio"])) as audio:
        return audio.getnframes() / audio.getframerate()


def test_a_line_has_the_words_the_aligner_found_in_whole_milliseconds(installed, write_narration, tmp_path):
    aligned = {"点一下": [["点", 0.05, 0.1104], ["一", 0.1104, 0.17], ["下", 0.17, 0.2296]]}
    [line] = narrate(installed, write_narration, tmp_path, one_line("点一下"), aligned)

    assert line["words"] == [{"text": "点", "start": 0.05, "end": 0.11}, {"text": "一", "start": 0.11, "end": 0.17},
                             {"text": "下", "start": 0.17, "end": 0.23}]


def test_words_are_timed_on_the_audio_after_its_leading_silence_is_trimmed(installed, write_narration, tmp_path):
    # Seed 3 makes the fake Engine read 1.2 s of silence before the Line; the fake aligner spreads the words evenly
    # over the sound it hears in the WAV voxx wrote.
    [line] = narrate(installed, write_narration, tmp_path, one_line("点一下发送", seed=3))

    seconds = duration(tmp_path, line)
    assert seconds < 1.2
    assert [w["text"] for w in line["words"]] == list("点一下发送")
    assert line["words"][0]["start"] == pytest.approx(0.05, abs=0.002)
    assert line["words"][-1]["end"] == pytest.approx(seconds - 0.05, abs=0.002)


@pytest.mark.parametrize("language, text, words", [
    ("zh", "点一下「发送」，就完成了。", list("点一下发送就完成了")),
    ("zh", "点一下 Send 按钮", ["点", "一", "下", "Send", "按", "钮"]),
    ("en", "Press send, and you're done!", ["Press", "send", "and", "you're", "done"]),
])
def test_words_spell_out_the_line_by_character_in_chinese_and_by_word_in_english(installed, write_narration, tmp_path,
                                                                                 language, text, words):
    [line] = narrate(installed, write_narration, tmp_path, one_line(text, language))

    assert [w["text"] for w in line["words"]] == words
    assert_well_timed(line["words"], duration(tmp_path, line))


def assert_well_timed(words, seconds):
    previous_end = 0
    for word in words:
        assert previous_end <= word["start"] <= word["end"] <= seconds, words
        previous_end = word["end"]


def test_aligner_times_out_of_order_or_outside_the_audio_are_kept_within_it_and_in_order(installed, write_narration, tmp_path):
    aligned = {"点一下": [["点", -0.1, 0.12], ["一", 0.1, 0.05], ["下", 0.2, 9.0]]}
    [line] = narrate(installed, write_narration, tmp_path, one_line("点一下"), aligned)

    last_end = math.floor(duration(tmp_path, line) * 1000) / 1000
    assert line["words"] == [{"text": "点", "start": 0, "end": 0.12}, {"text": "一", "start": 0.12, "end": 0.12},
                             {"text": "下", "start": 0.2, "end": last_end}]


def test_a_line_the_aligner_fails_on_has_no_words_and_a_warning(installed, write_narration, tmp_path):
    narration = {"language": "zh", "voice": "fake-alice",
                 "lines": [{"id": "a", "text": "点一下"}, {"id": "b", "text": "就完成了"}]}
    a, b = narrate(installed, write_narration, tmp_path, narration, {"点一下": "out of memory"})

    assert "words" not in a
    [warning] = a["warnings"]
    assert warning["code"] == "not_aligned"
    assert "out of memory" in warning["message"]
    assert (tmp_path / "out" / "a.wav").exists()
    assert [w["text"] for w in b["words"]] == list("就完成了")


def test_aligned_words_that_do_not_spell_out_the_line_are_dropped_with_a_warning(installed, write_narration, tmp_path):
    [line] = narrate(installed, write_narration, tmp_path, one_line("点一下"), {"点一下": [["点", 0.05, 0.1]]})

    assert "words" not in line
    assert [w["code"] for w in line["warnings"]] == ["not_aligned"]


def test_a_line_in_a_language_no_model_aligns_has_no_words_and_does_not_need_the_aligner(installed, write_narration, tmp_path):
    shutil.rmtree(installed.home / "models" / "fake-aligner")
    [line] = narrate(installed, write_narration, tmp_path, one_line("Bonjour.", "fr"))

    assert "words" not in line
    assert "not_aligned" in [w["code"] for w in line["warnings"]]


def test_narrate_without_the_aligner_installed_reads_every_line_without_words_and_warns(installed, write_narration,
                                                                                       tmp_path, hub):
    shutil.rmtree(installed.home / "models" / "fake-aligner")
    narration = {"language": "zh", "voice": "fake-alice", "lines": [{"id": "a", "text": "点一下"}, {"id": "b", "text": "就完成了"}]}
    lines = narrate(installed, write_narration, tmp_path, narration)

    for line in lines:
        assert (tmp_path / "out" / line["audio"]).exists()
        assert "words" not in line
        # The transcriber is installed, so the Line is still checked.
        assert line["error_rate"] == 0
        [warning] = line["warnings"]
        assert warning["code"] == "aligner_not_installed"
        assert warning["details"] == {"model": "fake-aligner", "size_bytes": 4096, "license": "Apache-2.0",
                                      "license_url": "https://huggingface.co/voxx-test/fake-aligner",
                                      "command": "voxx install fake-aligner"}
    assert hub.requests == []
