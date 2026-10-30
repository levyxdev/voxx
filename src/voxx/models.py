"""The Models voxx knows and which one reads a given Voice. Lightweight: the CLI imports it."""

import os
from dataclasses import dataclass

from voxx.output import UNSUPPORTED, USAGE, VoxxError

# Set to 1 only in tests: registers the fake Engine and its Model.
FAKE_ENGINE_ENV = "VOXX_TEST_FAKE_ENGINE"


@dataclass(frozen=True)
class Model:
    id: str
    engine: str
    languages: tuple[str, ...]
    preset_voices: tuple[str, ...] = ()


FAKE_MODEL = Model("fake-tts", engine="fake", languages=("zh", "en"), preset_voices=("fake-alice", "fake-bob"))


def fake_engine_enabled():
    return os.environ.get(FAKE_ENGINE_ENV) == "1"


def models():
    return [FAKE_MODEL] if fake_engine_enabled() else []


def resolve_voice(voice, language):
    """The Model that reads this Voice, and the Voice's full name. No Voice means the default Preset Voice."""
    candidates = [m for m in models() if m.preset_voices]
    if voice is None:
        if not candidates:
            raise VoxxError("no_preset_model", "No Model for Preset Voices is available in this build.",
                            "This voxx build has no speech Engine yet.")
        model = candidates[0]
        voice = model.preset_voices[0]
    else:
        model = next((m for m in candidates if voice in m.preset_voices), None)
        if model is None:
            known = [v for m in candidates for v in m.preset_voices]
            raise VoxxError("unknown_voice", f"No Model has a Voice named {voice!r}.",
                            "Use one of the Voices in details.known_voices.", {"voice": voice, "known_voices": known}, USAGE)
    if language not in model.languages:
        raise VoxxError("unsupported_language", f"Model {model.id} cannot read language {language!r}.",
                        "Pick a Voice whose Model reads this language.",
                        {"model": model.id, "language": language, "languages": list(model.languages)}, UNSUPPORTED)
    return model, voice
