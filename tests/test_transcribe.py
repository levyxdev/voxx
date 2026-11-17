"""`voxx transcribe`: the Transcript of an audio or video file, Passage by Passage, with Word Timings on request."""

import json
import shutil
import subprocess
import wave

import numpy as np
import pytest
from conftest import assert_error

SPOKEN = "VOXX_TEST_FAKE_SPOKEN"
RATE = 8_000


def write_media(path, seconds, quiet=(), rate=RATE):
    """A tone `seconds` long, silent for a second from each of the moments in `quiet`."""
    t = np.arange(int(seconds * rate)) / rate
    samples = 0.3 * np.sin(2 * np.pi * 220 * t)
    for start in quiet:
        samples[int(start * rate):int((start + 1) * rate)] = 0
    with wave.open(str(path), "wb") as f:
        f.setnchannels(1)
        f.setsampwidth(2)
        f.setframerate(rate)
        f.writeframes((samples * 32767).astype("<i2").tobytes())
    return path


def spoken(*passages):
    """What the fake Engine hears in each Passage it transcribes, in order, as [text, language]."""
    return {SPOKEN: json.dumps([list(p) for p in passages], ensure_ascii=False)}


def transcribe(voxx, *args, env=None):
    run = voxx("transcribe", *args, env=env)
    assert run.exit_code == 0, run.result
    return run.result["data"], run.events


def test_a_short_recording_is_one_passage_in_the_language_heard(installed, tmp_path):
    media = write_media(tmp_path / "talk.wav", 4)
    data, events = transcribe(installed, media, env=spoken(("这是一段录音。", "zh")))

    assert data["source"] == str(media)
    assert data["model"] == "fake-asr-large"
    assert data["language"] == "zh"
    assert data["text"] == "这是一段录音。"
    assert data["duration"] == 4
    assert data["passages"] == [{"start": 0, "end": 4, "language": "zh", "text": "这是一段录音。", "warnings": []}]
    assert data["warnings"] == []
    assert [e["event"] for e in events if e["event"].startswith("passage")] == ["passage_done"]


def test_a_long_recording_is_cut_where_it_is_quiet_into_passages_of_at_most_five_minutes(installed, tmp_path):
    media = write_media(tmp_path / "meeting.wav", 660, quiet=(270, 560))
    data, events = transcribe(installed, media, env=spoken(("第一段。", "zh"), ("第二段。", "zh"), ("third part.", "en")))

    passages = data["passages"]
    assert [p["text"] for p in passages] == ["第一段。", "第二段。", "third part."]
    assert [p["language"] for p in passages] == ["zh", "zh", "en"]
    assert passages[0]["start"] == 0 and passages[-1]["end"] == data["duration"] == 660
    for before, after in zip(passages, passages[1:]):
        assert before["end"] == after["start"]
    assert 270 <= passages[0]["end"] <= 271 and 560 <= passages[1]["end"] <= 561
    assert all(p["end"] - p["start"] <= 300 for p in passages)
    # No space between two Chinese passages; one before the English one.
    assert data["text"] == "第一段。第二段。 third part."
    # Most of the audio is Chinese.
    assert data["language"] == "zh"
    assert [(e["index"], e["total"]) for e in events if e["event"] == "passage_done"] == [(1, 3), (2, 3), (3, 3)]


def test_a_recording_with_no_quiet_moment_is_cut_at_five_minutes(installed, tmp_path):
    data, _ = transcribe(installed, write_media(tmp_path / "hum.wav", 400), env=spoken(("a", "en"), ("b", "en")))

    assert [(p["start"], p["end"]) for p in data["passages"]][0][1] <= 300
    assert len(data["passages"]) == 2


def test_language_names_the_language_of_every_passage(installed, tmp_path):
    media = write_media(tmp_path / "talk.wav", 4)
    data, _ = transcribe(installed, media, "--language", "yue", env=spoken(("呢段係廣東話。", None)))

    assert data["language"] == data["passages"][0]["language"] == "yue"


def test_model_names_the_transcribing_model(installed, tmp_path):
    data, _ = transcribe(installed, write_media(tmp_path / "talk.wav", 2), "--model", "fake-asr")

    assert data["model"] == "fake-asr"


def test_the_best_installed_transcribing_model_is_used_when_none_is_named(installed, tmp_path):
    (installed.home / "models" / "fake-asr-large" / "voxx-install.json").unlink()
    data, _ = transcribe(installed, write_media(tmp_path / "talk.wav", 2))

    assert data["model"] == "fake-asr"


def test_without_a_transcribing_model_installed_it_asks_for_the_best_one(voxx, tmp_path):
    error = assert_error(voxx("transcribe", write_media(tmp_path / "talk.wav", 2)), 3, "model_not_installed")

    assert [m["model"] for m in error["details"]["missing"]] == ["fake-asr-large"]


def test_a_model_that_cannot_transcribe_or_read_the_language_is_refused(installed, tmp_path):
    media = write_media(tmp_path / "talk.wav", 2)

    error = assert_error(installed("transcribe", media, "--model", "fake-tts"), 4, "capability_unsupported")
    assert error["details"]["capability"] == "transcribe"
    error = assert_error(installed("transcribe", media, "--language", "fr"), 4, "unsupported_language")
    assert error["details"]["languages"] == ["zh", "en", "yue"]
    assert_error(installed("transcribe", media, "--language", "ZH"), 2, "invalid_language")


def test_a_missing_or_undecodable_file_is_an_input_error(installed, tmp_path):
    error = assert_error(installed("transcribe", tmp_path / "nowhere.wav"), 2, "media_not_found")
    assert error["details"]["media"] == str(tmp_path / "nowhere.wav")

    junk = tmp_path / "junk.wav"
    junk.write_bytes(b"not audio at all" * 64)
    error = assert_error(installed("transcribe", junk), 2, "unreadable_media")
    assert "ffmpeg" in error["hint"]


def test_an_empty_recording_is_an_input_error(installed, tmp_path):
    assert_error(installed("transcribe", write_media(tmp_path / "empty.wav", 0)), 2, "silent_media")


def test_silence_has_an_empty_transcript_and_no_language(installed, tmp_path):
    media = tmp_path / "quiet.wav"
    with wave.open(str(media), "wb") as f:
        f.setnchannels(1)
        f.setsampwidth(2)
        f.setframerate(RATE)
        f.writeframes(bytes(RATE * 4))
    data, _ = transcribe(installed, media)

    assert data["text"] == "" and data["language"] is None
    assert data["passages"][0]["language"] is None


def test_words_are_timed_from_the_start_of_the_recording(installed, tmp_path):
    media = write_media(tmp_path / "meeting.wav", 400, quiet=(250,))
    data, _ = transcribe(installed, media, "--words", env=spoken(("first part", "en"), ("second part here", "en")))

    first, second = data["passages"]
    assert [w["text"] for w in first["words"]] == ["first", "part"]
    assert [w["text"] for w in second["words"]] == ["second", "part", "here"]
    for passage in (first, second):
        for word in passage["words"]:
            assert passage["start"] <= word["start"] <= word["end"] <= passage["end"]
    assert second["words"][0]["start"] >= 250


def test_without_words_no_passage_is_timed(installed, tmp_path):
    data, _ = transcribe(installed, write_media(tmp_path / "talk.wav", 2), env=spoken(("hello there", "en")))

    assert "words" not in data["passages"][0]


def test_a_passage_in_a_language_no_aligner_reads_has_no_words(installed, tmp_path):
    media = write_media(tmp_path / "meeting.wav", 400, quiet=(250,))
    data, _ = transcribe(installed, media, "--words", env=spoken(("呢段係廣東話", "yue"), ("now English", "en")))

    cantonese, english = data["passages"]
    assert "words" not in cantonese
    assert [w["code"] for w in cantonese["warnings"]] == ["not_aligned"]
    assert [w["text"] for w in english["words"]] == ["now", "English"]


def test_words_without_the_aligner_installed_is_a_warning(installed, tmp_path):
    (installed.home / "models" / "fake-aligner" / "voxx-install.json").unlink()
    data, _ = transcribe(installed, write_media(tmp_path / "talk.wav", 2), "--words", env=spoken(("hello", "en")))

    assert "words" not in data["passages"][0]
    [warning] = data["warnings"]
    assert warning["code"] == "aligner_not_installed"
    assert warning["details"]["command"] == "voxx install fake-aligner"


@pytest.mark.skipif(shutil.which("ffmpeg") is None, reason="needs ffmpeg to make a video")
def test_a_video_is_transcribed_from_its_audio_track(installed, tmp_path):
    audio = write_media(tmp_path / "voice.wav", 3)
    video = tmp_path / "demo.mkv"
    subprocess.run(["ffmpeg", "-loglevel", "error", "-f", "lavfi", "-i", "color=c=black:s=64x64:d=3", "-i", str(audio),
                    "-c:v", "libx264", "-c:a", "aac", "-shortest", str(video)], check=True)
    data, _ = transcribe(installed, video, env=spoken(("视频里的话。", "zh")))

    assert data["text"] == "视频里的话。"
    assert 2.9 <= data["duration"] <= 3.1
