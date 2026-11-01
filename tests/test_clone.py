import json
import wave

import numpy as np
import pyloudnorm
import pytest
from conftest import assert_error, snapshot

NARRATION = {"language": "zh", "voice": "me", "lines": [{"id": "intro", "text": "这是一个新的发送流程。"},
                                                        {"id": "send", "text": "点一下发送就完成了。"}]}
SAID = "这是我自己的声音。"  # what the fake transcriber hears in a recording it did not read


def write_recording(path, rate=44_100, channels=2, lead=0.5, tail=0.7, seconds=2.0, amplitude=0.1, pitch=220):
    """A recording as a user might hand one over: a tone with silence before and after it."""
    t = np.arange(int(rate * seconds)) / rate
    tone = amplitude * np.sin(2 * np.pi * pitch * t)
    mono = np.concatenate([np.zeros(int(rate * lead)), tone, np.zeros(int(rate * tail))])
    frames = np.repeat(mono[:, None], channels, axis=1)
    with wave.open(str(path), "wb") as f:
        f.setnchannels(channels)
        f.setsampwidth(2)
        f.setframerate(rate)
        f.writeframes((frames * 32767).astype("<i2").tobytes())
    return path


@pytest.fixture
def recording(tmp_path):
    return write_recording(tmp_path / "me.wav")


def read_wav(path):
    with wave.open(str(path)) as audio:
        return audio.getnchannels(), audio.getframerate(), np.frombuffer(audio.readframes(audio.getnframes()), "<i2") / 32768


def lines(run):
    return {line["id"]: line for line in run.result["data"]["narration"]["lines"]}


def test_voice_add_stores_the_reference_recording_normalized_with_voice_json(voxx, recording):
    run = voxx("voice", "add", "me", "--ref", recording, "--ref-text", SAID)

    assert run.exit_code == 0, run.result
    voice = run.result["data"]
    path = voxx.home / "voices" / "me"
    assert voice["path"] == str(path)
    assert (voice["name"], voice["kind"], voice["reference_text"], voice["source"]) == ("me", "cloned", SAID, str(recording))
    # Without --model, the Voice is read by VoxCPM2, the default Model that clones; adding it needs no Model installed.
    assert voice["model"] == "voxcpm2"
    assert voice["transcribed_by"] is None
    stored = json.loads((path / "voice.json").read_text(encoding="utf-8"))
    assert stored == {k: voice[k] for k in ("name", "reference_text", "model", "source", "created", "transcribed_by")}
    assert stored["created"]
    channels, rate, samples = read_wav(path / "reference.wav")
    assert (channels, rate) == (1, 24_000)
    assert abs(pyloudnorm.Meter(rate).integrated_loudness(samples) - -18) <= 0.5
    sound = np.flatnonzero(np.abs(samples) > 0.01 * np.abs(samples).max())
    # The 0.5 s and 0.7 s of silence are cut to 50 ms each.
    assert abs(sound[0] / rate - 0.05) < 0.005 and abs((len(samples) - sound[-1] - 1) / rate - 0.05) < 0.005


def test_voice_add_transcribes_the_reference_recording_without_ref_text(installed, recording):
    run = installed("voice", "add", "me", "--ref", recording, "--model", "fake-clone")

    assert run.exit_code == 0, run.result
    assert run.result["data"]["reference_text"] == SAID
    assert run.result["data"]["transcribed_by"] == "fake-asr"
    stored = json.loads((installed.home / "voices" / "me" / "voice.json").read_text(encoding="utf-8"))
    assert (stored["reference_text"], stored["transcribed_by"], stored["model"]) == (SAID, "fake-asr", "fake-clone")


def test_voice_add_without_ref_text_needs_the_transcriber_installed(voxx, recording):
    run = voxx("voice", "add", "me", "--ref", recording)

    error = assert_error(run, 3, "model_not_installed")
    assert [m["model"] for m in error["details"]["missing"]] == ["qwen3-asr-0.6b"]
    assert not (voxx.home / "voices" / "me").exists()


def test_voice_add_that_hears_no_words_asks_for_ref_text(installed, recording):
    run = installed("voice", "add", "me", "--ref", recording, "--model", "fake-clone",
                    env={"VOXX_TEST_FAKE_HEARD": json.dumps({SAID: "  "})})

    assert_error(run, 2, "reference_not_transcribed")
    assert not (installed.home / "voices" / "me").exists()


def test_a_name_already_stored_is_an_argument_error_unless_overwritten(voxx, recording, tmp_path):
    assert voxx("voice", "add", "me", "--ref", recording, "--ref-text", "一").exit_code == 0
    voices = voxx.home / "voices"
    before = snapshot(voices / "me")

    assert_error(voxx("voice", "add", "me", "--ref", recording, "--ref-text", "二"), 2, "voice_exists")
    assert snapshot(voices / "me") == before

    louder = write_recording(tmp_path / "other.wav", pitch=440)
    run = voxx("voice", "add", "me", "--ref", louder, "--ref-text", "二", "--overwrite")
    assert run.exit_code == 0, run.result
    assert run.result["data"]["reference_text"] == "二"
    assert snapshot(voices / "me") != before
    # Nothing is left behind from staging or from the Voice it replaced.
    assert [p.name for p in voices.iterdir()] == ["me"]


def test_a_preset_voice_name_cannot_name_a_cloned_voice(installed, recording):
    assert_error(installed("voice", "add", "fake-alice", "--ref", recording, "--ref-text", "一"), 2, "voice_exists")


@pytest.mark.parametrize("name", [".hidden", "a/b", "", "a\nb"])
def test_a_cloned_voice_name_must_be_a_safe_file_name(voxx, recording, name):
    assert_error(voxx("voice", "add", name, "--ref", recording, "--ref-text", "一"), 2, "invalid_voice_name")


def test_a_missing_unreadable_or_silent_reference_is_an_argument_error(voxx, tmp_path):
    assert_error(voxx("voice", "add", "me", "--ref", tmp_path / "nope.wav", "--ref-text", "一"), 2, "reference_not_found")
    (tmp_path / "notes.wav").write_text("not audio")
    assert_error(voxx("voice", "add", "me", "--ref", tmp_path / "notes.wav", "--ref-text", "一"), 2, "unreadable_reference")
    silent = write_recording(tmp_path / "silent.wav", amplitude=0)
    assert_error(voxx("voice", "add", "me", "--ref", silent, "--ref-text", "一"), 2, "silent_reference")
    assert_error(voxx("voice", "add", "me", "--ref", silent, "--ref-text", " "), 2, "invalid_reference_text")
    assert not (voxx.home / "voices" / "me").exists()


def test_voice_add_with_a_model_that_cannot_clone_is_unsupported(voxx, recording):
    error = assert_error(voxx("voice", "add", "me", "--ref", recording, "--ref-text", "一", "--model", "fake-tts"),
                         4, "capability_unsupported")
    assert error["details"] == {"model": "fake-tts", "capability": "clone"}


def test_a_crash_while_adding_a_voice_stores_nothing(installed, recording):
    run = installed("voice", "add", "me", "--ref", recording, "--model", "fake-clone", env={"VOXX_TEST_FAKE_CRASH": "transcribe"})

    assert_error(run, 1, "worker_crashed")
    assert list((installed.home / "voices").iterdir()) == []


def test_narrate_reads_a_cloned_voice_with_the_model_it_was_added_with(installed, recording, write_narration, tmp_path):
    assert installed("voice", "add", "me", "--ref", recording, "--model", "fake-clone").exit_code == 0
    out = tmp_path / "out"
    narration = {**NARRATION, "lines": [NARRATION["lines"][0], {**NARRATION["lines"][1], "style": "语气兴奋"}]}
    run = installed("narrate", write_narration(narration), "--out", out)

    assert run.exit_code == 0, run.result
    intro, send = lines(run).values()
    for line in (intro, send):
        assert (line["model"], line["voice"], line["sample_rate"]) == ("fake-clone", "me", 48_000)
        assert read_wav(out / line["audio"])[1] == 48_000
        # A cloned Line is timed and checked like any other.
        assert line["words"] and line["error_rate"] == 0
    assert intro["warnings"] == []
    # Neither Model that clones follows style.
    assert [w["code"] for w in send["warnings"]] == ["style_ignored"]


def test_narrate_reads_a_cloned_voice_with_the_model_given_to_model(installed, recording, write_narration, tmp_path):
    assert installed("voice", "add", "me", "--ref", recording, "--model", "fake-clone").exit_code == 0
    run = installed("narrate", write_narration(NARRATION), "--out", tmp_path / "out", "--model", "fake-clone-alt")

    assert run.exit_code == 0, run.result
    assert {(l["model"], l["sample_rate"]) for l in lines(run).values()} == {("fake-clone-alt", 24_000)}


@pytest.mark.parametrize("add_with, narrate_with, reader", [
    ([], [], "voxcpm2"),
    (["--model", "qwen3-tts-1.7b-base"], [], "qwen3-tts-1.7b-base"),
    ([], ["--model", "qwen3-tts-1.7b-base"], "qwen3-tts-1.7b-base"),
])
def test_a_cloned_voice_is_read_by_voxcpm2_unless_qwen3_base_is_asked_for(voxx, recording, write_narration, tmp_path,
                                                                          add_with, narrate_with, reader):
    assert voxx("voice", "add", "me", "--ref", recording, "--ref-text", SAID, *add_with).exit_code == 0
    run = voxx("narrate", write_narration(NARRATION), "--out", tmp_path / "out", *narrate_with)

    # Neither real Model is installed here, so the one that would read the Lines is the one missing.
    error = assert_error(run, 3, "model_not_installed")
    assert [m["model"] for m in error["details"]["missing"]] == [reader]


def test_a_model_that_cannot_clone_cannot_read_a_cloned_voice(installed, recording, write_narration, tmp_path):
    assert installed("voice", "add", "me", "--ref", recording, "--model", "fake-clone").exit_code == 0
    run = installed("narrate", write_narration(NARRATION), "--out", tmp_path / "out", "--model", "fake-tts")

    error = assert_error(run, 4, "capability_unsupported")
    assert error["details"] == {"model": "fake-tts", "capability": "clone"}


def test_each_cloned_voice_reads_in_its_own_voice(installed, write_narration, tmp_path):
    for name, pitch in (("low", 150), ("high", 600)):
        recording = write_recording(tmp_path / f"{name}.wav", pitch=pitch)
        assert installed("voice", "add", name, "--ref", recording, "--ref-text", SAID, "--model", "fake-clone").exit_code == 0
    narration = {"language": "zh", "seed": 7, "lines": [{"id": "a", "text": "一样的话。", "voice": "low"},
                                                        {"id": "b", "text": "一样的话。", "voice": "high"}]}
    out = tmp_path / "out"
    assert installed("narrate", write_narration(narration), "--out", out).exit_code == 0

    assert (out / "a.wav").read_bytes() != (out / "b.wav").read_bytes()


def test_voices_dir_stores_and_finds_cloned_voices_in_a_project(installed, recording, write_narration, tmp_path):
    project = tmp_path / "project" / "voices"
    run = installed("voice", "add", "me", "--ref", recording, "--model", "fake-clone", "--voices-dir", project)

    assert run.exit_code == 0, run.result
    assert run.result["data"]["path"] == str(project / "me")
    assert (project / "me" / "voice.json").exists()
    assert not (installed.home / "voices" / "me").exists()
    cloned = [v["name"] for v in installed("voices", "--voices-dir", project).result["data"]["voices"] if v["kind"] == "cloned"]
    assert cloned == ["me"]
    assert all(v["kind"] == "preset" for v in installed("voices").result["data"]["voices"])

    path = write_narration(NARRATION)
    run = installed("narrate", path, "--out", tmp_path / "out", "--voices-dir", project)
    assert run.exit_code == 0, run.result
    assert {l["voice"] for l in lines(run).values()} == {"me"}
    # Without --voices-dir, the Voice is looked for in $VOXX_HOME/voices.
    error = assert_error(installed("narrate", path, "--out", tmp_path / "out2"), 2, "unknown_voice")
    assert error["details"]["voices_dir"] == str(installed.home / "voices")


def test_voices_lists_preset_and_cloned_voices(installed, recording):
    assert installed("voice", "add", "me", "--ref", recording, "--model", "fake-clone").exit_code == 0
    voices = installed("voices").result["data"]["voices"]

    assert [v["kind"] for v in voices].count("preset") == len(voices) - 1
    me = voices[-1]
    assert (me["name"], me["kind"], me["model"], me["reference_text"]) == ("me", "cloned", "fake-clone", SAID)
    assert {"model": "fake-clone", "installed": True} in me["models"]
    assert {"model": "voxcpm2", "installed": False} in me["models"]
    assert "zh" in me["languages"]


def test_an_unknown_voice_lists_the_cloned_voices_too(installed, recording, write_narration, tmp_path):
    assert installed("voice", "add", "me", "--ref", recording, "--model", "fake-clone").exit_code == 0
    run = installed("narrate", write_narration({**NARRATION, "voice": "you"}), "--out", tmp_path / "out")

    error = assert_error(run, 2, "unknown_voice")
    assert {"fake-alice", "me"} <= set(error["details"]["known_voices"])


def test_a_broken_cloned_voice_is_an_argument_error(installed, recording, write_narration, tmp_path):
    assert installed("voice", "add", "me", "--ref", recording, "--model", "fake-clone").exit_code == 0
    (installed.home / "voices" / "me" / "reference.wav").unlink()

    assert_error(installed("narrate", write_narration(NARRATION), "--out", tmp_path / "out"), 2, "invalid_cloned_voice")


def test_line_reads_a_cloned_voice_and_flags_a_kept_line_whose_voice_is_now_cloned(installed, recording, write_narration,
                                                                                    tmp_path):
    assert installed("voice", "add", "me", "--ref", recording, "--model", "fake-clone").exit_code == 0
    out = tmp_path / "out"
    assert installed("narrate", write_narration({**NARRATION, "voice": "fake-alice"}), "--out", out).exit_code == 0

    run = installed("narrate", write_narration(NARRATION), "--out", out, "--line", "intro")

    assert run.exit_code == 0, run.result
    intro, send = lines(run).values()
    assert (intro["model"], intro["voice"]) == ("fake-clone", "me")
    assert (send["model"], send["voice"]) == ("fake-tts", "fake-alice")
    assert [w["code"] for w in send["warnings"]] == ["stale_audio"]
    assert "'me'" in send["warnings"][0]["message"]
