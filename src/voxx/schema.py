"""`voxx schema`: every command's arguments and result as JSON Schema, so agents never guess."""

from voxx.models import CAPABILITIES, LISTED_VOICES_MAX
from voxx.narration import CONTROLS, LANGUAGE_PATTERN, LANGUAGE_RULE, LINE_ID_RULE, MAX_SEED
from voxx.output import USAGE, VoxxError

DRAFT = "https://json-schema.org/draft/2020-12/schema"

_non_empty_string = {"type": "string", "minLength": 1}
_language = {"type": "string", "pattern": LANGUAGE_PATTERN,
             "description": "BCP 47 tag in canonical case, such as zh, yue or en-US. Matches a Model's languages exactly."}
_seed = {"type": "integer", "minimum": 0, "maximum": MAX_SEED}
_model_id = {"type": "string", "description": "A Model id from `voxx models`."}

_EXTRA_REPOS = ("Hugging Face repos the Model's Engine also loads, downloaded with it. Present only for a Model that has "
                "any. Not pinned: `voxx install` downloads each one's current revision, so its size can differ from "
                "the one voxx checked.")
INSTALL_SUMMARY = {
    "type": "object",
    "description": "What to tell the user before running `voxx install <model>`.",
    "required": ["model", "size_bytes", "license", "license_url"],
    "properties": {"model": _model_id,
                   "size_bytes": {"type": "integer", "description": "Download size, extra repos included."},
                   "license": {"type": "string", "description": "SPDX id of the weights license."},
                   "license_url": {"type": "string"},
                   "extra_repos": {"type": "array", "description": _EXTRA_REPOS + " Tell the user about them too.",
                                   "items": {"type": "object", "required": ["repo", "size_bytes", "license", "license_url"],
                                             "properties": {"repo": {"type": "string"}, "size_bytes": {"type": "integer"},
                                                            "license": {"type": "string", "description": "SPDX id."},
                                                            "license_url": {"type": "string"}}}}},
}

# Delivery Controls: the delivery a Line asks for by value, where style asks in words.
_CONTROL_WORDS = {"emotion": "Default emotion", "speed": "Default speaking rate", "pitch": "Default pitch",
                  "volume": "Default speaking volume; each Line is still normalized to -18 LUFS, so it cannot make a "
                            "Line louder"}
_CONTROLS = {field: {"enum": list(values), "description": f"{_CONTROL_WORDS[field]} for every Line. Only a Model that "
                                                         "follows Delivery Controls (ming-3.0-tts-0.5b) reads it; any "
                                                         "other ignores it with a controls_ignored warning."}
             for field, values in CONTROLS.items()}

NARRATION_INPUT = {
    "$schema": DRAFT,
    "title": "Narration",
    "description": "Lines in one language, read in order. Unknown fields are kept as they are.",
    "type": "object",
    "required": ["language", "lines"],
    "properties": {
        "language": {**_language, "description": f"{LANGUAGE_RULE} The Model must read it; see `voxx models`."},
        "voice": {**_non_empty_string, "description": "Default Voice for every Line, from `voxx voices`: a Preset Voice, "
                                                      "or a Cloned Voice or Designed Voice from `voxx voice add`, read "
                                                      "by the Model it was added with. Omit for the Model's first "
                                                      "Preset Voice native to the language."},
        "style": {**_non_empty_string, "description": "Default delivery, in natural language; passed to the Model as an "
                                                      "instruction. Ignored, with a warning, by a Model that cannot follow it."},
        **_CONTROLS,
        "seed": {**_seed, "description": "Default seed for every Line. Omit for a random one per Line; the same seed, "
                                         "Model, Voice, style, Delivery Controls and text read the same way again."},
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
                    **{field: {**schema, "description": f"Overrides the Narration's {field} for this Line."}
                       for field, schema in _CONTROLS.items()},
                    "seed": {**_seed, "description": "Overrides the Narration's seed for this Line."},
                },
            },
        },
    },
}

# Only on aligner_not_installed and checker_not_installed warnings.
MISSING_MODEL = {
    **INSTALL_SUMMARY,
    "description": "The Model the Line was read without, because it is not installed. Tell the user its size and "
                   "license; once they agree, run command, then read the Line again with --line.",
    "required": [*INSTALL_SUMMARY["required"], "command"],
    "properties": {**INSTALL_SUMMARY["properties"],
                   "command": {"type": "string", "description": "The `voxx install` command that installs it."}},
}

LINE_OUTPUT_FIELDS = {
    "audio": {"type": "string", "description": "Mono WAV at the Model's native sample rate, at -18 LUFS with 50 ms of "
                                               "silence before and after the speech; relative to the output Narration file."},
    "model": {"type": "string"},
    "voice": {"type": "string", "description": "The name of the Preset Voice, Cloned Voice or Designed Voice the Line "
                                               "was read in."},
    "seed": {"type": "integer", "description": "Seed the Line was read with."},
    "sample_rate": {"type": "integer", "description": "The Model's native sample rate, in Hz."},
    "warnings": {"type": "array", "description": "What did not go as asked, such as a style (style_ignored) or "
                                                  "Delivery Controls (controls_ignored) the Model ignored, a Line "
                                                  "that could not reach -18 LUFS without clipping, a Line without "
                                                  "words (not_aligned) because no Model aligns its language or the "
                                                  "aligner failed, a Line read with --check but not checked "
                                                  "(not_checked) because no Model can transcribe its language, a Line "
                                                  "without words (aligner_not_installed) or, with --check, not checked "
                                                  "(checker_not_installed) "
                                                  "because the Model that would do it is not installed, or a Line kept by "
                                                  "--line whose audio is stale (stale_audio) because the Narration now "
                                                  "gives it other text, another language, another Voice, another "
                                                  "style or other Delivery Controls.",
                 "items": {"type": "object", "required": ["code", "message"],
                           "properties": {"code": {"type": "string"}, "message": {"type": "string"},
                                          "details": MISSING_MODEL}}},
}

# Only on Lines a Model aligned; any other Line has a not_aligned or aligner_not_installed warning instead.
ALIGN_FIELDS = {
    "words": {"type": "array",
              "description": "Word Timing: each word of the text in order, without punctuation; each Chinese "
                             "character is a word. start and end are seconds into the Line's "
                             "audio file, silence included, in whole milliseconds; 0 <= start <= end <= the audio's "
                             "length, and no word starts before the one before it ends.",
              "items": {"type": "object", "required": ["text", "start", "end"],
                        "properties": {"text": {"type": "string"}, "start": {"type": "number", "minimum": 0},
                                       "end": {"type": "number", "minimum": 0}}}},
}

# Only on Lines read with --check that an installed Model transcribed; any other Line read with --check has a
# not_checked or checker_not_installed warning instead.
SELF_CHECK_FIELDS = {
    "transcript": {"type": "string", "description": "The Line's audio, transcribed by the Model that transcribes its language."},
    "error_rate": {"type": "number", "minimum": 0,
                   "description": "Edits from text to transcript per unit of text: each Chinese, Japanese or Korean "
                                  "character is a unit (CER), and so is each run of other letters and digits (WER). "
                                  "Punctuation, spacing and case do not count; words heard but not written do, so it "
                                  "can exceed 1. voxx only reports it: decide yourself whether to read the Line again."},
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
                "properties": {**NARRATION_INPUT["properties"]["lines"]["items"]["properties"], **LINE_OUTPUT_FIELDS,
                               **ALIGN_FIELDS, **SELF_CHECK_FIELDS},
            },
        },
    },
}

_license = {"type": "object", "required": ["id", "url"],
            "properties": {"id": {"type": "string", "description": "SPDX id."}, "url": {"type": "string"}}}

MODEL = {
    "type": "object",
    "required": ["id", "capabilities", "languages", "size_bytes", "sample_rate", "weights_license", "code_license",
                 "verified", "repo", "revision", "installed"],
    "properties": {
        "id": _model_id,
        "capabilities": {"type": "array", "items": {"enum": list(CAPABILITIES)}},
        "languages": {"type": "array", "items": _language},
        "size_bytes": {"type": "integer", "description": "Download size, extra repos included."},
        "sample_rate": {"type": ["integer", "null"], "description": "Native output sample rate in Hz; null if the Model does not speak."},
        "weights_license": {**_license, "description": "License of the weights; every listed Model allows commercial use."},
        "code_license": {**_license, "description": "License of the upstream code."},
        "verified": {"type": "string", "format": "date", "description": "When the licenses were last checked."},
        "repo": {"type": "string", "description": "Hugging Face repo `voxx install` downloads."},
        "revision": {"type": "string", "description": "The pinned commit of that repo."},
        "installed": {"type": "boolean", "description": "False if an extra repo is missing too."},
        "extra_repos": {"type": "array", "description": _EXTRA_REPOS,
                        "items": {"type": "object", "required": ["repo", "size_bytes", "license"],
                                  "properties": {"repo": {"type": "string"},
                                                 "size_bytes": {"type": "integer", "description": "Size when checked."},
                                                 "license": _license}}},
    },
}

_installed_models = {"type": "array", "items": {"type": "object", "required": ["model", "installed"],
                                               "properties": {"model": _model_id, "installed": {"type": "boolean"}}}}

PRESET_VOICE = {
    "type": "object",
    "required": ["name", "kind", "native_language", "description", "languages", "models"],
    "properties": {
        "name": {"type": "string", "description": "What a Narration's voice names."},
        "kind": {"const": "preset"},
        "native_language": _language,
        "description": {"type": "string", "description": "How the Voice sounds, from the Model's makers."},
        "languages": {"type": "array", "items": _language, "description": "Languages a Model reads this Voice in."},
        "models": {**_installed_models, "description": "The Models that have this Voice."},
    },
}

CLONED_VOICE = {
    "type": "object",
    "required": ["name", "kind", "reference_text", "model", "languages", "models", "path", "source", "created",
                 "transcribed_by"],
    "properties": {
        "name": {"type": "string", "description": "What a Narration's voice names."},
        "kind": {"const": "cloned"},
        "reference_text": {"type": "string", "description": "The words of the Reference Recording."},
        "model": {**_model_id, "description": "The Model that reads the Voice, unless `voxx narrate --model` names "
                                              "another Model with the clone capability."},
        "languages": {"type": "array", "items": _language, "description": "Languages a Model reads this Voice in."},
        "models": {**_installed_models, "description": "Every Model that can read this Voice: the Models that clone."},
        "path": {"type": "string", "description": "The Voice's directory, holding voice.json and reference.wav: the "
                                                  "Reference Recording as mono 24 kHz WAV at -18 LUFS, with 50 ms of "
                                                  "silence before and after the speech."},
        "source": {"type": "string", "description": "Absolute path of the recording given to --ref."},
        "created": {"type": "string", "format": "date-time"},
        "transcribed_by": {"type": ["string", "null"],
                           "description": "The Model that transcribed reference_text; null if --ref-text gave it."},
    },
}

DESIGNED_VOICE = {
    "type": "object",
    "description": "A Voice designed from a text description with `voxx voice design`, fixed by the Design Take the "
                   "user chose, which is its Reference Recording. A Model that clones reads it, as it reads a Cloned "
                   "Voice, in any language that Model reads.",
    "required": [*CLONED_VOICE["required"], "description", "design_model", "take", "seed"],
    "properties": {
        **CLONED_VOICE["properties"],
        "kind": {"const": "designed"},
        "reference_text": {"type": "string", "description": "The text the Design Takes read."},
        "source": {"type": "string", "description": "Absolute path of the chosen Design Take's audio."},
        "transcribed_by": {"type": "null"},
        "description": {"type": "string", "description": "The description the chosen Design Take was designed from."},
        "design_model": {**_model_id, "description": "The Model that designed it."},
        "take": {"type": "integer", "description": "The number of the chosen Design Take (--take)."},
        "seed": {"type": "integer", "description": "The seed the chosen Design Take was read with."},
    },
}

_voices_dir = {"type": "string", "description": "Directory of Cloned Voices and Designed Voices (--voices-dir), such "
                                                "as one in the user's project; omit for $VOXX_HOME/voices."}

_ADD_WARNINGS = {"type": "array", "description": "What did not go as asked, such as a recording that could not reach "
                                               "-18 LUFS without clipping.",
                 "items": {"type": "object", "required": ["code", "message"],
                           "properties": {"code": {"type": "string"}, "message": {"type": "string"}}}}

MODEL_NOT_INSTALLED = {
    "$schema": DRAFT,
    "description": "details of a model_not_installed error (exit code 3): the Models that read the Lines. A missing "
                   "aligner, or with --check transcriber, is a warning on each Line instead.",
    "type": "object",
    "required": ["missing", "total_bytes"],
    "properties": {
        "missing": {"type": "array", "items": INSTALL_SUMMARY},
        "total_bytes": {"type": "integer"},
    },
}

COMMANDS = {
    "narrate": {
        "usage": "voxx narrate <narration.json> --out <dir> [--model <model>] [--line <id>]... [--voices-dir <dir>] "
                 "[--check]",
        "description": "Read every Line of a Narration, time each word, and write <dir>/<id>.wav per Line and "
                       "<dir>/narration.json. With --check, also transcribe each Line back to check it. Only the Model "
                       "that reads must be installed: without the aligner, or with --check the transcriber, the Lines "
                       "are read without words or the check, with a warning. "
                       "The completed Narration, read again with the same --model, gives the same audio. "
                       "With --line, read only those Lines again and keep every other Line, and its audio file, "
                       "as <dir>/narration.json from the earlier run has it.",
        "arguments": {
            "$schema": DRAFT,
            "type": "object",
            "required": ["narration", "out"],
            "properties": {
                "narration": {"type": "string", "description": "Path to the Narration file (positional)."},
                "out": {"type": "string", "description": "Output directory (--out); created if missing."},
                "model": {**_model_id, "description": "The Model that reads every Line (--model). Omit for the Model "
                                                      "that has each Line's Preset Voice, the Model each Cloned Voice or "
                                                      "Designed Voice was added with, or the default Model."},
                "line": {"type": "array", "items": _non_empty_string,
                         "description": "Ids of Lines to read again (--line, once per id), after a whole run into the "
                                        "same --out. Each is read with a new seed: the one the Narration file gives it, "
                                        "if that differs from the seed it was read with before, else a random one. "
                                        "Every other Line keeps its audio file and fields from the earlier run."},
                "voices_dir": {**_voices_dir, "description": "Where to find the Cloned Voices and Designed Voices "
                                                             "the Narration names (--voices-dir): the directory they "
                                                             "were added to; omit for $VOXX_HOME/voices."},
                "check": {"type": "boolean", "default": False,
                          "description": "Transcribe each Line back and report transcript and error_rate (--check). Off "
                                         "by default: it loads the transcriber beside the reader, which takes more "
                                         "memory and time, and the user listens anyway. Pass it when the user asks "
                                         "for the check or will not listen to every Line."},
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
        "errors": {
            "model_not_installed": MODEL_NOT_INSTALLED,
            "invalid_narration": {"description": "Exit 2: details.at points at what is wrong in the Narration file."},
            "unknown_voice": {"description": "Exit 2: no Preset Voice, or Cloned Voice or Designed Voice in "
                                             "details.voices_dir, has this name; details.known_voices lists them."},
            "invalid_cloned_voice": {"description": "Exit 2: the directory of a Cloned Voice or Designed Voice, "
                                                    "details.path, cannot be read; add the Voice again with --overwrite."},
            "unknown_model": {"description": "Exit 2: no Model by the id given to --model; details.known_models lists them."},
            "capability_unsupported": {"description": "Exit 4: the Model given to --model cannot read Preset Voices, "
                                                      "or cannot clone to read a Cloned Voice or Designed Voice "
                                                      "(details.capability)."},
            "voice_unsupported": {"description": "Exit 4: the Model given to --model lacks this Voice; details.voices lists its own."},
            "unsupported_language": {"description": "Exit 4: the Model cannot read the language; details.languages lists what it reads."},
            "unknown_line": {"description": "Exit 2: no Line has an id given to --line; details.known_lines lists them."},
            "no_earlier_output": {"description": "Exit 2: --line needs <dir>/narration.json from a whole run first."},
            "invalid_earlier_output": {"description": "Exit 2: <dir>/narration.json from the earlier run cannot be read; "
                                                       "read the whole Narration again."},
            "line_not_read": {"description": "Exit 2: details.unread lists Lines the earlier run did not read and "
                                             "--line does not name."},
        },
    },
    "voice add": {
        "usage": "voxx voice add <name> (--ref <recording> [--ref-text <text>] | --from-design <dir> --take <n>) "
                 "[--model <model>] [--voices-dir <dir>] [--overwrite]",
        "description": "Store a Cloned Voice: normalize the Reference Recording (mono, 24 kHz, -18 LUFS, 50 ms of "
                       "silence at each end), transcribe it unless --ref-text gives its words, and save both as "
                       "<voices dir>/<name>/. A Narration then names it as its voice. voxx does not check consent: "
                       "before --ref, ask the user to confirm they have the right to use this voice. Only without "
                       "--ref-text must a Model be installed: the one that transcribes. With --from-design and --take "
                       "instead, store a Designed Voice: the Design Take the user chose from a `voxx voice design` run "
                       "is its Reference Recording and the text it read is its words, so no Model needs to be "
                       "installed, and there is no consent to ask about.",
        "arguments": {
            "$schema": DRAFT,
            "type": "object",
            "required": ["name"],
            "oneOf": [{"required": ["ref"], "not": {"anyOf": [{"required": ["from_design"]}, {"required": ["take"]}]}},
                      {"required": ["from_design", "take"],
                       "not": {"anyOf": [{"required": ["ref"]}, {"required": ["ref_text"]}]}}],
            "properties": {
                "name": {**_non_empty_string,
                         "description": "The Voice's name (positional): not a Preset Voice's name, and a safe file "
                                        "name: visible text that does not start with '.' and has no '/' or '\\'."},
                "ref": {"type": "string", "description": "The Reference Recording (--ref): WAV, MP3 or FLAC, or with "
                                                         "ffmpeg installed M4A, Ogg, AIFF and more. A few seconds to "
                                                         "half a minute of one person speaking clearly."},
                "ref_text": {**_non_empty_string, "description": "Its words, exactly as spoken (--ref-text). Omit to "
                                                                 "transcribe them, which needs the transcribing Model."},
                "from_design": {"type": "string", "description": "The --out of a finished `voxx voice design` run "
                                                                 "(--from-design), holding design.json."},
                "take": {"type": "integer", "minimum": 1, "description": "The number of the Design Take the user chose "
                                                                         "(--take), as design.json lists it."},
                "model": {**_model_id, "description": "The Model that clones, which reads the Voice from then on "
                                                      "(--model). Omit for the default, the first Model with the "
                                                      "clone capability in `voxx models`."},
                "voices_dir": {**_voices_dir, "description": "Where to store the Voice (--voices-dir), such as a "
                                                             "directory in the user's project; omit for "
                                                             "$VOXX_HOME/voices. Pass the same one to narrate."},
                "overwrite": {"type": "boolean", "description": "Replace the Cloned Voice or Designed Voice of "
                                                               "this name (--overwrite)."},
            },
        },
        "result": {
            "$schema": DRAFT,
            "oneOf": [{**voice, "required": [*voice["required"], "warnings"],
                       "properties": {**voice["properties"], "warnings": _ADD_WARNINGS}}
                      for voice in (CLONED_VOICE, DESIGNED_VOICE)],
        },
        "errors": {
            "model_not_installed": {**MODEL_NOT_INSTALLED,
                                    "description": "details of a model_not_installed error (exit code 3): the Model "
                                                   "that transcribes the Reference Recording. Install it once the "
                                                   "user agrees, or pass --ref-text instead."},
            "invalid_voice_name": {"description": "Exit 2: the name cannot name a directory."},
            "voice_exists": {"description": "Exit 2: a Preset Voice, Cloned Voice or Designed Voice has this name; "
                                            "pass --overwrite to replace a Cloned Voice or Designed Voice."},
            "design_not_found": {"description": "Exit 2: no design.json in --from-design; pass the --out of a "
                                                "`voxx voice design` run that finished."},
            "invalid_design": {"description": "Exit 2: design.json in --from-design, or the audio of the chosen Design "
                                              "Take, cannot be read; design the voice again into a new --out."},
            "take_not_found": {"description": "Exit 2: design.json has no Design Take numbered --take; details.takes "
                                              "lists the numbers it has."},
            "reference_not_found": {"description": "Exit 2: no file at --ref."},
            "invalid_reference_text": {"description": "Exit 2: --ref-text is empty."},
            "unreadable_reference": {"description": "Exit 2: the file at --ref cannot be decoded as audio."},
            "silent_reference": {"description": "Exit 2: the recording is silent."},
            "reference_not_transcribed": {"description": "Exit 2: no words were heard; pass --ref-text."},
            "invalid_voices_dir": {"description": "Exit 2: --voices-dir cannot be created or written."},
            "unknown_model": {"description": "Exit 2: no Model by the id given to --model; details.known_models lists them."},
            "capability_unsupported": {"description": "Exit 4: the Model given to --model cannot clone."},
            "cannot_transcribe": {"description": "Exit 4: no Model can transcribe for this Model; pass --ref-text."},
        },
    },
    "voice design": {
        "usage": "voxx voice design --describe <description> [--describe <description>]... --text <text> "
                 "--language <tag> --out <dir> [--takes <n>] [--model <model>] [--check]",
        "description": "Design new voices from text descriptions: read --text --takes times for each description, each "
                       "time with a new seed and so in a new voice, as Design Takes for the user to listen to and choose "
                       "from. Writes <dir>/take-<n>.wav, numbered in the order of the descriptions, and "
                       "<dir>/design.json. Stores no Voice. With --check, each take is transcribed back to check it, as a "
                       "Line is: a take that reads its description out loud shows it in its transcript. Only the "
                       "Model that designs must be installed: with --check but without the transcriber, the takes "
                       "come without the check, with a warning.",
        "arguments": {
            "$schema": DRAFT,
            "type": "object",
            "required": ["describe", "text", "language", "out"],
            "properties": {
                "describe": {"type": "array", "minItems": 1, "items": _non_empty_string,
                             "description": "How a voice should sound (--describe, once per description), in natural "
                                            "language: traits such as age, gender, timbre, pace and mood, never a real "
                                            "person. Compare styles with several descriptions, then pick a voice with "
                                            "--takes on the one the user likes."},
                "text": {**_non_empty_string, "description": "The words every Design Take reads (--text): a few short "
                                                             "sentences in the language and tone of the Narration the "
                                                             "voice is for."},
                "language": {**_language, "description": f"The language of --text (--language). {LANGUAGE_RULE}"},
                "out": {"type": "string", "description": "Output directory (--out); created if missing. Must not hold "
                                                         "design.json from an earlier run."},
                "takes": {"type": "integer", "minimum": 1, "default": 1,
                          "description": "How many Design Takes to read for each description (--takes)."},
                "model": {**_model_id, "description": "The Model that designs (--model). Omit for the default, the "
                                                      "first Model with the design capability in `voxx models`."},
                "check": {"type": "boolean", "default": False,
                          "description": "Transcribe each Design Take back and report transcript and error_rate (--check). Off "
                                         "by default: it loads the transcriber beside the reader, which takes more "
                                         "memory and time, and the user listens anyway. Pass it when the user asks "
                                         "for the check or will not listen to every take."},
            },
        },
        "result": {
            "$schema": DRAFT,
            "type": "object",
            "required": ["path", "design"],
            "properties": {
                "path": {"type": "string", "description": "Absolute path of the written design.json."},
                "design": {
                    "type": "object",
                    "description": "The contents of design.json.",
                    "required": ["model", "language", "text", "takes"],
                    "properties": {
                        "model": _model_id,
                        "language": _language,
                        "text": {"type": "string"},
                        "takes": {"type": "array", "items": {
                            "type": "object",
                            "required": ["take", "description", "seed", "audio", "sample_rate", "warnings"],
                            "properties": {
                                "take": {"type": "integer", "minimum": 1, "description": "The n of take-<n>.wav."},
                                "description": {"type": "string", "description": "The --describe it was read from."},
                                "seed": {"type": "integer", "description": "Seed it was read with."},
                                "audio": {**LINE_OUTPUT_FIELDS["audio"],
                                          "description": "Mono WAV at the Model's native sample rate, at -18 LUFS with "
                                                         "50 ms of silence before and after the speech; relative to "
                                                         "design.json."},
                                "sample_rate": LINE_OUTPUT_FIELDS["sample_rate"],
                                "warnings": {**LINE_OUTPUT_FIELDS["warnings"],
                                             "description": "What did not go as asked, such as a take that could not "
                                                            "reach -18 LUFS without clipping, or a take read with "
                                                            "--check but not checked because no Model transcribes its "
                                                            "language (not_checked) "
                                                            "or the one that would is not installed "
                                                            "(checker_not_installed)."},
                                "transcript": {**SELF_CHECK_FIELDS["transcript"],
                                               "description": "The take, transcribed back; only with --check."},
                                "error_rate": SELF_CHECK_FIELDS["error_rate"],
                            },
                        }},
                    },
                },
            },
        },
        "errors": {
            "model_not_installed": {**MODEL_NOT_INSTALLED,
                                    "description": "details of a model_not_installed error (exit code 3): the Model "
                                                   "that designs. With --check, a missing transcriber is a warning on "
                                                   "each take instead."},
            "invalid_arguments": {"description": "Exit 2: a description or the text is empty, or --takes is below 1."},
            "invalid_language": {"description": "Exit 2: --language is not a BCP 47 tag in canonical case."},
            "unknown_model": {"description": "Exit 2: no Model by the id given to --model; details.known_models lists them."},
            "capability_unsupported": {"description": "Exit 4: the Model given to --model cannot design a voice."},
            "unsupported_language": {"description": "Exit 4: the Model cannot read the language; details.languages lists what it reads."},
            "design_exists": {"description": "Exit 2: --out already holds design.json from an earlier run; pass a new "
                                             "directory."},
            "invalid_out": {"description": "Exit 2: --out cannot be created or written."},
        },
    },
    "voices": {
        "usage": "voxx voices [--model <model>] [--language <language>] [--voices-dir <dir>]",
        "description": "List the Preset Voices and the Models that read them, then the Cloned Voices and Designed "
                       f"Voices in the voices dir. A Model with more than {LISTED_VOICES_MAX} Preset Voices, such as "
                       "ming-3.0-tts-0.5b, is only summarized in unlisted unless --model names it.",
        "arguments": {"$schema": DRAFT, "type": "object", "properties": {
            "model": {**_model_id, "description": "Only the Voices this Model reads (--model): every one of its Preset "
                                                  "Voices, and the Cloned Voices and Designed Voices if it clones."},
            "language": {**_language, "description": "Only Preset Voices native to this language, and Cloned Voices and "
                                                     "Designed Voices a Model reads in it (--language)."},
            "voices_dir": _voices_dir}},
        "result": {
            "$schema": DRAFT,
            "type": "object",
            "required": ["voices", "unlisted"],
            "properties": {
                "voices": {"type": "array", "items": {"oneOf": [PRESET_VOICE, CLONED_VOICE, DESIGNED_VOICE]}},
                "unlisted": {
                    "type": "array",
                    "description": "Each Model whose Preset Voices are left out of voices; run command to list them.",
                    "items": {"type": "object", "required": ["model", "installed", "voices", "native_languages", "command"],
                              "properties": {"model": _model_id, "installed": {"type": "boolean"},
                                             "voices": {"type": "integer", "description": "How many are left out."},
                                             "native_languages": {"type": "object",
                                                                  "additionalProperties": {"type": "integer"},
                                                                  "description": "How many of them are native to each "
                                                                                 "language."},
                                             "command": {"type": "string"}}},
                },
            },
        },
        "errors": {
            "unknown_model": {"description": "Exit 2: no Model by the id given to --model; details.known_models lists them."},
            "invalid_language": {"description": "Exit 2: --language is not a BCP 47 tag in canonical case."},
            "invalid_cloned_voice": {"description": "Exit 2: the directory of a Cloned Voice or Designed Voice, "
                                                    "details.path, cannot be read; add the Voice again with "
                                                    "--overwrite, or remove the directory."},
        },
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
        "description": "Download a Model into $VOXX_HOME/models, and its extra repos, if any, into $VOXX_HOME/hf-cache. "
                       "The only command that downloads; ask the user first. Resumes an interrupted download; honors "
                       "HF_ENDPOINT for a Hugging Face mirror.",
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
            "properties": {"model": _model_id, "path": {"type": "string"},
                           "size_bytes": {"type": "integer", "description": "Installed size, extra repos included."},
                           "already_installed": {"type": "boolean", "description": "True if nothing was downloaded."},
                           "extra_repos": {"type": "array", "description": "The extra repos installed with the Model, "
                                                                           "at the revision downloaded. Present only "
                                                                           "for a Model that has any.",
                                           "items": {"type": "object", "required": ["repo", "revision", "size_bytes", "path"],
                                                     "properties": {"repo": {"type": "string"},
                                                                    "revision": {"type": "string"},
                                                                    "size_bytes": {"type": "integer"},
                                                                    "path": {"type": "string"}}}}},
        },
        "errors": {
            "unknown_model": {"description": "Exit 2: no Model by that id; details.known_models lists them."},
            "download_failed": {"description": "Exit 1: the network or the hub failed. Run the same install again to resume."},
            "download_corrupt": {"description": "Exit 1: a file did not match the hub's checksum and was deleted. Run install again."},
            "invalid_repo": {"description": "Exit 1: the hub at HF_ENDPOINT does not serve the pinned files. Check HF_ENDPOINT."},
            "insufficient_disk_space": {"description": "Exit 1: details.required_bytes exceeds details.free_bytes; nothing was downloaded."},
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
        "description": "Describe every command, or just one, such as `voxx schema narrate` or `voxx schema voice add`.",
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
        "3": "Model not installed: tell the user its size and license, and any extra repos it downloads with it, and "
             "run `voxx install` once they agree.",
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
