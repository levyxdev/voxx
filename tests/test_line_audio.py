"""What every Line's WAV sounds like after voxx finishes it: one loudness, short silences, the Engine's own sample rate."""

import wave

import numpy as np
import pyloudnorm

TEN_CHARS = "一二三四五六七八九十"  # the fake Engine reads it as a 0.6 s tone
# Seeds 0-3 make the fake Engine read at amplitudes from 0.01 to 0.7, with 0 to 1.2 s of silence around the tone.
SHAPED = {"language": "zh", "voice": "fake-alice", "lines": [{"id": f"s{seed}", "text": TEN_CHARS, "seed": seed} for seed in range(4)]}


def read_wav(path):
    with wave.open(str(path)) as audio:
        samples = np.frombuffer(audio.readframes(audio.getnframes()), "<i2") / 32768
        return samples, audio.getframerate(), audio.getnchannels()


def narrated(installed, write_narration, tmp_path, narration):
    out = tmp_path / "out"
    run = installed("narrate", write_narration(narration), "--out", out)
    assert run.exit_code == 0, run.result
    return [(line, *read_wav(out / line["audio"])) for line in run.result["data"]["narration"]["lines"]]


def test_every_line_is_normalised_to_minus_18_lufs(installed, write_narration, tmp_path):
    for line, samples, rate, channels in narrated(installed, write_narration, tmp_path, SHAPED):
        assert abs(pyloudnorm.Meter(rate).integrated_loudness(samples) - -18) <= 0.5, line["id"]


def test_silence_before_and_after_every_line_is_50_ms_and_the_speech_is_kept_whole(installed, write_narration, tmp_path):
    for line, samples, rate, channels in narrated(installed, write_narration, tmp_path, SHAPED):
        sound = np.flatnonzero(samples)
        lead, tail = sound[0] / rate, (len(samples) - 1 - sound[-1]) / rate
        assert abs(lead - 0.05) <= 0.003 and abs(tail - 0.05) <= 0.003, (line["id"], lead, tail)
        assert abs(len(samples) / rate - (0.6 + 0.1)) <= 0.003, line["id"]


def test_every_line_is_mono_at_the_engines_own_sample_rate(installed, write_narration, tmp_path):
    for line, samples, rate, channels in narrated(installed, write_narration, tmp_path, SHAPED):
        assert channels == 1
        assert rate == line["sample_rate"] == 24_000  # the fake Engine's native rate


CEILING = 10 ** (-1 / 20)  # -1 dBFS


def test_a_sharp_peak_is_limited_so_the_line_still_reaches_minus_18_lufs_without_clipping(installed, write_narration, tmp_path):
    # Seed 4: a 0.01 tone with one 0.1 sample, which -18 LUFS alone would push past full scale.
    narration = {**SHAPED, "lines": [{"id": "steady", "text": TEN_CHARS, "seed": 0}, {"id": "peaky", "text": TEN_CHARS, "seed": 4}]}
    for line, samples, rate, _ in narrated(installed, write_narration, tmp_path, narration):
        assert np.abs(samples).max() <= CEILING, line["id"]
        assert abs(pyloudnorm.Meter(rate).integrated_loudness(samples) - -18) <= 0.5, line["id"]
        assert line["warnings"] == []


def test_a_line_too_peaky_to_reach_minus_18_lufs_without_clipping_stays_below_full_scale_and_warns(installed, write_narration,
                                                                                                    tmp_path):
    # Seed 6: a 0.01 tone with a 0.9 sample every 10 ms, so limiting the peaks turns the whole Line down.
    narration = {**SHAPED, "lines": [{"id": "clicks", "text": TEN_CHARS, "seed": 6}]}
    [(line, samples, rate, _)] = narrated(installed, write_narration, tmp_path, narration)

    assert np.abs(samples).max() <= CEILING
    assert pyloudnorm.Meter(rate).integrated_loudness(samples) < -18.5
    assert [w["code"] for w in line["warnings"]] == ["loudness_below_target"]


def test_a_line_shorter_than_the_loudness_meters_block_is_normalised_too(installed, write_narration, tmp_path):
    # A 0.06 s tone in the steady shapes and in the one with a sharp peak, which the limiter turns down for most of it.
    narration = {**SHAPED, "lines": [{"id": f"s{seed}", "text": "一", "seed": seed} for seed in range(5)]}
    *steady, (_, peaky, _, _) = narrated(installed, write_narration, tmp_path, narration)

    for line, samples, rate, _ in steady:
        assert len(samples) / rate < 0.4
        meter = pyloudnorm.Meter(rate, block_size=(len(samples) - 1) / rate)
        assert abs(meter.integrated_loudness(samples) - -18) <= 0.5, line["id"]
    assert np.abs(peaky).max() <= CEILING


def test_a_line_read_as_near_silence_is_not_amplified_and_warns(installed, write_narration, tmp_path):
    narration = {**SHAPED, "lines": [{"id": "silent", "text": TEN_CHARS, "seed": 5}]}  # seed 5: a -100 dBFS tone
    [(line, samples, rate, _)] = narrated(installed, write_narration, tmp_path, narration)

    assert len(samples) > 0 and not samples.any()
    assert [w["code"] for w in line["warnings"]] == ["silent"]
