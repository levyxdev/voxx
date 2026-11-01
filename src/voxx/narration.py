"""Reading and checking a Narration file (ADR 0001)."""

import json
import re
import unicodedata
from pathlib import Path
from typing import NoReturn

from voxx.output import USAGE, VoxxError

# Which languages a Narration may use is up to the Model that reads it; here only the form is checked (ADR 0005).
LANGUAGE_RULE = ("language must be a BCP 47 tag in canonical case: a language, then optionally a script and a region, "
                 "such as zh, yue, en-US or zh-Hant-HK.")
LANGUAGE_PATTERN = "^[a-z]{2,3}(-[A-Z][a-z]{3})?(-([A-Z]{2}|[0-9]{3}))?$"
# Seeds fit in 31 bits, so every Engine can take them.
MAX_SEED = 2**31 - 1
SEED_RULE = f"seed must be an integer from 0 to {MAX_SEED}."
# A Line id names its audio file, so it must be a safe, visible file name. Any other text works, such as "开场" or "step 1".
# Control, formatting, surrogate, and line or paragraph separator characters.
UNSAFE_CATEGORIES = {"Cc", "Cf", "Cs", "Zl", "Zp"}
# The longest file name voxx writes for a Line, within macOS's 255-byte limit.
LONGEST_SUFFIX = ".wav.partial"
FILE_NAME_BYTES = 255
LINE_ID_RULE = ("An id is visible text that does not start with '.', has no '/', '\\', control or formatting characters, "
                f"and is at most {FILE_NAME_BYTES - len(LONGEST_SUFFIX)} bytes in UTF-8.")
NARRATION_HINT = "Run `voxx schema narrate` to see the Narration file format."


def load_narration(path):
    path = Path(path)
    try:
        text = path.read_text(encoding="utf-8")
    except FileNotFoundError:
        raise VoxxError("narration_not_found", f"No Narration file at {path}.", "Check the path.", {"path": str(path)}, USAGE)
    except (OSError, UnicodeDecodeError) as e:
        raise VoxxError("narration_unreadable", f"Cannot read {path}: {e}", "Pass a UTF-8 JSON file.", {"path": str(path)}, USAGE)
    try:
        narration = json.loads(text)
    except json.JSONDecodeError as e:
        raise VoxxError("invalid_narration", f"{path} is not valid JSON: {e}", NARRATION_HINT, {"path": str(path)}, USAGE)
    check_narration(narration)
    return narration


def check_narration(narration):
    if not isinstance(narration, dict):
        _invalid("$", "The Narration must be a JSON object.")
    language = narration.get("language")
    if not (isinstance(language, str) and re.fullmatch(LANGUAGE_PATTERN, language)):
        canonical = _canonical_case(language) if isinstance(language, str) else None
        _invalid("$.language", LANGUAGE_RULE + (f" Write it as {canonical!r}." if canonical else ""))
    _check_settings(narration, "$")
    lines = narration.get("lines")
    if not isinstance(lines, list) or not lines:
        _invalid("$.lines", "lines must be a non-empty array of Lines.")
    seen = {}
    for i, line in enumerate(lines):
        where = f"$.lines[{i}]"
        if not isinstance(line, dict):
            _invalid(where, "Each Line must be a JSON object.")
        line_id = line.get("id")
        if not is_line_id(line_id):
            _invalid(f"{where}.id", LINE_ID_RULE)
        key = line_id_key(line_id)
        if key in seen:
            _invalid(f"{where}.id", f"id {line_id!r} repeats the id of $.lines[{seen[key]}].")
        seen[key] = i
        if not isinstance(line.get("text"), str) or not line["text"].strip():
            _invalid(f"{where}.text", "text must be a non-empty string.")
        _check_settings(line, where)


def is_line_id(value):
    return is_file_name(value, LONGEST_SUFFIX)


def is_file_name(value, suffix=""):
    """Whether `value`, followed by `suffix`, is a safe, visible file name."""
    return (isinstance(value, str) and bool(value.strip()) and not value.startswith(".")
            and not any(c in "/\\" or unicodedata.category(c) in UNSAFE_CATEGORIES for c in value)
            and len((value + suffix).encode("utf-8")) <= FILE_NAME_BYTES)


def line_id_key(line_id):
    """Ids that name the same audio file share a key: macOS file names ignore case and Unicode normalization."""
    return unicodedata.normalize("NFD", unicodedata.normalize("NFD", line_id).casefold())


def _canonical_case(tag):
    """The tag in canonical case if only its case is wrong, else None: zh-hant-hk is zh-Hant-HK."""
    first, *rest = tag.split("-")
    canonical = "-".join([first.lower(), *(s.title() if len(s) == 4 else s.upper() for s in rest)])
    return canonical if re.fullmatch(LANGUAGE_PATTERN, canonical) else None


def line_setting(narration, line, field):
    """A Line's voice, style or seed: its own, else the Narration's default, else None."""
    return line.get(field, narration.get(field))


def _check_settings(obj, where):
    """The settings a Narration gives every Line and a Line can override."""
    for field in ("voice", "style"):
        _optional_string(obj, field, where)
    seed = obj.get("seed", 0)
    if type(seed) is not int or not 0 <= seed <= MAX_SEED:
        _invalid(f"{where}.seed", SEED_RULE)


def _optional_string(obj, field, where):
    if field in obj and not (isinstance(obj[field], str) and obj[field].strip()):
        _invalid(f"{where}.{field}", f"{field} must be a non-empty string when given.")


def _invalid(where, message) -> NoReturn:
    raise VoxxError("invalid_narration", f"{where}: {message}", NARRATION_HINT, {"at": where}, USAGE)
