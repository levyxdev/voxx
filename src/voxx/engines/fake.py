"""Test-only Engine: deterministic tones and no model files. Registered only when VOXX_TEST_FAKE_ENGINE=1."""

import os
import signal
import zlib
from typing import NamedTuple

import numpy as np

SAMPLE_RATE = 24_000
SECONDS_PER_CHAR = 0.06
# "load" or "synthesize": the worker is killed at that step, as the OS does when memory runs out.
CRASH_ENV = "VOXX_TEST_FAKE_CRASH"


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
    def load(self, path):
        _crash_if("load")

    def synthesize(self, text, *, model, voice, style, language, seed):
        _crash_if("synthesize")
        # The tone's pitch follows the seed, the Voice and the style, so tests can tell what reached the Engine.
        frequency = 200 + np.random.default_rng([seed, zlib.crc32(voice.encode()), zlib.crc32((style or "").encode())]).integers(0, 2000)
        shape = SHAPES[seed] if seed < len(SHAPES) else SHAPES[0]
        t = np.arange(int(SAMPLE_RATE * len(text) * SECONDS_PER_CHAR)) / SAMPLE_RATE
        tone = shape.amplitude * np.sin(2 * np.pi * frequency * t)
        if shape.spike:
            tone[(2 * np.arange(shape.spikes) + 1) * len(tone) // (2 * shape.spikes)] = shape.spike
        lead, tail = np.zeros(int(SAMPLE_RATE * shape.lead)), np.zeros(int(SAMPLE_RATE * shape.tail))
        return np.concatenate([lead, tone, tail]).astype(np.float32), SAMPLE_RATE


def _crash_if(step):
    if os.environ.get(CRASH_ENV) == step:
        os.kill(os.getpid(), signal.SIGKILL)
