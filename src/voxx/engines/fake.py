"""Test-only Engine: deterministic tones and no model files. Registered only when VOXX_TEST_FAKE_ENGINE=1."""

import os
import signal

import numpy as np

SAMPLE_RATE = 24_000
LEAD_SILENCE = 0.25
TAIL_SILENCE = 0.35
SECONDS_PER_CHAR = 0.06
AMPLITUDE = 0.2
# "load" or "synthesize": the worker is killed at that step, as the OS does when memory runs out.
CRASH_ENV = "VOXX_TEST_FAKE_CRASH"


class FakeEngine:
    def load(self, model):
        _crash_if("load")

    def synthesize(self, text, *, model, voice, style, language, seed):
        _crash_if("synthesize")
        frequency = 200 + np.random.default_rng(seed).integers(0, 400)
        t = np.arange(int(SAMPLE_RATE * max(0.3, len(text) * SECONDS_PER_CHAR))) / SAMPLE_RATE
        tone = AMPLITUDE * np.sin(2 * np.pi * frequency * t)
        lead, tail = np.zeros(int(SAMPLE_RATE * LEAD_SILENCE)), np.zeros(int(SAMPLE_RATE * TAIL_SILENCE))
        return np.concatenate([lead, tone, tail]).astype(np.float32), SAMPLE_RATE


def _crash_if(step):
    if os.environ.get(CRASH_ENV) == step:
        os.kill(os.getpid(), signal.SIGKILL)
