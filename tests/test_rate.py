"""Rate: a Line's audio played faster or slower than the Model read it, at the same pitch (levyxdev/voxx#47)."""

import json
import wave

import numpy as np
import pytest
from conftest import assert_error


def narration(rate=None, line_rate=None, text="这是一句用来测语速的旁白，要读得足够长，长度才测得准。"):
    line = {"id": "a", "text": text, **({"rate": line_rate} if line_rate is not None else {})}
    return {"language": "zh", "voice": "fake-alice", "seed": 7, **({"rate": rate} if rate is not None else {}),
            "lines": [line]}


@pytest.mark.parametrize("given, at", [
    (narration(rate=0.49), "$.rate"),
    (narration(rate=2.01), "$.rate"),
    (narration(line_rate="fast"), "$.lines[0].rate"),
    (narration(line_rate=True), "$.lines[0].rate"),
])
def test_a_rate_out_of_range_or_not_a_number_names_where_it_is(installed, write_narration, tmp_path, given, at):
    run = installed("narrate", write_narration(given), "--out", tmp_path / "out")

    assert assert_error(run, 2, "invalid_narration")["details"] == {"at": at}


def narrate_one(installed, write_narration, tmp_path, name, given):
    out = tmp_path / name
    run = installed("narrate", write_narration(given, f"{name}.json"), "--out", out)
    assert run.exit_code == 0, run.result
    line = run.result["data"]["narration"]["lines"][0]
    return line, out / line["audio"]


def samples_of(path):
    with wave.open(str(path)) as audio:
        return np.frombuffer(audio.readframes(audio.getnframes()), "<i2"), audio.getframerate()


def speech_seconds(path):
    """How long the speech lasts, without the silence every Line keeps before and after it."""
    samples, sample_rate = samples_of(path)
    sound = np.flatnonzero(samples)
    return (sound[-1] + 1 - sound[0]) / sample_rate


def test_a_line_with_a_rate_is_that_many_times_shorter(installed, write_narration, tmp_path):
    _, unstretched = narrate_one(installed, write_narration, tmp_path, "as-read", narration())
    _, stretched = narrate_one(installed, write_narration, tmp_path, "faster", narration(rate=1.25))

    assert speech_seconds(stretched) == pytest.approx(speech_seconds(unstretched) / 1.25, rel=0.02)


def frequency_of(path):
    """The frequency of the fake Engine's tone, from the peak of its spectrum, finely sampled."""
    samples, sample_rate = samples_of(path)
    spectrum = np.abs(np.fft.rfft(samples, n=2**22))
    return np.argmax(spectrum) * sample_rate / 2**22


@pytest.mark.parametrize("rate", [0.5, 0.8, 1.25, 2.0])
def test_a_rate_keeps_the_pitch(installed, write_narration, tmp_path, rate):
    _, unstretched = narrate_one(installed, write_narration, tmp_path, "as-read", narration())
    _, stretched = narrate_one(installed, write_narration, tmp_path, "stretched", narration(rate=rate))

    assert frequency_of(stretched) == pytest.approx(frequency_of(unstretched), rel=0.01)


def test_words_are_timed_on_the_stretched_audio(installed, write_narration, tmp_path):
    line, stretched = narrate_one(installed, write_narration, tmp_path, "slower", narration(line_rate=0.8))

    samples, sample_rate = samples_of(stretched)
    sound = np.flatnonzero(samples)
    # The fake aligner spreads the words evenly over the sound in the audio it is given.
    assert line["words"][0]["start"] == pytest.approx(sound[0] / sample_rate, abs=0.001)
    assert line["words"][-1]["end"] == pytest.approx((sound[-1] + 1) / sample_rate, abs=0.001)


def test_a_line_rate_overrides_the_narration_rate(installed, write_narration, tmp_path):
    line, overridden = narrate_one(installed, write_narration, tmp_path, "overridden", narration(rate=2.0, line_rate=1.25))
    _, faster = narrate_one(installed, write_narration, tmp_path, "faster", narration(rate=1.25))

    assert overridden.read_bytes() == faster.read_bytes()
    # The completed Narration keeps rate as given.
    assert line["rate"] == 1.25
    completed = json.loads((overridden.parent / "narration.json").read_text(encoding="utf-8"))
    assert completed["rate"] == 2.0


@pytest.mark.parametrize("rate", [1, 1.0])
def test_a_rate_of_one_leaves_the_audio_as_the_model_read_it(installed, write_narration, tmp_path, rate):
    _, as_read = narrate_one(installed, write_narration, tmp_path, "as-read", narration())
    _, one = narrate_one(installed, write_narration, tmp_path, "one", narration(rate=rate))

    assert one.read_bytes() == as_read.read_bytes()
