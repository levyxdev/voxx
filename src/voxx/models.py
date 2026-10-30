"""The Models voxx knows, which are installed, and which one reads a given Voice. Lightweight: the CLI imports it."""

import json
import os
from dataclasses import dataclass
from pathlib import Path

from voxx.output import NOT_INSTALLED, UNSUPPORTED, USAGE, VoxxError

# Set to 1 only in tests: registers the fake Engine and its Model.
FAKE_ENGINE_ENV = "VOXX_TEST_FAKE_ENGINE"

CAPABILITIES = ("preset_voice", "clone", "align", "transcribe")


@dataclass(frozen=True)
class License:
    id: str
    url: str


@dataclass(frozen=True)
class PresetVoice:
    name: str
    native_language: str
    # The upstream Model card's own words, so an agent can offer the user a choice it cannot hear.
    description: str


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
    preset_voices: tuple[PresetVoice, ...] = ()
    # Whether the Model follows a Line's style; a Model that cannot reads the Line without it.
    reads_style: bool = False

    def to_json(self):
        return {"id": self.id, "capabilities": list(self.capabilities), "languages": list(self.languages),
                "size_bytes": self.size_bytes, "sample_rate": self.sample_rate,
                "weights_license": vars(self.weights_license), "code_license": vars(self.code_license),
                "verified": self.verified, "repo": self.repo, "revision": self.revision}

    def voice_names(self):
        return tuple(v.name for v in self.preset_voices)

    def install_summary(self):
        """What the user hears before agreeing to `voxx install`."""
        return {"model": self.id, "size_bytes": self.size_bytes, "license": self.weights_license.id,
                "license_url": self.weights_license.url}


def _apache(url):
    return License("Apache-2.0", url)


# Only Models whose weights allow commercial use (ADR 0003). Weights licenses are the upstream repo's; the mlx
# conversions downloaded here carry the same license. Sizes are the repo's total at the pinned revision.
QWEN3_TTS_CODE = _apache("https://github.com/QwenLM/Qwen3-TTS")
# Languages as ISO 639-1 codes; mlx-audio's names for them are the Engine's business.
QWEN3_TTS_LANGUAGES = ("zh", "en", "ja", "ko", "fr", "de", "it", "pt", "ru", "es")
# The CustomVoice speakers, named as in the Model's config; descriptions from the Qwen3-TTS README.
QWEN3_TTS_VOICES = (
    PresetVoice("vivian", "zh", "Bright, slightly edgy young female voice."),
    PresetVoice("serena", "zh", "Warm, gentle young female voice."),
    PresetVoice("uncle_fu", "zh", "Seasoned male voice with a low, mellow timbre."),
    PresetVoice("dylan", "zh", "Youthful Beijing male voice with a clear, natural timbre; reads Chinese in Beijing dialect."),
    PresetVoice("eric", "zh", "Lively Chengdu male voice with a slightly husky brightness; reads Chinese in Sichuan dialect."),
    PresetVoice("ryan", "en", "Dynamic male voice with strong rhythmic drive."),
    PresetVoice("aiden", "en", "Sunny American male voice with a clear midrange."),
    PresetVoice("ono_anna", "ja", "Playful Japanese female voice with a light, nimble timbre."),
    PresetVoice("sohee", "ko", "Warm Korean female voice with rich emotion."),
)
QWEN3_ASR_CODE = _apache("https://github.com/QwenLM/Qwen3-ASR")
VERIFIED = "2026-10-30"
REGISTRY = (
    # The first Model with Preset Voices is the default one.
    Model("qwen3-tts-1.7b-customvoice", "mlx-audio", ("preset_voice",), QWEN3_TTS_LANGUAGES,
          "mlx-community/Qwen3-TTS-12Hz-1.7B-CustomVoice-8bit", "41d3337e8b7f2843a75841595fc14e4b9a7a4b96", 3_080_141_538,
          _apache("https://huggingface.co/Qwen/Qwen3-TTS-12Hz-1.7B-CustomVoice"), QWEN3_TTS_CODE, VERIFIED, 24_000,
          QWEN3_TTS_VOICES, reads_style=True),
    # The fast tier: the same Voices, but it ignores style.
    Model("qwen3-tts-0.6b-customvoice", "mlx-audio", ("preset_voice",), QWEN3_TTS_LANGUAGES,
          "mlx-community/Qwen3-TTS-12Hz-0.6B-CustomVoice-8bit", "049ef77fe8816b536193c0c25f9a214d17921282", 1_973_575_388,
          _apache("https://huggingface.co/Qwen/Qwen3-TTS-12Hz-0.6B-CustomVoice"), QWEN3_TTS_CODE, VERIFIED, 24_000,
          QWEN3_TTS_VOICES),
    Model("qwen3-tts-1.7b-base", "mlx-audio", ("clone",), QWEN3_TTS_LANGUAGES,
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

# Installed like any other Model, from the test suite's local stand-in for Hugging Face. Like the two CustomVoice
# Models, the two fake ones share their Voices, and only the first follows style.
FAKE_VOICES = (PresetVoice("fake-alice", "zh", "A test tone."), PresetVoice("fake-bob", "en", "A lower test tone."))
FAKE_MODEL = Model("fake-tts", "fake", ("preset_voice",), ("zh", "en", "fr"),
                   "voxx-test/fake-tts", "0123456789abcdef0123456789abcdef01234567", 4096,
                   _apache("https://huggingface.co/voxx-test/fake-tts"), _apache("https://github.com/levyxdev/voxx"),
                   VERIFIED, 24_000, FAKE_VOICES, reads_style=True)
FAKE_SMALL_MODEL = Model("fake-tts-small", "fake", ("preset_voice",), ("zh", "en"),
                         "voxx-test/fake-tts-small", "89abcdef0123456789abcdef0123456789abcdef", 4096,
                         _apache("https://huggingface.co/voxx-test/fake-tts-small"),
                         _apache("https://github.com/levyxdev/voxx"), VERIFIED, 24_000, FAKE_VOICES)


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


def require_installed(required):
    """Fails, without downloading anything, unless every Model is installed (ADR 0003)."""
    missing = [m for m in required if not is_installed(m)]
    if missing:
        commands = " and ".join(f"`voxx install {m.id}`" for m in missing)
        raise VoxxError("model_not_installed", f"Not installed: {', '.join(m.id for m in missing)}.",
                        f"Tell the user each Model's size and license from details; once they agree, run {commands}.",
                        {"missing": [m.install_summary() for m in missing], "total_bytes": sum(m.size_bytes for m in missing)},
                        NOT_INSTALLED)


def fake_engine_enabled():
    return os.environ.get(FAKE_ENGINE_ENV) == "1"


def models():
    return [*REGISTRY, FAKE_MODEL, FAKE_SMALL_MODEL] if fake_engine_enabled() else list(REGISTRY)


def list_models(capability=None, installed=None):
    """`voxx models`: every registered Model, optionally only those with a capability or install state."""
    listed = [{**m.to_json(), "installed": is_installed(m)} for m in models()
              if capability is None or capability in m.capabilities]
    return {"models": [m for m in listed if installed is None or m["installed"] == installed]}


def list_voices():
    """`voxx voices`: every Preset Voice, and the Models that read it."""
    voices = {}
    for model in models():
        installed = is_installed(model)
        for voice in model.preset_voices:
            entry = voices.setdefault(voice.name, {"name": voice.name, "kind": "preset", "native_language": voice.native_language,
                                                   "description": voice.description, "languages": [], "models": []})
            entry["languages"] += [l for l in model.languages if l not in entry["languages"]]
            entry["models"].append({"model": model.id, "installed": installed})
    return {"voices": list(voices.values())}


def find_model(model_id):
    model = next((m for m in models() if m.id == model_id), None)
    if model is None:
        raise VoxxError("unknown_model", f"No Model named {model_id!r}.", "Use one of the Models in details.known_models.",
                        {"model": model_id, "known_models": [m.id for m in models()]}, USAGE)
    return model


def resolve_voice(voice, language, model=None):
    """The Model that reads this Voice in this language, and the Voice's name.

    No Model means the one that has the Voice, or the default Model; no Voice means the Model's first Voice whose
    native language this is, else its first Voice."""
    readers = [m for m in models() if m.preset_voices]
    if voice is not None and not any(voice in m.voice_names() for m in readers):
        known = list(dict.fromkeys(v for m in readers for v in m.voice_names()))
        raise VoxxError("unknown_voice", f"No Model has a Voice named {voice!r}.",
                        "Use one of the Voices in details.known_voices, or run `voxx voices`.",
                        {"voice": voice, "known_voices": known}, USAGE)
    if model is None:
        model = next(m for m in readers if voice is None or voice in m.voice_names())
    elif "preset_voice" not in model.capabilities:
        raise _unsupported("capability_unsupported", model, f"Model {model.id} cannot read Preset Voices.",
                           "Pick a Model with the preset_voice capability from `voxx models`.", {"capability": "preset_voice"})
    elif voice is not None and voice not in model.voice_names():
        raise _unsupported("voice_unsupported", model, f"Model {model.id} has no Voice named {voice!r}.",
                           "Pick one of the Voices in details.voices, or a Model that has this Voice.",
                           {"voice": voice, "voices": list(model.voice_names())})
    if language not in model.languages:
        raise _unsupported("unsupported_language", model, f"Model {model.id} cannot read language {language!r}.",
                           "Pick a Model that reads this language.", {"language": language, "languages": list(model.languages)})
    if voice is None:
        voice = next((v.name for v in model.preset_voices if v.native_language == language), model.preset_voices[0].name)
    return model, voice


def _unsupported(code, model, message, hint, details):
    return VoxxError(code, message, hint, {"model": model.id, **details}, UNSUPPORTED)
