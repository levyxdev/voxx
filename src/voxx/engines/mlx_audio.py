"""Runs Models through mlx-audio on Apple Silicon. Imported only inside the worker (ADR 0002)."""

from typing import Any

import mlx.core as mx
import numpy as np
from mlx_audio.stt.utils import load as load_stt
from mlx_audio.tts.models.bailingmm.bailingmm import ming3_instruction
from mlx_audio.tts.utils import load as load_tts

from voxx.output import BUG_HINT, VoxxError

# MLX keeps freed Metal buffers for reuse, by default up to the whole memory limit, and the worker holds a reader, an
# aligner and a transcriber at once: on a 16 GB Mac that ran the machine out of memory. Keep at most this much cached.
mx.set_cache_limit(512 * 1024**2)

# Narrations name languages by BCP 47 tag; mlx-audio names them in English.
LANGUAGE_NAMES = {"zh": "chinese", "en": "english", "ja": "japanese", "ko": "korean", "fr": "french", "de": "german",
                  "it": "italian", "pt": "portuguese", "ru": "russian", "es": "spanish", "ar": "arabic", "id": "indonesian",
                  "th": "thai", "vi": "vietnamese", "tr": "turkish", "hi": "hindi", "ms": "malay", "nl": "dutch",
                  "sv": "swedish", "da": "danish", "fi": "finnish", "pl": "polish", "cs": "czech", "fa": "persian",
                  "el": "greek", "ro": "romanian", "hu": "hungarian", "mk": "macedonian", "yue": "cantonese",
                  "fil": "filipino"}


# Ming-3.0-tts's words for the values of each Delivery Control (its cookbook's "Speech Control").
MING_CONTROLS = {
    "emotion": {"happy": "高兴", "sad": "悲伤", "angry": "愤怒", "fearful": "恐惧", "disgusted": "厌恶", "surprised": "惊讶",
                "neutral": "中性"},
    "speed": {"slow": "慢速", "medium": "中速", "fast": "快速"},
    "pitch": {"low": "低", "medium": "中", "high": "高"},
    "volume": {"low": "低", "medium": "中", "high": "高"},
}


def _ming_caption(*, ip=None, style=None, controls=None):
    """Ming-3.0-tts's control caption, a JSON object it reads before the text: a Preset Voice (ip), a voice design
    (style) and the Delivery Controls in Ming's words."""
    translated = {field: MING_CONTROLS[field][value] for field, value in (controls or {}).items()}
    return ming3_instruction(ip=ip, style=style, **translated)


class _Architecture:
    """The arguments besides its text that a Line is read with, as Qwen3-TTS and VoxCPM2 take them. Each architecture
    that takes them otherwise is a subclass; `_architecture` picks one when the Model loads."""

    def __init__(self, extra_repos):
        self.extra_repos = extra_repos

    def lang_code(self, language):
        return LANGUAGE_NAMES[language]

    def synthesize(self, *, voice, style, controls, language):
        return {"voice": voice, "instruct": style, "lang_code": self.lang_code(language)}

    def clone(self, *, reference, reference_text, style, controls, language):
        if style:
            # Only VoxCPM2 is given a style. Continuing a recording, it would read the style out as part of the text,
            # so a styled Line takes ref_audio alone for the voice and the style as its instruct.
            return {"ref_audio": str(reference), "instruct": style, "lang_code": self.lang_code(language)}
        # Qwen3-TTS Base clones from ref_audio and ref_text. VoxCPM2 takes ref_audio for the voice and continues
        # prompt_audio, read as prompt_text, for its closest likeness (upstream's "ultimate cloning"). Chatterbox takes
        # ref_audio alone. Each Model's generate ignores the others' arguments.
        return {"ref_audio": str(reference), "ref_text": reference_text, "prompt_audio": str(reference),
                "prompt_text": reference_text, "lang_code": self.lang_code(language)}

    def design(self, *, description, language):
        # Without reference audio, VoxCPM2 reads "({instruct}){text}": a voice that fits the description.
        return {"instruct": description, "lang_code": self.lang_code(language)}


class _Ming(_Architecture):
    def synthesize(self, *, voice, style, controls, language):
        # Ming is never given a style. It takes its Voice as one more field of the caption: mlx-audio's own voice
        # argument would refuse Delivery Controls beside it, and silently drop a Voice whose name has a space or
        # parentheses.
        return {"instruct": _ming_caption(ip=voice, controls=controls), "use_zero_spk_emb": True,
                "lang_code": self.lang_code(language)}

    def clone(self, *, reference, reference_text, style, controls, language):
        # Ming ignores ref_audio without ref_text, so it always takes both. With Delivery Controls it also needs a
        # speaker slot, if an empty one: without it, a short Line often comes back as a fraction of a second of noise.
        arguments = {"ref_audio": str(reference), "ref_text": reference_text, "lang_code": self.lang_code(language)}
        if controls:
            arguments.update(instruct=_ming_caption(controls=controls), use_zero_spk_emb=True)
        return arguments

    def design(self, *, description, language):
        # Ming designs a voice from the caption's style field and an empty speaker slot, as its README does.
        return {"instruct": _ming_caption(style=description), "use_zero_spk_emb": True,
                "lang_code": self.lang_code(language)}


class _Chatterbox(_Architecture):
    def lang_code(self, language):
        # Chatterbox names a language by its tag, as a Narration does, and refuses the English name.
        return language


class _Moss(_Architecture):
    def clone(self, *, reference, reference_text, style, controls, language):
        # MOSS-TTS-Nano clones from ref_audio alone and reads no language tag. It loads its audio tokenizer on the
        # first Line, from the copy `voxx install` made rather than by name.
        [tokenizer] = self.extra_repos.values()
        return {"ref_audio": str(reference), "audio_tokenizer_source": str(tokenizer)}


def _architecture(model):
    """How the Model mlx-audio loaded takes a Line's arguments. Most name their architecture in config.model_type;
    Ming-3.0's says "dense", as Ming Omni's does, so mlx-audio marks it with `ming3` instead."""
    if getattr(model, "ming3", False):
        return _Ming
    model_type = getattr(getattr(model, "config", None), "model_type", "")
    return {"chatterbox": _Chatterbox, "moss_tts_nano": _Moss}.get(model_type, _Architecture)


class MlxAudioEngine:
    # mlx-audio's Models share no typed interface.
    model: Any
    architecture: _Architecture

    def load(self, path, capability, *, extra_repos):
        # mlx-audio loads Models that speak and Models that listen through different loaders.
        if capability in ("transcribe", "align"):
            self.model = load_stt(path)
        else:
            self.model = load_tts(path)
            self.architecture = _architecture(self.model)(extra_repos)

    def synthesize(self, text, *, model, voice, style, controls, language, seed):
        return self._read(model, seed, text=text, **self.architecture.synthesize(voice=voice, style=style,
                                                                                 controls=controls, language=language))

    def clone(self, text, *, model, reference, reference_text, style, controls, language, seed):
        return self._read(model, seed, text=text, **self.architecture.clone(
            reference=reference, reference_text=reference_text, style=style, controls=controls, language=language))

    def design(self, text, *, model, description, language, seed):
        return self._read(model, seed, text=text, **self.architecture.design(description=description, language=language))

    def _read(self, model, seed, **arguments):
        # mlx samples from one global generator, so seeding it before each Line makes the Line independent of the others.
        mx.random.seed(seed)
        # CustomVoice Models never split a Line; an empty split_pattern keeps the Base ones from splitting it at newlines.
        results = list(self.model.generate(**arguments, split_pattern="", verbose=False))
        mx.clear_cache()
        if len(results) != 1:
            raise VoxxError("engine_split_line", f"mlx-audio read the Line in {len(results)} parts instead of one.",
                            BUG_HINT, {"model": model, "parts": len(results)})
        samples = np.asarray(results[0].audio, dtype=np.float32)
        # MOSS-TTS-Nano reads in stereo, as [samples, channels]; a Line is mono.
        return (samples.mean(axis=1) if samples.ndim == 2 else samples), results[0].sample_rate

    def transcribe(self, path, *, model, language):
        # Greedy decoding, so the same Line is always heard the same way; the path lets mlx-audio resample to 16 kHz.
        # No language lets Qwen3-ASR detect it.
        text = self.model.generate(str(path), language=language and LANGUAGE_NAMES[language], verbose=False).text
        mx.clear_cache()
        return text

    def align(self, path, *, model, text, language):
        # The aligner splits the text into words itself: by character for Chinese, by space for English.
        result = self.model.generate(str(path), text=text, language=LANGUAGE_NAMES[language])
        mx.clear_cache()
        return [(item.text, item.start_time, item.end_time) for item in result]
