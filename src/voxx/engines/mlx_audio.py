"""Runs Models through mlx-audio on Apple Silicon. Imported only inside the worker (ADR 0002)."""

import mlx.core as mx
import numpy as np
from mlx_audio.tts.utils import load

from voxx.output import BUG_HINT, VoxxError

# Narrations name languages by ISO 639-1 code; mlx-audio names them in English.
LANGUAGE_NAMES = {"zh": "chinese", "en": "english", "ja": "japanese", "ko": "korean", "fr": "french", "de": "german",
                  "it": "italian", "pt": "portuguese", "ru": "russian", "es": "spanish"}


class MlxAudioEngine:
    def load(self, path):
        self.model = load(path)

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
