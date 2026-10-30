"""`voxx schema`: every command's arguments and result as JSON Schema, so agents never guess."""

from voxx.models import CAPABILITIES
from voxx.narration import LANGUAGES, LINE_ID_RULE
from voxx.output import USAGE, VoxxError

DRAFT = "https://json-schema.org/draft/2020-12/schema"

_non_empty_string = {"type": "string", "minLength": 1}

NARRATION_INPUT = {
    "$schema": DRAFT,
    "title": "Narration",
    "description": "Lines in one language, read in order. Unknown fields are kept as they are.",
    "type": "object",
    "required": ["language", "lines"],
    "properties": {
        "language": {"enum": list(LANGUAGES)},
        "voice": {**_non_empty_string, "description": "Default Voice for every Line. Omit for the default Preset Voice."},
        "style": {**_non_empty_string, "description": "Default delivery, in natural language; passed to the Model as an instruction."},
        "lines": {
            "type": "array",
            "minItems": 1,
            "items": {
                "type": "object",
                "required": ["id", "text"],
                "properties": {
                    "id": {**_non_empty_string,
                           "description": "Unique within the Narration, ignoring case and Unicode normalization; "
                                          f"names the Line's audio file. {LINE_ID_RULE}"},
                    "text": _non_empty_string,
                    "voice": {**_non_empty_string, "description": "Overrides the Narration's voice for this Line."},
                    "style": {**_non_empty_string, "description": "Overrides the Narration's style for this Line."},
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

_license = {"type": "object", "required": ["id", "url"],
            "properties": {"id": {"type": "string", "description": "SPDX id."}, "url": {"type": "string"}}}
_model_id = {"type": "string", "description": "A Model id from `voxx models`."}

MODEL = {
    "type": "object",
    "required": ["id", "capabilities", "languages", "size_bytes", "sample_rate", "weights_license", "code_license",
                 "verified", "repo", "revision", "installed"],
    "properties": {
        "id": _model_id,
        "capabilities": {"type": "array", "items": {"enum": list(CAPABILITIES)}},
        "languages": {"type": "array", "items": {"enum": list(LANGUAGES)}},
        "size_bytes": {"type": "integer", "description": "Download size."},
        "sample_rate": {"type": ["integer", "null"], "description": "Native output sample rate in Hz; null if the Model does not speak."},
        "weights_license": {**_license, "description": "License of the weights; every listed Model allows commercial use."},
        "code_license": {**_license, "description": "License of the upstream code."},
        "verified": {"type": "string", "format": "date", "description": "When the licenses were last checked."},
        "repo": {"type": "string", "description": "Hugging Face repo `voxx install` downloads."},
        "revision": {"type": "string", "description": "The pinned commit of that repo."},
        "installed": {"type": "boolean"},
    },
}

INSTALL_SUMMARY = {
    "type": "object",
    "description": "What to tell the user before running `voxx install <model>`.",
    "required": ["model", "size_bytes", "license", "license_url"],
    "properties": {"model": _model_id, "size_bytes": {"type": "integer"},
                   "license": {"type": "string", "description": "SPDX id of the weights license."},
                   "license_url": {"type": "string"}},
}

MODEL_NOT_INSTALLED = {
    "$schema": DRAFT,
    "description": "details of a model_not_installed error (exit code 3).",
    "type": "object",
    "required": ["missing", "total_bytes"],
    "properties": {
        "missing": {"type": "array", "items": INSTALL_SUMMARY},
        "total_bytes": {"type": "integer"},
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
        "errors": {"model_not_installed": MODEL_NOT_INSTALLED},
    },
    "models": {
        "usage": "voxx models [--capability <capability>] [--installed | --not-installed]",
        "description": "List the registered Models: only Models whose weights allow commercial use.",
        "arguments": {
            "$schema": DRAFT,
            "type": "object",
            "properties": {
                "capability": {"enum": list(CAPABILITIES), "description": "Only Models with this capability (--capability)."},
                "installed": {"type": "boolean", "description": "Only installed (--installed) or not installed (--not-installed) Models."},
            },
        },
        "result": {"$schema": DRAFT, "type": "object", "required": ["models"],
                   "properties": {"models": {"type": "array", "items": MODEL}}},
    },
    "install": {
        "usage": "voxx install <model>",
        "description": "Download a Model into $VOXX_HOME/models. The only command that downloads; ask the user first. "
                       "Resumes an interrupted download; honors HF_ENDPOINT for a Hugging Face mirror.",
        "arguments": {
            "$schema": DRAFT,
            "type": "object",
            "required": ["model"],
            "properties": {"model": {**_model_id, "description": "Model id (positional)."}},
        },
        "result": {
            "$schema": DRAFT,
            "type": "object",
            "required": ["model", "path", "size_bytes", "already_installed"],
            "properties": {"model": _model_id, "path": {"type": "string"}, "size_bytes": {"type": "integer"},
                           "already_installed": {"type": "boolean", "description": "True if nothing was downloaded."}},
        },
    },
    "doctor": {
        "usage": "voxx doctor",
        "description": "Check the platform, the installed Models and free disk space before narrating. Always exits 0.",
        "arguments": {"$schema": DRAFT, "type": "object", "properties": {}},
        "result": {
            "$schema": DRAFT,
            "type": "object",
            "required": ["platform", "home", "disk", "models"],
            "properties": {
                "platform": {
                    "type": "object",
                    "required": ["system", "machine", "apple_silicon", "supported"],
                    "properties": {"system": {"type": "string"}, "machine": {"type": "string"},
                                   "apple_silicon": {"type": "boolean"}, "supported": {"type": "boolean"},
                                   "reason": {"type": "string", "description": "Why voxx cannot run here; only when unsupported."}},
                },
                "home": {"type": "string", "description": "$VOXX_HOME."},
                "disk": {"type": "object", "required": ["path", "free_bytes"],
                         "properties": {"path": {"type": "string"}, "free_bytes": {"type": "integer"}}},
                "models": {
                    "type": "object",
                    "required": ["installed", "not_installed"],
                    "properties": {
                        "installed": {"type": "array", "items": _model_id},
                        "not_installed": {"type": "array", "items": INSTALL_SUMMARY},
                    },
                },
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
