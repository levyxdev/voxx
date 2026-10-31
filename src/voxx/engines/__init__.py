"""Engine adapters. Worker-side only: an Engine may import heavy inference libraries."""

from pathlib import Path
from typing import Protocol

import numpy as np

from voxx.models import fake_engine_enabled
from voxx.output import BUG_HINT, VoxxError


class Engine(Protocol):
    def load(self, path: Path, capability: str) -> None:
        """Load the Model installed at path, to use it for capability. Called once per Model per worker; never
        downloads (ADR 0003)."""
        ...

    def synthesize(self, text: str, *, model: str, voice: str, style: str | None, language: str, seed: int) -> tuple[np.ndarray, int]:
        """Read one whole Line in one pass, the same way every time for the same seed. language is a BCP 47 tag.
        Returns mono float32 samples in [-1, 1] and the native sample rate."""
        ...

    def transcribe(self, path: Path, *, model: str, language: str) -> str:
        """The words spoken in the WAV at path, in language, a BCP 47 tag."""
        ...


def load_engine(name) -> Engine:
    if name == "fake" and fake_engine_enabled():
        from voxx.engines.fake import FakeEngine
        return FakeEngine()
    if name == "mlx-audio":
        from voxx.engines.mlx_audio import MlxAudioEngine
        return MlxAudioEngine()
    raise VoxxError("unknown_engine", f"No Engine named {name!r}.", BUG_HINT, {"engine": name})
