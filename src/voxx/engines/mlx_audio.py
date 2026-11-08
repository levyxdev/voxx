"""Runs Models through mlx-audio on Apple Silicon. Imported only inside the worker (ADR 0002)."""

from typing import Any

import mlx.core as mx
import numpy as np
from mlx_audio.stt.utils import load as load_stt
from mlx_audio.tts.models.bailingmm.bailingmm import ming3_instruction
from mlx_audio.tts.utils import load as load_tts

from voxx.output import BUG_HINT, VoxxError

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


class MlxAudioEngine:
    # mlx-audio's Models share no typed interface.
    model: Any

    def load(self, path, capability):
        # mlx-audio loads Models that speak and Models that listen through different loaders.
        self.model = load_stt(path) if capability in ("transcribe", "align") else load_tts(path)

    @property
    def ming(self):
        return getattr(self.model, "ming3", False)

    def synthesize(self, text, *, model, voice, style, controls, language, seed):
        if self.ming:
            # Ming is never given a style. It takes its Voice as one more field of the caption: mlx-audio's own voice
            # argument would refuse Delivery Controls beside it, and silently drop a Voice whose name has a space or
            # parentheses.
            return self._read(model, seed, text=text, instruct=_ming_caption(ip=voice, controls=controls),
                              use_zero_spk_emb=True, lang_code=LANGUAGE_NAMES[language])
        return self._read(model, seed, text=text, voice=voice, instruct=style, lang_code=LANGUAGE_NAMES[language])

    @property
    def chatterbox(self):
        return getattr(getattr(self.model, "config", None), "model_type", None) == "chatterbox"

    def clone(self, text, *, model, reference, reference_text, style, controls, language, seed):
        # Chatterbox names a language by its tag, as a Narration does, and refuses the English name.
        lang_code = language if self.chatterbox else LANGUAGE_NAMES[language]
        if self.ming:
            # Ming ignores ref_audio without ref_text, so it always takes both. With Delivery Controls it also needs a
            # speaker slot, if an empty one: without it, a short Line often comes back as a fraction of a second of noise.
            if not controls:
                return self._read(model, seed, text=text, ref_audio=str(reference), ref_text=reference_text,
                                  lang_code=lang_code)
            return self._read(model, seed, text=text, ref_audio=str(reference), ref_text=reference_text,
                              instruct=_ming_caption(controls=controls), use_zero_spk_emb=True, lang_code=lang_code)
        if style:
            # Of the others, only VoxCPM2 is given a style. Continuing a recording, it would read the style out as part
            # of the text, so a styled Line takes ref_audio alone for the voice and the style as its instruct.
            return self._read(model, seed, text=text, ref_audio=str(reference), instruct=style, lang_code=lang_code)
        # Qwen3-TTS Base clones from ref_audio and ref_text. VoxCPM2 takes ref_audio for the voice and continues
        # prompt_audio, read as prompt_text, for its closest likeness (upstream's "ultimate cloning"). Chatterbox takes
        # ref_audio alone. Each Model's generate ignores the others' arguments.
        return self._read(model, seed, text=text, ref_audio=str(reference), ref_text=reference_text,
                          prompt_audio=str(reference), prompt_text=reference_text, lang_code=lang_code)

    def design(self, text, *, model, description, language, seed):
        if self.ming:
            # Ming designs a voice from the caption's style field and an empty speaker slot, as its README does.
            return self._read(model, seed, text=text, instruct=_ming_caption(style=description), use_zero_spk_emb=True,
                              lang_code=LANGUAGE_NAMES[language])
        # Without reference audio, VoxCPM2 reads "({instruct}){text}": a voice that fits the description.
        return self._read(model, seed, text=text, instruct=description, lang_code=LANGUAGE_NAMES[language])

    def _read(self, model, seed, **arguments):
        # mlx samples from one global generator, so seeding it before each Line makes the Line independent of the others.
        mx.random.seed(seed)
        # CustomVoice Models never split a Line; an empty split_pattern keeps the Base ones from splitting it at newlines.
        results = list(self.model.generate(**arguments, split_pattern="", verbose=False))
        if len(results) != 1:
            raise VoxxError("engine_split_line", f"mlx-audio read the Line in {len(results)} parts instead of one.",
                            BUG_HINT, {"model": model, "parts": len(results)})
        return np.asarray(results[0].audio, dtype=np.float32), results[0].sample_rate

    def transcribe(self, path, *, model, language):
        # Greedy decoding, so the same Line is always heard the same way; the path lets mlx-audio resample to 16 kHz.
        # No language lets Qwen3-ASR detect it.
        return self.model.generate(str(path), language=language and LANGUAGE_NAMES[language], verbose=False).text

    def align(self, path, *, model, text, language):
        # The aligner splits the text into words itself: by character for Chinese, by space for English.
        result = self.model.generate(str(path), text=text, language=LANGUAGE_NAMES[language])
        return [(item.text, item.start_time, item.end_time) for item in result]
