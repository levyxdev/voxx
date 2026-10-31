"""Test-only Engine: deterministic tones and no model files. Registered only when VOXX_TEST_FAKE_ENGINE=1."""

import json
import os
import signal
import unicodedata
import wave
import zlib
from typing import NamedTuple

import numpy as np

SAMPLE_RATE = 24_000
SECONDS_PER_CHAR = 0.06
# "load", "synthesize", "transcribe" or "align": the worker is killed at that step, as the OS does when memory runs out.
CRASH_ENV = "VOXX_TEST_FAKE_CRASH"
# A JSON object from a Line's text to what the fake Engine transcribes instead; any other Line is transcribed as written.
HEARD_ENV = "VOXX_TEST_FAKE_HEARD"
# A JSON object from a Line's text to the [word, start, end] list the fake Engine aligns it to instead, or to the
# error it fails with; any other Line's words are spread evenly over the sound in its WAV.
ALIGNED_ENV = "VOXX_TEST_FAKE_ALIGNED"


class Shape(NamedTuple):
    amplitude: float
    lead: float  # seconds of silence before the tone
    tail: float  # seconds of silence after it
    spike: float = 0  # height of one-sample spikes spread evenly through the tone
    spikes: int = 1


# Seeds 0-6 read in these shapes, so tests can hand the postprocessing different audio; every other seed reads in the first.
SHAPES = [Shape(0.2, 0.25, 0.35), Shape(0.01, 0.0, 0.8), Shape(0.7, 0.6, 0.0), Shape(0.05, 1.2, 0.02),
          Shape(0.01, 0.1, 0.1, spike=0.1), Shape(1e-5, 0.1, 0.1), Shape(0.01, 0.1, 0.1, spike=0.9, spikes=60)]


class FakeEngine:
    # A tone carries no words, so the fake Engine transcribes the text it last read in this worker.
    last_read = None

    def load(self, path, capability):
        _crash_if("load")

    def synthesize(self, text, *, model, voice, style, language, seed):
        _crash_if("synthesize")
        FakeEngine.last_read = text
        # The tone's pitch follows the seed, the Voice and the style, so tests can tell what reached the Engine.
        frequency = 200 + np.random.default_rng([seed, zlib.crc32(voice.encode()), zlib.crc32((style or "").encode())]).integers(0, 2000)
        shape = SHAPES[seed] if seed < len(SHAPES) else SHAPES[0]
        t = np.arange(int(SAMPLE_RATE * len(text) * SECONDS_PER_CHAR)) / SAMPLE_RATE
        tone = shape.amplitude * np.sin(2 * np.pi * frequency * t)
        if shape.spike:
            tone[(2 * np.arange(shape.spikes) + 1) * len(tone) // (2 * shape.spikes)] = shape.spike
        lead, tail = np.zeros(int(SAMPLE_RATE * shape.lead)), np.zeros(int(SAMPLE_RATE * shape.tail))
        return np.concatenate([lead, tone, tail]).astype(np.float32), SAMPLE_RATE

    def transcribe(self, path, *, model, language):
        _crash_if("transcribe")
        with wave.open(str(path)) as audio:
            if not any(audio.readframes(audio.getnframes())):
                return ""
        return json.loads(os.environ.get(HEARD_ENV, "{}")).get(FakeEngine.last_read, FakeEngine.last_read)

    def align(self, path, *, model, text, language):
        _crash_if("align")
        aligned = json.loads(os.environ.get(ALIGNED_ENV, "{}")).get(text)
        if isinstance(aligned, str):
            raise RuntimeError(aligned)
        if aligned is not None:
            return [tuple(word) for word in aligned]
        with wave.open(str(path)) as audio:
            rate = audio.getframerate()
            samples = np.frombuffer(audio.readframes(audio.getnframes()), "<i2")
        sound = np.flatnonzero(samples)
        start, end = (sound[0], sound[-1] + 1) if len(sound) else (0, len(samples))
        words = _words(text)
        step = (end - start) / rate / max(len(words), 1)
        return [(word, start / rate + i * step, start / rate + (i + 1) * step) for i, word in enumerate(words)]


def _words(text):
    """As the real aligner splits a Chinese Line: each Chinese character, and each run of other letters, digits and
    apostrophes."""
    words, word = [], ""
    for c in text:
        if unicodedata.name(c, "").startswith("CJK UNIFIED"):
            words += [word, c] if word else [c]
            word = ""
        elif c == "'" or unicodedata.category(c)[0] in "LN":
            word += c
        elif word:
            words.append(word)
            word = ""
    return words + [word] if word else words


def _crash_if(step):
    if os.environ.get(CRASH_ENV) == step:
        os.kill(os.getpid(), signal.SIGKILL)
