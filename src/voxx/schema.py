"""`voxx schema`: every command's arguments and result as JSON Schema, so agents never guess."""

from voxx.narration import LANGUAGES, LINE_ID
from voxx.output import USAGE, VoxxError

DRAFT = "https://json-schema.org/draft/2020-12/schema"

_text = {"type": "string", "minLength": 1}

NARRATION_INPUT = {
    "$schema": DRAFT,
    "title": "Narration",
    "description": "Lines in one language, read in order. Unknown fields are kept as they are.",
    "type": "object",
    "required": ["language", "lines"],
    "properties": {
        "language": {"enum": list(LANGUAGES)},
        "voice": {**_text, "description": "Default Voice for every Line. Omit for the default Preset Voice."},
        "style": {**_text, "description": "Default delivery, in natural language; passed to the Model as an instruction."},
        "lines": {
            "type": "array",
            "minItems": 1,
            "items": {
                "type": "object",
                "required": ["id", "text"],
                "properties": {
                    "id": {"type": "string", "pattern": LINE_ID.pattern,
                           "description": "Unique within the Narration, ignoring case; names the Line's audio file."},
                    "text": _text,
                    "voice": {**_text, "description": "Overrides the Narration's voice for this Line."},
                    "style": {**_text, "description": "Overrides the Narration's style for this Line."},
                },
            },
        },
    },
}

LINE_OUTPUT_FIELDS = {
    "audio": {"type": "string", "description": "Mono WAV, relative to the output Narration file."},
    "model": {"type": "string"},
    "voice": {"type": "string"},
    "seed": {"type": "integer", "description": "Seed the Line was read with."},
    "sample_rate": {"type": "integer", "description": "The Model's native sample rate, in Hz."},
}

NARRATION_OUTPUT = {
    **NARRATION_INPUT,
    "title": "Narration (completed)",
    "description": "The input Narration, unchanged, with each Line completed by voxx.",
    "properties": {
        **NARRATION_INPUT["properties"],
        "lines": {
            **NARRATION_INPUT["properties"]["lines"],
            "items": {
                **NARRATION_INPUT["properties"]["lines"]["items"],
                "required": ["id", "text", *LINE_OUTPUT_FIELDS],
                "properties": {**NARRATION_INPUT["properties"]["lines"]["items"]["properties"], **LINE_OUTPUT_FIELDS},
            },
        },
    },
}

COMMANDS = {
    "narrate": {
        "usage": "voxx narrate <narration.json> --out <dir>",
        "description": "Read every Line of a Narration, write <dir>/<id>.wav per Line and <dir>/narration.json.",
        "arguments": {
            "$schema": DRAFT,
            "type": "object",
            "required": ["narration", "out"],
            "properties": {
                "narration": {"type": "string", "description": "Path to the Narration file (positional)."},
                "out": {"type": "string", "description": "Output directory (--out); created if missing."},
            },
        },
        "input": NARRATION_INPUT,
        "result": {
            "$schema": DRAFT,
            "type": "object",
            "required": ["path", "narration"],
            "properties": {
                "path": {"type": "string", "description": "Absolute path of the written Narration file."},
                "narration": NARRATION_OUTPUT,
            },
        },
    },
    "schema": {
        "usage": "voxx schema [<command>]",
        "description": "Describe every command, or just one.",
        "arguments": {
            "$schema": DRAFT,
            "type": "object",
            "properties": {"command": {"type": "string", "description": "Command name (positional)."}},
        },
        "result": {"$schema": DRAFT, "type": "object", "description": "This document, or one entry of its commands."},
    },
}

CONTRACT = {
    "stdout": "Exactly one JSON object: {\"ok\": true, \"data\": <result>} or {\"ok\": false, \"error\": <error>}.",
    "stderr": "NDJSON progress events, each an object with an \"event\" field.",
    "error": {
        "$schema": DRAFT,
        "type": "object",
        "required": ["code", "message", "hint", "details"],
        "properties": {"code": {"type": "string"}, "message": {"type": "string"}, "hint": {"type": "string"},
                       "details": {"type": "object"}},
    },
    "exit_codes": {
        "0": "Success.",
        "1": "Internal error, including a crashed worker: report it.",
        "2": "Invalid arguments or input: fix them.",
        "3": "Model not installed: tell the user its size and license, and run `voxx install` once they agree.",
        "4": "The Model cannot do this: pick another Model or Voice.",
    },
}


def schema(command=None):
    if command is None:
        return {**CONTRACT, "commands": COMMANDS}
    if command not in COMMANDS:
        raise VoxxError("unknown_command", f"No command named {command!r}.", "Run `voxx schema` to list every command.",
                        {"commands": list(COMMANDS)}, USAGE)
    return {command: COMMANDS[command]}
