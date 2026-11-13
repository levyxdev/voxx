"""The Models voxx knows, which are installed, and which one reads a given Voice. Lightweight: the CLI imports it."""

import json
import os
from collections import Counter
from dataclasses import dataclass
from pathlib import Path

from voxx.ming_voices import MING_VOICES
from voxx.output import NOT_INSTALLED, UNSUPPORTED, USAGE, VoxxError

# Set to 1 only in tests: registers the fake Engine and its Model.
FAKE_ENGINE_ENV = "VOXX_TEST_FAKE_ENGINE"

CAPABILITIES = ("preset_voice", "clone", "design", "align", "transcribe")
# `voxx voices` lists the Preset Voices of a Model with more than this only when asked to, so that hundreds of names do
# not fill an agent's context by default.
LISTED_VOICES_MAX = 20


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
class ExtraRepo:
    """A Hugging Face repo a Model's Engine loads by name alongside the Model's own. Not pinned: `voxx install`
    downloads its current revision and records it (ADR 0003)."""
    repo: str
    # The size of `files` when voxx checked the repo; a later revision may differ.
    size_bytes: int
    license: License
    # Glob patterns of the files the Engine loads, as its own download would filter them; only these are installed.
    files: tuple[str, ...]


@dataclass(frozen=True)
class Model:
    id: str
    engine: str
    capabilities: tuple[str, ...]
    languages: tuple[str, ...]
    # What `voxx install` downloads: a Hugging Face repo pinned to one commit, so the license and size stay as verified.
    repo: str
    revision: str
    # The size of the repo alone; what voxx reports as a Model's size_bytes is its download_bytes.
    repo_bytes: int
    weights_license: License
    code_license: License
    verified: str
    # The native sample rate of a speech Model's output; None for Models that only listen.
    sample_rate: int | None = None
    preset_voices: tuple[PresetVoice, ...] = ()
    # Whether the Model follows a Line's style; a Model that cannot reads the Line without it.
    reads_style: bool = False
    # Whether the Model follows a Line's Delivery Controls (emotion, speed, pitch, volume); a Model that cannot reads
    # the Line without them.
    reads_controls: bool = False
    # Repos the Engine also loads, downloaded with the Model by `voxx install`.
    extra_repos: tuple[ExtraRepo, ...] = ()

    @property
    def download_bytes(self):
        """What `voxx install` downloads: the Model's repo and its extra repos, at the sizes voxx checked."""
        return self.repo_bytes + sum(e.size_bytes for e in self.extra_repos)

    def to_json(self):
        listed = {"id": self.id, "capabilities": list(self.capabilities), "languages": list(self.languages),
                  "size_bytes": self.download_bytes, "sample_rate": self.sample_rate,
                  "weights_license": vars(self.weights_license), "code_license": vars(self.code_license),
                  "verified": self.verified, "repo": self.repo, "revision": self.revision}
        if self.extra_repos:
            listed["extra_repos"] = [{"repo": e.repo, "size_bytes": e.size_bytes, "license": vars(e.license)}
                                     for e in self.extra_repos]
        return listed

    def voice_names(self):
        return tuple(v.name for v in self.preset_voices)

    def install_summary(self):
        """What the user hears before agreeing to `voxx install`, extra repos included."""
        summary = {"model": self.id, "size_bytes": self.download_bytes, "license": self.weights_license.id,
                   "license_url": self.weights_license.url}
        if self.extra_repos:
            summary["extra_repos"] = [{"repo": e.repo, "size_bytes": e.size_bytes, "license": e.license.id,
                                       "license_url": e.license.url} for e in self.extra_repos]
        return summary


def _apache(url):
    return License("Apache-2.0", url)


def _mit(url):
    return License("MIT", url)


# Only Models whose weights allow commercial use (ADR 0003). Weights licenses are the upstream repo's; the mlx
# conversions downloaded here carry the same license. Sizes are the repo's total at the pinned revision.
QWEN3_TTS_CODE = _apache("https://github.com/QwenLM/Qwen3-TTS")
# Languages as BCP 47 tags (ADR 0005); mlx-audio's names for them are the Engine's business.
QWEN3_TTS_LANGUAGES = ("zh", "en", "ja", "ko", "fr", "de", "it", "pt", "ru", "es")
# The CustomVoice Voices, named as in the Model's config; descriptions from the Qwen3-TTS README.
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
# Every language in the pinned revision's config.json (support_languages).
QWEN3_ASR_LANGUAGES = ("zh", "en", "yue", "ar", "de", "fr", "es", "pt", "id", "it", "ko", "ru", "th", "vi", "ja", "tr", "hi",
                       "ms", "nl", "sv", "da", "fi", "pl", "cs", "fil", "fa", "el", "ro", "hu", "mk")
VERIFIED = "2026-10-30"
# Ming-3.0-tts reads these languages (its cookbook's "Target languages"); its dialects are not offered.
MING_LANGUAGES = ("zh", "en", "ja", "ko", "de", "fr", "es")
REGISTRY = (
    # The first Model with Preset Voices is the default one.
    Model("qwen3-tts-1.7b-customvoice", "mlx-audio", ("preset_voice",), QWEN3_TTS_LANGUAGES,
          "mlx-community/Qwen3-TTS-12Hz-1.7B-CustomVoice-8bit", "41d3337e8b7f2843a75841595fc14e4b9a7a4b96", 3_080_141_538,
          _apache("https://huggingface.co/Qwen/Qwen3-TTS-12Hz-1.7B-CustomVoice"), QWEN3_TTS_CODE, VERIFIED, 24_000,
          QWEN3_TTS_VOICES, reads_style=True),
    # The first Model that clones is the one a new Cloned Voice is read with; the other is there to compare by ear.
    # The first Model that designs is the one `voxx voice design` uses.
    Model("voxcpm2", "mlx-audio", ("clone", "design"), ("zh", "en"),
          "mlx-community/VoxCPM2-8bit", "d52725898a0675703f7f9ddc5a4d1a3cdbb99032", 3_226_617_581,
          _apache("https://huggingface.co/openbmb/VoxCPM2"), _apache("https://github.com/OpenBMB/VoxCPM"), VERIFIED, 48_000,
          reads_style=True),
    Model("qwen3-tts-1.7b-base", "mlx-audio", ("clone",), QWEN3_TTS_LANGUAGES,
          "mlx-community/Qwen3-TTS-12Hz-1.7B-Base-8bit", "e7dd0585652209fa0d7783659aad4e8a324de11c", 3_104_158_788,
          _apache("https://huggingface.co/Qwen/Qwen3-TTS-12Hz-1.7B-Base"), QWEN3_TTS_CODE, VERIFIED, 24_000),
    Model("qwen3-forcedaligner-0.6b", "mlx-audio", ("align",), ("zh", "en"),
          "mlx-community/Qwen3-ForcedAligner-0.6B-8bit", "0e1a68e91d815300c7c9754b2a7639378b23db15", 1_276_475_979,
          _apache("https://huggingface.co/Qwen/Qwen3-ForcedAligner-0.6B"), QWEN3_ASR_CODE, VERIFIED),
    Model("qwen3-asr-0.6b", "mlx-audio", ("transcribe",), QWEN3_ASR_LANGUAGES,
          "mlx-community/Qwen3-ASR-0.6B-8bit", "89e96d92ba34aca20b3e29fb10cc284097d1219f", 1_010_773_761,
          _apache("https://huggingface.co/Qwen/Qwen3-ASR-0.6B"), QWEN3_ASR_CODE, VERIFIED),
    # Kept after the audition (levyxdev/voxx#25), checked 2026-11-06. It follows Delivery Controls but not style: with a
    # Preset Voice or a Reference Recording it keeps the voice and ignores the style (tested in levyxdev/voxx#33).
    Model("ming-3.0-tts-0.5b", "mlx-audio", ("preset_voice", "clone", "design"), MING_LANGUAGES,
          "mlx-community/Ming-3.0-tts-0.5B-8bit", "d0d1da6f627e4b3f20cc2db6ba4aee86d45343ad", 1_617_181_518,
          _mit("https://huggingface.co/inclusionAI/Ming-3.0-tts-0.5B"), _mit("https://github.com/inclusionAI/Ming-3.0-tts"),
          "2026-11-06", 44_100, tuple(PresetVoice(*v) for v in MING_VOICES),
          reads_controls=True),
    # Kept after the audition (levyxdev/voxx#25), checked 2026-11-06. It only designs, in every language Qwen3-TTS
    # reads; it has no Voices of its own. The description goes in as a chat turn of its own, before the text it reads,
    # so it is not read out the way VoxCPM2 sometimes reads its description.
    Model("qwen3-tts-1.7b-voicedesign", "mlx-audio", ("design",), QWEN3_TTS_LANGUAGES,
          "mlx-community/Qwen3-TTS-12Hz-1.7B-VoiceDesign-8bit", "f90d617701d9f7f4ca499291e0b57f2b3c2fd2ee", 3_080_140_867,
          _apache("https://huggingface.co/Qwen/Qwen3-TTS-12Hz-1.7B-VoiceDesign"), QWEN3_TTS_CODE, "2026-11-06", 24_000),
)

# Installed like any other Model, from the test suite's local stand-in for Hugging Face. Like the two CustomVoice
# Models, the two fake ones share their Voices, and only the first follows style; it also follows Delivery Controls,
# as Ming-3.0-tts does.
FAKE_VOICES = (PresetVoice("fake-alice", "zh", "A test tone."), PresetVoice("fake-bob", "en", "A lower test tone."))
FAKE_MODEL = Model("fake-tts", "fake", ("preset_voice",), ("zh", "en", "fr", "yue"),
                   "voxx-test/fake-tts", "0123456789abcdef0123456789abcdef01234567", 4096,
                   _apache("https://huggingface.co/voxx-test/fake-tts"), _apache("https://github.com/levyxdev/voxx"),
                   VERIFIED, 24_000, FAKE_VOICES, reads_style=True, reads_controls=True)
FAKE_SMALL_MODEL = Model("fake-tts-small", "fake", ("preset_voice",), ("zh", "en"),
                         "voxx-test/fake-tts-small", "89abcdef0123456789abcdef0123456789abcdef", 4096,
                         _apache("https://huggingface.co/voxx-test/fake-tts-small"),
                         _apache("https://github.com/levyxdev/voxx"), VERIFIED, 24_000, FAKE_VOICES)
# Transcribes the fake Models' Lines. It cannot transcribe every language they read.
FAKE_ASR_MODEL = Model("fake-asr", "fake", ("transcribe",), ("zh", "en", "yue"),
                       "voxx-test/fake-asr", "fedcba9876543210fedcba9876543210fedcba98", 4096,
                       _apache("https://huggingface.co/voxx-test/fake-asr"), _apache("https://github.com/levyxdev/voxx"),
                       VERIFIED)
# Times the words of the fake Models' Lines, in the languages the real aligner reads.
FAKE_ALIGN_MODEL = Model("fake-aligner", "fake", ("align",), ("zh", "en"),
                         "voxx-test/fake-aligner", "76543210fedcba9876543210fedcba9876543210", 4096,
                         _apache("https://huggingface.co/voxx-test/fake-aligner"),
                         _apache("https://github.com/levyxdev/voxx"), VERIFIED)
# Clone like the two real cloning Models: the first follows style and designs as VoxCPM2 does, the other ignores style
# as Qwen3-TTS Base does, and they read at different sample rates. Only the first follows Delivery Controls, as
# Ming-3.0-tts does.
FAKE_CLONE_MODEL = Model("fake-clone", "fake", ("clone", "design"), ("zh", "en"),
                         "voxx-test/fake-clone", "0f1e2d3c4b5a69788796a5b4c3d2e1f00f1e2d3c", 4096,
                         _apache("https://huggingface.co/voxx-test/fake-clone"),
                         _apache("https://github.com/levyxdev/voxx"), VERIFIED, 48_000, reads_style=True,
                         reads_controls=True)
FAKE_CLONE_ALT_MODEL = Model("fake-clone-alt", "fake", ("clone",), ("zh", "en"),
                             "voxx-test/fake-clone-alt", "a5b4c3d2e1f00f1e2d3c4b5a69788796a5b4c3d2", 4096,
                             _apache("https://huggingface.co/voxx-test/fake-clone-alt"),
                             _apache("https://github.com/levyxdev/voxx"), VERIFIED, 24_000)
# Clones with a tokenizer from a repo of its own: the hub serves more files than it loads.
FAKE_EXTRA_REPO = ExtraRepo("voxx-test/fake-tokenizer", 4096, _apache("https://huggingface.co/voxx-test/fake-tokenizer"),
                            ("model.safetensors", "*.json"))
FAKE_EXTRA_MODEL = Model("fake-clone-extra", "fake", ("clone",), ("zh", "en"),
                         "voxx-test/fake-clone-extra", "c3d2e1f00f1e2d3c4b5a69788796a5b4c3d2e1f0", 4096,
                         _apache("https://huggingface.co/voxx-test/fake-clone-extra"),
                         _apache("https://github.com/levyxdev/voxx"), VERIFIED, 24_000,
                         extra_repos=(FAKE_EXTRA_REPO,))
FAKE_MODELS = (FAKE_MODEL, FAKE_SMALL_MODEL, FAKE_ASR_MODEL, FAKE_ALIGN_MODEL, FAKE_CLONE_MODEL, FAKE_CLONE_ALT_MODEL,
               FAKE_EXTRA_MODEL)


INSTALL_MANIFEST = "voxx-install.json"


def voxx_home():
    return Path(os.environ.get("VOXX_HOME") or Path.home() / ".voxx")


def models_dir():
    return voxx_home() / "models"


def model_dir(model):
    return models_dir() / model.id


def hf_cache_dir():
    """Where extra repos are installed, laid out as a Hugging Face cache: an Engine that loads one by name finds it
    there offline, because the worker points HF_HUB_CACHE here."""
    return voxx_home() / "hf-cache"


def extra_repo_dir(repo):
    return hf_cache_dir() / ("models--" + repo.replace("/", "--"))


def extra_repo_snapshot(repo, revision):
    """Where `voxx install` puts an extra repo's files at a revision, as Hugging Face's cache lays them out."""
    return extra_repo_dir(repo) / "snapshots" / revision


def extra_repo_path(repo):
    """The installed files of an extra repo, where Hugging Face's own loader finds them: the snapshot its main ref
    names. None if there is none."""
    try:
        revision = (extra_repo_dir(repo) / "refs" / "main").read_text(encoding="utf-8")
    except OSError:
        return None
    path = extra_repo_snapshot(repo, revision)
    return path if revision and path.is_dir() else None


def extra_repo_paths(model) -> dict[str, Path]:
    """The installed files of each of a Model's extra repos, by repo name, as its Engine is given them when it loads
    the Model. An extra repo with none is left out."""
    return {e.repo: path for e in model.extra_repos if (path := extra_repo_path(e.repo)) is not None}


def read_manifest(model):
    """What `voxx install` recorded when it finished installing this Model, or None."""
    try:
        manifest = json.loads((model_dir(model) / INSTALL_MANIFEST).read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return None
    return manifest if isinstance(manifest, dict) else None


def is_installed(model):
    """Installed means `voxx install` finished for the revision this voxx pins, and every extra repo's files are still
    where the Engine looks for them; an older revision does not count."""
    manifest = read_manifest(model)
    if manifest is None or manifest.get("revision") != model.revision:
        return False
    try:
        recorded = {e["repo"]: e for e in manifest.get("extra_repos", [])}
        return all(_extra_repo_installed(recorded[e.repo]) for e in model.extra_repos)
    except (KeyError, TypeError, AttributeError):
        return False


def _extra_repo_installed(entry):
    # Every file is checked, because an Engine may go on without one: Chatterbox, once registered, read with random weights.
    path = extra_repo_path(entry["repo"])
    try:
        return path is not None and path.name == entry["revision"] and all(
            (path / f["path"]).stat().st_size == f["size"] for f in entry["files"])
    except OSError:
        return False


def require_installed(required):
    """Fails, without downloading anything, unless every Model is installed (ADR 0003)."""
    missing = [m for m in required if not is_installed(m)]
    if missing:
        commands = " and ".join(f"`voxx install {m.id}`" for m in missing)
        raise VoxxError("model_not_installed", f"Not installed: {', '.join(m.id for m in missing)}.",
                        f"Tell the user each Model's size and license from details, and the extra repos it downloads with it; "
                        f"once they agree, run {commands}.",
                        {"missing": [m.install_summary() for m in missing], "total_bytes": sum(m.download_bytes for m in missing)},
                        NOT_INSTALLED)


def fake_engine_enabled():
    return os.environ.get(FAKE_ENGINE_ENV) == "1"


def models():
    return [*REGISTRY, *FAKE_MODELS] if fake_engine_enabled() else list(REGISTRY)


def list_models(capability=None, installed=None):
    """`voxx models`: every registered Model, optionally only those with a capability or install state."""
    listed = [{**m.to_json(), "installed": is_installed(m)} for m in models()
              if capability is None or capability in m.capabilities]
    return {"models": [m for m in listed if installed is None or m["installed"] == installed]}


def list_preset_voices(model=None, language=None):
    """The Preset Voices `voxx voices` lists, each with the Models that read it, and a summary of each Model whose
    Voices it leaves out: only `model`'s if given, else those of every Model with at most LISTED_VOICES_MAX; only those
    native to `language` if given."""
    voices, listed, unlisted = {}, set(), []
    for reader in models():
        installed = is_installed(reader)
        own = [v for v in reader.preset_voices if language is None or v.native_language == language]
        shown = reader is model if model is not None else len(reader.preset_voices) <= LISTED_VOICES_MAX
        if shown:
            listed.update(v.name for v in own)
        elif model is None and own:
            # A Model with too many to list unasked gets a summary instead, with the command that lists them.
            command = f"voxx voices --model {reader.id}" + (f" --language {language}" if language else "")
            unlisted.append({"model": reader.id, "installed": installed, "voices": len(own),
                             "native_languages": dict(Counter(v.native_language for v in own)), "command": command})
        for voice in own:
            entry = voices.setdefault(voice.name, {"name": voice.name, "kind": "preset", "native_language": voice.native_language,
                                                   "description": voice.description, "languages": [], "models": []})
            entry["languages"] += [l for l in reader.languages if l not in entry["languages"]]
            entry["models"].append({"model": reader.id, "installed": installed})
    return [v for name, v in voices.items() if name in listed], unlisted


def find_model(model_id):
    model = next((m for m in models() if m.id == model_id), None)
    if model is None:
        raise VoxxError("unknown_model", f"No Model named {model_id!r}.", "Use one of the Models in details.known_models.",
                        {"model": model_id, "known_models": [m.id for m in models()]}, USAGE)
    return model


def transcriber_for(model, language):
    """The Model that transcribes a Line this Model read in this language, or in any language if None: the first on
    the same Engine that can. None if no Model can."""
    return _listener_for(model, language, "transcribe")


def aligner_for(model, language):
    """The Model that times the words of a Line this Model read in this language: the first on the same Engine that
    can. None if no Model can."""
    return _listener_for(model, language, "align")


def _listener_for(model, language, capability):
    return next((m for m in models() if capability in m.capabilities and m.engine == model.engine
                 and (language is None or language in m.languages)), None)


def preset_voice_names():
    return list(dict.fromkeys(v for m in models() for v in m.voice_names()))


def default_clone_model():
    return next(m for m in models() if "clone" in m.capabilities)


def default_design_model():
    return next(m for m in models() if "design" in m.capabilities)


def resolve_preset_voice(voice, language, model=None):
    """The Model that reads this Preset Voice in this language, and the Voice's name.

    No Model means the one that has the Voice, or the default Model; no Voice means the Model's first Voice whose
    native language this is, else its first Voice."""
    readers = [m for m in models() if m.preset_voices]
    if model is None:
        model = next(m for m in readers if voice is None or voice in m.voice_names())
    elif "preset_voice" not in model.capabilities:
        raise unsupported_capability(model, "preset_voice", "read Preset Voices")
    elif voice is not None and voice not in model.voice_names():
        raise _unsupported("voice_unsupported", model, f"Model {model.id} has no Voice named {voice!r}.",
                           "Pick one of the Voices in details.voices, or a Model that has this Voice.",
                           {"voice": voice, "voices": list(model.voice_names())})
    check_language(model, language)
    if voice is None:
        voice = next((v.name for v in model.preset_voices if v.native_language == language), model.preset_voices[0].name)
    return model, voice


def check_language(model, language):
    if language not in model.languages:
        raise _unsupported("unsupported_language", model, f"Model {model.id} cannot read language {language!r}.",
                           "Pick a Model that reads this language.", {"language": language, "languages": list(model.languages)})


def unsupported_capability(model, capability, doing):
    return _unsupported("capability_unsupported", model, f"Model {model.id} cannot {doing}.",
                        f"Pick a Model with the {capability} capability from `voxx models`.", {"capability": capability})


def _unsupported(code, model, message, hint, details):
    return VoxxError(code, message, hint, {"model": model.id, **details}, UNSUPPORTED)
