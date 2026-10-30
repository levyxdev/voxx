"""Reading and checking a Narration file (ADR 0001)."""

import json
import re
import unicodedata
from pathlib import Path

from voxx.output import USAGE, VoxxError

LANGUAGES = ("zh", "en")
# A Line id names its audio file, so it must be a safe file name: no path separators, no control characters,
# not hidden. Any other text works, such as "开场" or "step 1".
LINE_ID = re.compile(r"^[^./\\\x00-\x1f\x7f-\x9f][^/\\\x00-\x1f\x7f-\x9f]*$")
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
    if narration.get("language") not in LANGUAGES:
        _invalid("$.language", f"language must be one of {', '.join(LANGUAGES)}.")
    for field in ("voice", "style"):
        _optional_string(narration, field, "$")
    lines = narration.get("lines")
    if not isinstance(lines, list) or not lines:
        _invalid("$.lines", "lines must be a non-empty array of Lines.")
    seen = {}
    for i, line in enumerate(lines):
        where = f"$.lines[{i}]"
        if not isinstance(line, dict):
            _invalid(where, "Each Line must be a JSON object.")
        line_id = line.get("id")
        if not isinstance(line_id, str) or not LINE_ID.fullmatch(line_id):
            _invalid(f"{where}.id", "id must be non-empty, must not start with '.', and must not contain '/', '\\' or control characters.")
        # Audio files are named after ids, and macOS file names ignore case and Unicode normalization.
        key = unicodedata.normalize("NFC", line_id).casefold()
        if key in seen:
            _invalid(f"{where}.id", f"id {line_id!r} repeats the id of $.lines[{seen[key]}].")
        seen[key] = i
        if not isinstance(line.get("text"), str) or not line["text"].strip():
            _invalid(f"{where}.text", "text must be a non-empty string.")
        for field in ("voice", "style"):
            _optional_string(line, field, where)


def line_setting(narration, line, field):
    """A Line's voice or style: its own, else the Narration's default, else None."""
    return line.get(field, narration.get(field))


def _optional_string(obj, field, where):
    if field in obj and not (isinstance(obj[field], str) and obj[field].strip()):
        _invalid(f"{where}.{field}", f"{field} must be a non-empty string when given.")


def _invalid(where, message):
    raise VoxxError("invalid_narration", f"{where}: {message}", NARRATION_HINT, {"at": where}, USAGE)
