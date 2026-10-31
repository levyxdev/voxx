"""Runs Models through mlx-audio on Apple Silicon. Imported only inside the worker (ADR 0002)."""

from typing import Any

import mlx.core as mx
import numpy as np
from mlx_audio.stt.utils import load as load_stt
from mlx_audio.tts.utils import load as load_tts

from voxx.output import BUG_HINT, VoxxError

# Narrations name languages by BCP 47 tag; mlx-audio names them in English.
LANGUAGE_NAMES = {"zh": "chinese", "en": "english", "ja": "japanese", "ko": "korean", "fr": "french", "de": "german",
                  "it": "italian", "pt": "portuguese", "ru": "russian", "es": "spanish", "ar": "arabic", "id": "indonesian",
                  "th": "thai", "vi": "vietnamese", "tr": "turkish", "hi": "hindi", "ms": "malay", "nl": "dutch",
                  "sv": "swedish", "da": "danish", "fi": "finnish", "pl": "polish", "cs": "czech", "fa": "persian",
                  "el": "greek", "ro": "romanian", "hu": "hungarian", "mk": "macedonian", "yue": "cantonese",
                  "fil": "filipino"}


class MlxAudioEngine:
    # mlx-audio's Models share no typed interface.
    model: Any

    def load(self, path, capability):
        # mlx-audio loads Models that speak and Models that listen through different loaders.
        self.model = load_stt(path) if capability in ("transcribe", "align") else load_tts(path)

    def synthesize(self, text, *, model, voice, style, language, seed):
        # mlx samples from one global generator, so seeding it before each Line makes the Line independent of the others.
        mx.random.seed(seed)
        # CustomVoice Models never split a Line; an empty split_pattern keeps the Base ones from splitting it at newlines.
        results = list(self.model.generate(text=text, voice=voice, instruct=style, lang_code=LANGUAGE_NAMES[language],
                                           split_pattern="", verbose=False))
        if len(results) != 1:
            raise VoxxError("engine_split_line", f"mlx-audio read the Line in {len(results)} parts instead of one.",
                            BUG_HINT, {"model": model, "parts": len(results)})
        return np.asarray(results[0].audio, dtype=np.float32), results[0].sample_rate

    def transcribe(self, path, *, model, language):
        # Greedy decoding, so the same Line is always heard the same way; the path lets mlx-audio resample to 16 kHz.
        return self.model.generate(str(path), language=LANGUAGE_NAMES[language], verbose=False).text

    def align(self, path, *, model, text, language):
        # The aligner splits the text into words itself: by character for Chinese, by space for English.
        result = self.model.generate(str(path), text=text, language=LANGUAGE_NAMES[language])
        return [(item.text, item.start_time, item.end_time) for item in result]
