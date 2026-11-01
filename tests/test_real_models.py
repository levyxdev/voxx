"""Slow tests with the real Models, in the user's own $VOXX_HOME. Opt in with VOXX_TEST_REAL=1; a test skips when
its Model is not installed. Listening is still a person's job: these only catch audio that is broken or silent."""

import json
import os
import subprocess
import wave

import numpy as np
import pyloudnorm
import pytest
from conftest import VOXX

pytestmark = pytest.mark.skipif(os.environ.get("VOXX_TEST_REAL") != "1", reason="set VOXX_TEST_REAL=1 to use the real Models")

NARRATIONS = {
    "zh": {"language": "zh", "lines": [{"id": "intro", "text": "这是一个新的发送流程。"},
                                       {"id": "send", "text": "点一下发送就完成了。", "style": "语气兴奋"}]},
    "en": {"language": "en", "lines": [{"id": "intro", "text": "This is the new way to send a file."},
                                       {"id": "send", "text": "Press send, and you're done.", "style": "Excited."}]},
}


def real_voxx(*args):
    env = {k: v for k, v in os.environ.items() if not k.startswith("VOXX_TEST_")}
    process = subprocess.run([str(VOXX), *map(str, args)], capture_output=True, encoding="utf-8", timeout=900, env=env)
    return process.returncode, json.loads(process.stdout)


@pytest.fixture(scope="module")
def installed_models():
    code, result = real_voxx("models", "--installed")
    assert code == 0
    return {m["id"] for m in result["data"]["models"]}


@pytest.fixture(params=["qwen3-tts-1.7b-customvoice", "qwen3-tts-0.6b-customvoice"])
def model(request, installed_models):
    # Every narrate times its Lines' words with Qwen3-ForcedAligner and transcribes them back with Qwen3-ASR.
    for needed in (request.param, "qwen3-forcedaligner-0.6b", "qwen3-asr-0.6b"):
        if needed not in installed_models:
            pytest.skip(f"{needed} is not installed")
    return request.param


def narrate(model, narration, out):
    path = out.with_suffix(".json")
    path.write_text(json.dumps(narration, ensure_ascii=False), encoding="utf-8")
    code, result = real_voxx("narrate", path, "--out", out, "--model", model)
    assert code == 0, result
    return result["data"]["narration"]["lines"]


@pytest.mark.parametrize("language", ["zh", "en"])
def test_a_real_model_reads_every_line_to_an_audible_wav(model, language, tmp_path):
    out = tmp_path / "out"
    for line in narrate(model, NARRATIONS[language], out):
        assert line["model"] == model
        with wave.open(str(out / line["audio"])) as audio:
            assert audio.getnchannels() == 1
            assert audio.getframerate() == line["sample_rate"] == 24_000
            samples = np.frombuffer(audio.readframes(audio.getnframes()), "<i2") / 32768
        seconds = len(samples) / line["sample_rate"]
        assert 1 < seconds < 15, f"{line['id']} is {seconds:.1f} s long"
        assert np.sqrt(np.mean(samples**2)) > 0.01, f"{line['id']} is silent"
        assert abs(pyloudnorm.Meter(line["sample_rate"]).integrated_loudness(samples) - -18) <= 0.5, line["warnings"]


@pytest.mark.parametrize("language", ["zh", "en"])
def test_a_real_model_reads_short_lines_that_qwen3_asr_transcribes_almost_word_for_word(model, language, tmp_path):
    # A Model sometimes reads a Line badly, and catching that is the self-check's job; a fixed seed keeps this test
    # about the pipeline, so it fails only when the pipeline or a pinned Model changes.
    for line in narrate(model, {**NARRATIONS[language], "seed": 42}, tmp_path / "out"):
        assert line["transcript"].strip(), line["id"]
        # One slip in a short Line is allowed; broken audio or the wrong language is not.
        assert line["error_rate"] <= 0.25, (line["id"], line["text"], line["transcript"])


@pytest.mark.parametrize("language", ["zh", "en"])
def test_qwen3_forcedaligner_times_every_word_of_short_lines(model, language, tmp_path):
    out = tmp_path / "out"
    for line in narrate(model, {**NARRATIONS[language], "seed": 42}, out):
        words = line["words"]
        texts = [w["text"] for w in words]
        if language == "zh":
            assert texts == [c for c in line["text"] if c.isalnum()], texts
        else:
            assert " ".join(texts) == "".join(c for c in line["text"] if c.isalnum() or c in " '").strip(), texts
        with wave.open(str(out / line["audio"])) as audio:
            seconds = audio.getnframes() / audio.getframerate()
        previous_end = 0
        for word in words:
            assert previous_end <= word["start"] <= word["end"] <= seconds, words
            previous_end = word["end"]
        # The speech fills the audio but for 50 ms of silence at each end, so the words should too, within the
        # aligner's 80 ms steps.
        assert words[0]["start"] < 0.4 and words[-1]["end"] > seconds - 0.4, (seconds, words)


def test_the_same_seed_reads_a_line_the_same_way(model, tmp_path):
    narration = {**NARRATIONS["en"], "seed": 42}
    first, second = narrate(model, narration, tmp_path / "first"), narrate(model, narration, tmp_path / "second")

    for a, b in zip(first, second):
        assert (tmp_path / "first" / a["audio"]).read_bytes() == (tmp_path / "second" / b["audio"]).read_bytes()


# A Reference Recording made by a Preset Voice, so the test needs no recording of a real person.
REFERENCE = {"language": "zh", "voice": "serena", "seed": 42,
             "lines": [{"id": "reference", "text": "大家好，这是我录的一段参考音频，用来克隆我的声音。"}]}
CLONE_SAMPLE_RATES = {"voxcpm2": 48_000, "qwen3-tts-1.7b-base": 24_000}


@pytest.fixture(params=list(CLONE_SAMPLE_RATES))
def cloning_model(request, installed_models):
    for needed in (request.param, "qwen3-tts-1.7b-customvoice", "qwen3-forcedaligner-0.6b", "qwen3-asr-0.6b"):
        if needed not in installed_models:
            pytest.skip(f"{needed} is not installed")
    return request.param


@pytest.fixture
def cloned_voice(cloning_model, tmp_path):
    """A Cloned Voice added from a short recording, its words transcribed by Qwen3-ASR, in a project's voices dir."""
    [reference] = narrate("qwen3-tts-1.7b-customvoice", REFERENCE, tmp_path / "reference")
    voices = tmp_path / "voices"
    code, result = real_voxx("voice", "add", "me", "--ref", tmp_path / "reference" / reference["audio"],
                             "--model", cloning_model, "--voices-dir", voices)
    assert code == 0, result
    assert result["data"]["transcribed_by"] == "qwen3-asr-0.6b"
    assert result["data"]["reference_text"].strip()
    return voices


@pytest.mark.parametrize("language", ["zh", "en"])
def test_a_cloned_voice_reads_short_lines_that_qwen3_asr_transcribes_almost_word_for_word(cloning_model, cloned_voice,
                                                                                          language, tmp_path):
    out = tmp_path / "out"
    path = out.with_suffix(".json")
    path.write_text(json.dumps({**NARRATIONS[language], "voice": "me", "seed": 42}, ensure_ascii=False), encoding="utf-8")
    code, result = real_voxx("narrate", path, "--out", out, "--voices-dir", cloned_voice)

    assert code == 0, result
    for line in result["data"]["narration"]["lines"]:
        assert (line["model"], line["voice"]) == (cloning_model, "me")
        with wave.open(str(out / line["audio"])) as audio:
            assert audio.getnchannels() == 1
            assert audio.getframerate() == line["sample_rate"] == CLONE_SAMPLE_RATES[cloning_model]
            samples = np.frombuffer(audio.readframes(audio.getnframes()), "<i2") / 32768
        seconds = len(samples) / line["sample_rate"]
        assert 1 < seconds < 15, f"{line['id']} is {seconds:.1f} s long"
        assert np.sqrt(np.mean(samples**2)) > 0.01, f"{line['id']} is silent"
        assert line["error_rate"] <= 0.25, (line["id"], line["text"], line["transcript"])
