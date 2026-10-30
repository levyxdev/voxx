"""The Models voxx knows, which are installed, and which one reads a given Voice. Lightweight: the CLI imports it."""

import json
import os
from dataclasses import dataclass
from pathlib import Path

from voxx.output import UNSUPPORTED, USAGE, VoxxError

# Set to 1 only in tests: registers the fake Engine and its Model.
FAKE_ENGINE_ENV = "VOXX_TEST_FAKE_ENGINE"

CAPABILITIES = ("preset_voice", "clone", "align", "transcribe")


@dataclass(frozen=True)
class License:
    id: str
    url: str


@dataclass(frozen=True)
class Model:
    id: str
    engine: str
    capabilities: tuple[str, ...]
    languages: tuple[str, ...]
    # What `voxx install` downloads: a Hugging Face repo pinned to one commit, so the license and size stay as verified.
    repo: str
    revision: str
    size_bytes: int
    weights_license: License
    code_license: License
    verified: str
    # The native sample rate of a speech Model's output; None for Models that only listen.
    sample_rate: int | None = None
    preset_voices: tuple[str, ...] = ()

    def to_json(self):
        return {"id": self.id, "capabilities": list(self.capabilities), "languages": list(self.languages),
                "size_bytes": self.size_bytes, "sample_rate": self.sample_rate,
                "weights_license": vars(self.weights_license), "code_license": vars(self.code_license),
                "verified": self.verified, "repo": self.repo, "revision": self.revision}


def _apache(url):
    return License("Apache-2.0", url)


# Only Models whose weights allow commercial use (ADR 0003). Weights licenses are the upstream repo's; the mlx
# conversions downloaded here carry the same license. Sizes are the repo's total at the pinned revision.
QWEN3_TTS_CODE = _apache("https://github.com/QwenLM/Qwen3-TTS")
QWEN3_ASR_CODE = _apache("https://github.com/QwenLM/Qwen3-ASR")
VERIFIED = "2026-10-30"
REGISTRY = (
    Model("qwen3-tts-1.7b-customvoice", "mlx-audio", ("preset_voice",), ("zh", "en"),
          "mlx-community/Qwen3-TTS-12Hz-1.7B-CustomVoice-8bit", "41d3337e8b7f2843a75841595fc14e4b9a7a4b96", 3_080_141_538,
          _apache("https://huggingface.co/Qwen/Qwen3-TTS-12Hz-1.7B-CustomVoice"), QWEN3_TTS_CODE, VERIFIED, 24_000),
    Model("qwen3-tts-0.6b-customvoice", "mlx-audio", ("preset_voice",), ("zh", "en"),
          "mlx-community/Qwen3-TTS-12Hz-0.6B-CustomVoice-8bit", "049ef77fe8816b536193c0c25f9a214d17921282", 1_973_575_388,
          _apache("https://huggingface.co/Qwen/Qwen3-TTS-12Hz-0.6B-CustomVoice"), QWEN3_TTS_CODE, VERIFIED, 24_000),
    Model("qwen3-tts-1.7b-base", "mlx-audio", ("clone",), ("zh", "en"),
          "mlx-community/Qwen3-TTS-12Hz-1.7B-Base-8bit", "e7dd0585652209fa0d7783659aad4e8a324de11c", 3_104_158_788,
          _apache("https://huggingface.co/Qwen/Qwen3-TTS-12Hz-1.7B-Base"), QWEN3_TTS_CODE, VERIFIED, 24_000),
    Model("voxcpm2", "mlx-audio", ("clone",), ("zh", "en"),
          "mlx-community/VoxCPM2-8bit", "d52725898a0675703f7f9ddc5a4d1a3cdbb99032", 3_226_617_581,
          _apache("https://huggingface.co/openbmb/VoxCPM2"), _apache("https://github.com/OpenBMB/VoxCPM"), VERIFIED, 48_000),
    Model("qwen3-forcedaligner-0.6b", "mlx-audio", ("align",), ("zh", "en"),
          "mlx-community/Qwen3-ForcedAligner-0.6B-8bit", "0e1a68e91d815300c7c9754b2a7639378b23db15", 1_276_475_979,
          _apache("https://huggingface.co/Qwen/Qwen3-ForcedAligner-0.6B"), QWEN3_ASR_CODE, VERIFIED),
    Model("qwen3-asr-0.6b", "mlx-audio", ("transcribe",), ("zh", "en"),
          "mlx-community/Qwen3-ASR-0.6B-8bit", "89e96d92ba34aca20b3e29fb10cc284097d1219f", 1_010_773_761,
          _apache("https://huggingface.co/Qwen/Qwen3-ASR-0.6B"), QWEN3_ASR_CODE, VERIFIED),
)

# Installed like any other Model, from the test suite's local stand-in for Hugging Face.
FAKE_MODEL = Model("fake-tts", "fake", ("preset_voice",), ("zh", "en"),
                   "voxx-test/fake-tts", "0123456789abcdef0123456789abcdef01234567", 4096,
                   _apache("https://huggingface.co/voxx-test/fake-tts"), _apache("https://github.com/levyxdev/voxx"),
                   VERIFIED, 24_000, preset_voices=("fake-alice", "fake-bob"))


INSTALL_MANIFEST = "voxx-install.json"


def voxx_home():
    return Path(os.environ.get("VOXX_HOME") or Path.home() / ".voxx")


def models_dir():
    return voxx_home() / "models"


def model_dir(model):
    return models_dir() / model.id


def is_installed(model):
    """Installed means `voxx install` finished for the revision this voxx pins; an older revision does not count."""
    try:
        manifest = json.loads((model_dir(model) / INSTALL_MANIFEST).read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return False
    return isinstance(manifest, dict) and manifest.get("revision") == model.revision


def fake_engine_enabled():
    return os.environ.get(FAKE_ENGINE_ENV) == "1"


def models():
    return [*REGISTRY, FAKE_MODEL] if fake_engine_enabled() else list(REGISTRY)


def list_models(capability=None, installed=None):
    """`voxx models`: every registered Model, optionally only those with a capability or install state."""
    listed = [{**m.to_json(), "installed": is_installed(m)} for m in models()
              if capability is None or capability in m.capabilities]
    return {"models": [m for m in listed if installed is None or m["installed"] == installed]}


def find_model(model_id):
    model = next((m for m in models() if m.id == model_id), None)
    if model is None:
        raise VoxxError("unknown_model", f"No Model named {model_id!r}.", "Use one of the Models in details.known_models.",
                        {"model": model_id, "known_models": [m.id for m in models()]}, USAGE)
    return model


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
