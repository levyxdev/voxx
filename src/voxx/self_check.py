"""The self-check: how far a Line's transcript is from its text. Lightweight: the CLI imports it."""

import unicodedata

# Scripts written without spaces between words: each character counts as one unit, as in CER.
CJK_SCRIPTS = ("CJK", "HIRAGANA", "KATAKANA", "HANGUL")
APOSTROPHES = "'’"


def error_rate(text, transcript):
    """Edits needed to turn the text into the transcript, per unit of the text.

    Chinese, Japanese and Korean characters count one unit each (CER); every run of other letters and digits counts
    one unit (WER), so a Chinese Line with an English word mixes the two. Punctuation, symbols, spacing, case and
    full-width forms do not count. Insertions count too, so a transcript with extra words can exceed 1."""
    reference, heard = _units(text), _units(transcript)
    if not reference:
        return float(bool(heard))
    return round(_edits(reference, heard) / len(reference), 4)


def _units(text):
    found, word = [], ""
    for c in unicodedata.normalize("NFKC", text).casefold():
        if c in APOSTROPHES:
            continue  # "you're" and "youre" are the same word
        if _is_cjk(c):
            found += [word, c] if word else [c]
            word = ""
        elif unicodedata.category(c)[0] in "LMN":
            word += c
        elif word:
            found.append(word)
            word = ""
    return found + [word] if word else found


def _is_cjk(c):
    return unicodedata.category(c)[0] == "L" and unicodedata.name(c, "").startswith(CJK_SCRIPTS)


def _edits(a, b):
    """Levenshtein distance between two lists."""
    row = list(range(len(b) + 1))
    for i, x in enumerate(a, start=1):
        diagonal, row[0] = row[0], i
        for j, y in enumerate(b, start=1):
            diagonal, row[j] = row[j], min(row[j] + 1, row[j - 1] + 1, diagonal + (x != y))
    return row[-1]
