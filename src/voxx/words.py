"""Word Timing: an aligner's words, made safe to cut a Line's audio by. Lightweight: the CLI imports it."""

import math
import unicodedata
import wave


def word_timings(text, aligned, path):
    """The aligner's [word, start, end] list as a Line's `words`: in milliseconds, in order, never overlapping, and
    within the audio at path. None if the words do not spell out the text, ignoring punctuation and spacing."""
    if _letters("".join(word for word, _, _ in aligned)) != _letters(text):
        return None
    with wave.open(str(path)) as audio:
        # Rounded down, so no word ends after the audio does.
        duration = math.floor(audio.getnframes() / audio.getframerate() * 1000) / 1000
    words, previous_end = [], 0.0
    for word, start, end in aligned:
        start = min(max(round(start, 3), previous_end), duration)
        end = min(max(round(end, 3), start), duration)
        words.append({"text": word, "start": start, "end": end})
        previous_end = end
    return words


def _letters(text):
    return "".join(c for c in unicodedata.normalize("NFKC", text) if unicodedata.category(c)[0] in "LN")
