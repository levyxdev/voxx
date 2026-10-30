"""Engine adapters. Worker-side only: an Engine may import heavy inference libraries."""

from typing import Protocol

import numpy as np

from voxx.models import fake_engine_enabled
from voxx.output import BUG_HINT, VoxxError


class Engine(Protocol):
    def load(self, model: str) -> None:
        """Load a Model's weights. Called once per Model per worker."""

    def synthesize(self, text: str, *, model: str, voice: str, style: str | None, language: str, seed: int) -> tuple[np.ndarray, int]:
        """Read one whole Line in one pass. Returns mono float32 samples in [-1, 1] and the native sample rate."""


def load_engine(name) -> Engine:
    if name == "fake" and fake_engine_enabled():
        from voxx.engines.fake import FakeEngine
        return FakeEngine()
    raise VoxxError("unknown_engine", f"No Engine named {name!r}.", BUG_HINT, {"engine": name})
