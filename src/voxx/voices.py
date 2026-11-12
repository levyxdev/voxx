"""Voices: the Preset Voices of the Models, and the Cloned Voices and Designed Voices `voxx voice add` stores.
Lightweight: the CLI imports it.

A Cloned Voice or Designed Voice is a directory `<voices dir>/<name>/` holding voice.json and the normalized Reference
Recording: a recording of a person for a Cloned Voice, the chosen Design Take for a Designed Voice (ADR 0007). Both are read the same
way, by a Model that clones. The voices dir is $VOXX_HOME/voices, or the one --voices-dir names, such as a directory in
the user's project."""

import json
import re
import shutil
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path

from voxx.design import read_take
from voxx.files import staging
from voxx.models import (check_language, default_clone_model, find_model, is_installed, list_preset_voices, model_dir,
                         models, preset_voice_names, require_installed, resolve_preset_voice, transcriber_for,
                         unsupported_capability, voxx_home)
from voxx.narration import FILE_NAME_BYTES, LANGUAGE_PATTERN, LANGUAGE_RULE, canonical_case, is_file_name
from voxx.output import UNSUPPORTED, USAGE, VoxxError
from voxx.worker.client import WorkerProcess

VOICE_FILE = "voice.json"
REFERENCE_FILE = "reference.wav"
NAME_RULE = ("The name of a Cloned Voice or Designed Voice is visible text that does not start with '.', has no '/', "
             f"'\\', control or formatting characters, and is at most {FILE_NAME_BYTES} bytes in UTF-8.")
ARGS_HINT = "Run `voxx schema voice add` to see its arguments."


@dataclass(frozen=True)
class StoredVoice:
    name: str
    path: Path
    reference_text: str
    # The Model that reads it unless `voxx narrate --model` picks another.
    model: str
    source: str
    created: str
    # The Model that transcribed the Reference Recording; None if the reference text was given.
    transcribed_by: str | None
    # A Designed Voice's description, design_model, take and seed; None for a Cloned Voice.
    design: dict | None = None

    @property
    def kind(self):
        return "cloned" if self.design is None else "designed"

    @property
    def reference(self):
        return self.path / REFERENCE_FILE

    def voice_json(self):
        """What voice.json holds."""
        return {"name": self.name, "kind": self.kind, "reference_text": self.reference_text, "model": self.model,
                "source": self.source, "created": self.created, "transcribed_by": self.transcribed_by, **(self.design or {})}

    def to_json(self):
        cloners = [m for m in models() if "clone" in m.capabilities]
        return {**self.voice_json(), "languages": list(dict.fromkeys(l for m in cloners for l in m.languages)),
                "models": [{"model": m.id, "installed": is_installed(m)} for m in cloners], "path": str(self.path)}


def voices_dir(path=None):
    return Path(path).resolve() if path is not None else voxx_home() / "voices"


def list_voices(directory=None, model_id=None, language=None):
    """`voxx voices`: the Preset Voices, then the Cloned Voices and Designed Voices in the voices dir; with `model_id`,
    only the Voices that Model reads, and with `language`, only Preset Voices native to it and the other Voices a
    Model reads in it."""
    if language is not None and not re.fullmatch(LANGUAGE_PATTERN, language):
        canonical = canonical_case(language)
        raise VoxxError("invalid_language", f"--language {language!r}: {LANGUAGE_RULE}"
                        + (f" Write it as {canonical!r}." if canonical else ""), ARGS_HINT, {"language": language}, USAGE)
    model = find_model(model_id) if model_id is not None else None
    presets, unlisted = list_preset_voices(model, language)
    # Every Model that clones reads every Cloned Voice and Designed Voice.
    stored = [v.to_json() for v in stored_voices(directory)] if model is None or "clone" in model.capabilities else []
    stored = [v for v in stored if language is None or language in (model.languages if model else v["languages"])]
    return {"voices": [*presets, *stored], "unlisted": unlisted}


def stored_voices(directory=None):
    root = voices_dir(directory)
    if not root.is_dir():
        return []
    return [_load(path) for path in sorted(root.iterdir())
            if path.is_dir() and not path.name.startswith(".") and (path / VOICE_FILE).exists()]


def find_stored_voice(name, directory=None):
    path = voices_dir(directory) / name
    if not is_file_name(name) or not (path / VOICE_FILE).exists():
        return None
    voice = _load(path)
    # A case-insensitive file system finds "Narrator" for "narrator"; Voices match by their exact name.
    return voice if voice.name == name else None


def resolve_voice(voice, language, model=None, directory=None):
    """The Model that reads this Voice in this language, the Voice's name, and the Cloned Voice or Designed Voice it
    names, if any.

    A Preset Voice resolves as `resolve_preset_voice` does; a Cloned Voice or Designed Voice is read by the Model it was
    added with, unless `model` is given."""
    if voice is None or voice in preset_voice_names():
        return (*resolve_preset_voice(voice, language, model), None)
    stored = find_stored_voice(voice, directory)
    if stored is None:
        known = [*preset_voice_names(), *(v.name for v in stored_voices(directory))]
        raise VoxxError("unknown_voice", f"No Preset Voice, Cloned Voice or Designed Voice is named {voice!r}.",
                        "Use one of the Voices in details.known_voices, or run `voxx voices` with the same --voices-dir.",
                        {"voice": voice, "known_voices": known, "voices_dir": str(voices_dir(directory))}, USAGE)
    if model is None:
        model = find_model(stored.model)
    elif "clone" not in model.capabilities:
        raise unsupported_capability(model, "clone", f"read a {stored.kind.capitalize()} Voice")
    check_language(model, language)
    return model, voice, stored


def add_voice(name, ref=None, ref_text=None, model_id=None, directory=None, overwrite=False, from_design=None, take=None):
    """`voxx voice add`: normalize the Reference Recording, transcribe it unless its words are given, and store both as
    a Cloned Voice; or, with `from_design`, store the Design Take numbered `take` and the words it read as a Designed
    Voice."""
    if (ref is None) == (from_design is None):
        _invalid("Pass --ref with a recording for a Cloned Voice, or --from-design and --take for a Designed Voice.")
    if from_design is not None and ref_text is not None:
        _invalid("--ref-text goes with --ref: a Designed Voice's words are the text its Design Takes read.")
    if (from_design is None) != (take is None):
        _invalid("--from-design and --take go together: the --out of `voxx voice design` and the number of the Design "
                 "Take the user chose.")
    if not is_file_name(name):
        raise VoxxError("invalid_voice_name", f"{name!r} cannot name a Voice. {NAME_RULE}", "Pick another name.",
                        {"name": name}, USAGE)
    if name in preset_voice_names():
        raise VoxxError("voice_exists", f"{name!r} is a Preset Voice.", "Pick another name.", {"name": name}, USAGE)
    model = find_model(model_id) if model_id is not None else default_clone_model()
    if "clone" not in model.capabilities:
        raise unsupported_capability(model, "clone", "clone a Voice")
    design = None
    if ref is not None:
        source = Path(ref).resolve()
        if not source.is_file():
            raise VoxxError("reference_not_found", f"No Reference Recording at {source}.", "Check the path given to --ref.",
                            {"ref": str(source)}, USAGE)
    else:
        chosen = read_take(from_design, take)
        source, ref_text = chosen["audio"], chosen["text"]
        design = {"description": chosen["description"], "design_model": chosen["model"], "take": chosen["take"],
                  "seed": chosen["seed"]}
    if ref_text is not None and not ref_text.strip():
        raise VoxxError("invalid_reference_text", "--ref-text is empty.",
                        "Pass the words of the Reference Recording, or leave --ref-text out to transcribe them.", {}, USAGE)
    root = voices_dir(directory)
    path = root / name
    if path.exists() and not overwrite:
        raise VoxxError("voice_exists", f"A Voice is already stored at {path}.",
                        "Pick another name, or pass --overwrite to replace it.", {"name": name, "path": str(path)}, USAGE)
    transcriber = None
    if ref_text is None:
        # The words are what this step cannot do without, so here the transcriber must be installed (ADR 0006).
        transcriber = transcriber_for(model, None)
        if transcriber is None:
            raise VoxxError("cannot_transcribe", f"No Model on the Engine of {model.id} can transcribe.",
                            "Pass the words of the Reference Recording with --ref-text.", {"model": model.id}, UNSUPPORTED)
        require_installed([transcriber])
    try:
        root.mkdir(parents=True, exist_ok=True)
    except OSError as e:
        raise VoxxError("invalid_voices_dir", f"Cannot store Voices in {root}: {e.strerror}.",
                        "Pass a writable directory for --voices-dir.", {"voices_dir": str(root)}, USAGE)

    words = (ref_text or "").strip()
    with staging(root) as stage:
        with WorkerProcess("voice add") as worker:
            prepared = worker.call("prepare_reference", source=str(source), path=str(stage / REFERENCE_FILE))
            if transcriber is not None:
                words = worker.call("transcribe_line", model=transcriber.id, engine=transcriber.engine,
                                    model_path=str(model_dir(transcriber)), capability="transcribe", language=None,
                                    path=str(stage / REFERENCE_FILE))["transcript"].strip()
                if not words:
                    raise VoxxError("reference_not_transcribed", f"Model {transcriber.id} heard no words in {source}.",
                                    "Pass the words of the Reference Recording with --ref-text, or record it again.",
                                    {"ref": str(source), "model": transcriber.id}, USAGE)
        voice = StoredVoice(name, path, words, model.id, str(source),
                            datetime.now(UTC).isoformat(timespec="seconds"), transcriber and transcriber.id, design)
        (stage / VOICE_FILE).write_text(json.dumps(voice.voice_json(), ensure_ascii=False, indent=2) + "\n",
                                        encoding="utf-8")
        _put(stage, path)
    return {**voice.to_json(), "warnings": prepared["warnings"]}


def _put(stage, path):
    """Moves the finished Voice into place, so the earlier one with its name, if any, is never half replaced."""
    if not path.exists():
        stage.rename(path)
        return
    earlier = stage.with_name(stage.name + "-replaced")
    path.rename(earlier)
    try:
        stage.rename(path)
    except BaseException:
        earlier.rename(path)
        raise
    shutil.rmtree(earlier, ignore_errors=True)


def _load(path):
    file = path / VOICE_FILE
    try:
        data = json.loads(file.read_text(encoding="utf-8"))
        fields = {k: data[k] for k in ("name", "reference_text", "model", "source", "created")}
        if not all(isinstance(v, str) and v.strip() for v in fields.values()):
            raise ValueError("name, reference_text, model, source and created must be non-empty strings")
        transcribed_by = data.get("transcribed_by")
        if transcribed_by is not None and not isinstance(transcribed_by, str):
            raise ValueError("transcribed_by must be a string or null")
        if fields["name"] != path.name:
            raise ValueError(f"it names the Voice {fields['name']!r}, not {path.name!r}")
        if not (path / REFERENCE_FILE).is_file():
            raise ValueError(f"{REFERENCE_FILE} is missing")
        # A voice.json from before Designed Voices has no kind: it is a Cloned Voice.
        kind, design = data.get("kind", "cloned"), None
        if kind == "designed":
            design = {k: data[k] for k in ("description", "design_model", "take", "seed")}
            if not (isinstance(design["description"], str) and isinstance(design["design_model"], str)
                    and isinstance(design["take"], int) and isinstance(design["seed"], int)):
                raise ValueError("description and design_model must be strings, and take and seed integers")
        elif kind != "cloned":
            raise ValueError(f"kind must be 'cloned' or 'designed', not {kind!r}")
    except (OSError, UnicodeDecodeError, ValueError, KeyError, TypeError) as e:
        raise VoxxError("invalid_cloned_voice", f"Cannot use the Voice stored at {path}: {e}",
                        "Add the Voice again with `voxx voice add --overwrite`, or remove its directory.",
                        {"path": str(file)}, USAGE)
    return StoredVoice(path=path, transcribed_by=transcribed_by, design=design, **fields)


def _invalid(message):
    raise VoxxError("invalid_arguments", message, ARGS_HINT, {}, USAGE)
