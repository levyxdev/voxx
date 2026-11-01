"""Voices: the Preset Voices of the Models, and the Cloned Voices `voxx voice add` stores. Lightweight: the CLI imports it.

A Cloned Voice is a directory `<voices dir>/<name>/` holding voice.json and the normalized Reference Recording. The
voices dir is $VOXX_HOME/voices, or the one --voices-dir names, such as a directory in the user's project."""

import json
import shutil
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path

from voxx.files import staging
from voxx.models import (check_language, default_clone_model, find_model, is_installed, list_preset_voices, model_dir,
                         models, preset_voice_names, require_installed, resolve_preset_voice, transcriber_for,
                         unsupported_capability, voxx_home)
from voxx.narration import FILE_NAME_BYTES, is_file_name
from voxx.output import UNSUPPORTED, USAGE, VoxxError
from voxx.worker.client import WorkerProcess

VOICE_FILE = "voice.json"
REFERENCE_FILE = "reference.wav"
NAME_RULE = ("A Cloned Voice's name is visible text that does not start with '.', has no '/', '\\', control or "
             f"formatting characters, and is at most {FILE_NAME_BYTES} bytes in UTF-8.")
VOICES_DIR_HINT = "Pass the same --voices-dir the Cloned Voice was added with."


@dataclass(frozen=True)
class ClonedVoice:
    name: str
    path: Path
    reference_text: str
    # The Model that reads it unless `voxx narrate --model` picks another.
    model: str
    source: str
    created: str
    # The Model that transcribed the Reference Recording; None if the reference text was given.
    transcribed_by: str | None

    @property
    def reference(self):
        return self.path / REFERENCE_FILE

    def to_json(self):
        cloners = [m for m in models() if "clone" in m.capabilities]
        return {"name": self.name, "kind": "cloned", "reference_text": self.reference_text, "model": self.model,
                "languages": list(dict.fromkeys(l for m in cloners for l in m.languages)),
                "models": [{"model": m.id, "installed": is_installed(m)} for m in cloners],
                "path": str(self.path), "source": self.source, "created": self.created, "transcribed_by": self.transcribed_by}


def voices_dir(path=None):
    return Path(path).resolve() if path is not None else voxx_home() / "voices"


def list_voices(directory=None):
    """`voxx voices`: every Preset Voice, then every Cloned Voice in the voices dir."""
    return {"voices": [*list_preset_voices(), *(v.to_json() for v in cloned_voices(directory))]}


def cloned_voices(directory=None):
    root = voices_dir(directory)
    if not root.is_dir():
        return []
    return [_load(path) for path in sorted(root.iterdir())
            if path.is_dir() and not path.name.startswith(".") and (path / VOICE_FILE).exists()]


def find_cloned_voice(name, directory=None):
    path = voices_dir(directory) / name
    if not is_file_name(name) or not (path / VOICE_FILE).exists():
        return None
    voice = _load(path)
    # A case-insensitive file system finds "Narrator" for "narrator"; Voices match by their exact name.
    return voice if voice.name == name else None


def resolve_voice(voice, language, model=None, directory=None):
    """The Model that reads this Voice in this language, the Voice's name, and the Cloned Voice it names, if any.

    A Preset Voice resolves as `resolve_preset_voice` does; a Cloned Voice is read by the Model it was added with,
    unless `model` is given."""
    if voice is None or voice in preset_voice_names():
        return (*resolve_preset_voice(voice, language, model), None)
    cloned = find_cloned_voice(voice, directory)
    if cloned is None:
        known = [*preset_voice_names(), *(v.name for v in cloned_voices(directory))]
        raise VoxxError("unknown_voice", f"No Preset Voice or Cloned Voice is named {voice!r}.",
                        "Use one of the Voices in details.known_voices, or run `voxx voices` with the same --voices-dir.",
                        {"voice": voice, "known_voices": known, "voices_dir": str(voices_dir(directory))}, USAGE)
    if model is None:
        model = find_model(cloned.model)
    elif "clone" not in model.capabilities:
        raise unsupported_capability(model, "clone", "read a Cloned Voice")
    check_language(model, language)
    return model, voice, cloned


def add_voice(name, ref, ref_text=None, model_id=None, directory=None, overwrite=False):
    """`voxx voice add`: normalize the Reference Recording, transcribe it unless its words are given, and store both as
    a Cloned Voice."""
    if not is_file_name(name):
        raise VoxxError("invalid_voice_name", f"{name!r} cannot name a Cloned Voice. {NAME_RULE}", "Pick another name.",
                        {"name": name}, USAGE)
    if name in preset_voice_names():
        raise VoxxError("voice_exists", f"{name!r} is a Preset Voice.", "Pick another name.", {"name": name}, USAGE)
    model = find_model(model_id) if model_id is not None else default_clone_model()
    if "clone" not in model.capabilities:
        raise unsupported_capability(model, "clone", "clone a Voice")
    source = Path(ref).resolve()
    if not source.is_file():
        raise VoxxError("reference_not_found", f"No Reference Recording at {source}.", "Check the path given to --ref.",
                        {"ref": str(source)}, USAGE)
    if ref_text is not None and not ref_text.strip():
        raise VoxxError("invalid_reference_text", "--ref-text is empty.",
                        "Pass the words of the Reference Recording, or leave --ref-text out to transcribe them.", {}, USAGE)
    root = voices_dir(directory)
    path = root / name
    if path.exists() and not overwrite:
        raise VoxxError("voice_exists", f"A Cloned Voice is already stored at {path}.",
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
        raise VoxxError("invalid_voices_dir", f"Cannot store Cloned Voices in {root}: {e.strerror}.",
                        "Pass a writable directory for --voices-dir.", {"voices_dir": str(root)}, USAGE)

    words = (ref_text or "").strip()
    with staging(root) as stage:
        with WorkerProcess() as worker:
            prepared = worker.call("prepare_reference", source=str(source), path=str(stage / REFERENCE_FILE))
            if transcriber is not None:
                words = worker.call("transcribe_line", model=transcriber.id, engine=transcriber.engine,
                                    model_path=str(model_dir(transcriber)), capability="transcribe", language=None,
                                    path=str(stage / REFERENCE_FILE))["transcript"].strip()
                if not words:
                    raise VoxxError("reference_not_transcribed", f"Model {transcriber.id} heard no words in {source}.",
                                    "Pass the words of the Reference Recording with --ref-text, or record it again.",
                                    {"ref": str(source), "model": transcriber.id}, USAGE)
        voice = ClonedVoice(name, path, words, model.id, str(source),
                            datetime.now(UTC).isoformat(timespec="seconds"), transcriber and transcriber.id)
        (stage / VOICE_FILE).write_text(json.dumps(
            {"name": voice.name, "reference_text": voice.reference_text, "model": voice.model, "source": voice.source,
             "created": voice.created, "transcribed_by": voice.transcribed_by}, ensure_ascii=False, indent=2) + "\n",
            encoding="utf-8")
        _put(stage, path)
    return {**voice.to_json(), "warnings": prepared["warnings"]}


def _put(stage, path):
    """Moves the finished Cloned Voice into place, so the earlier one with its name, if any, is never half replaced."""
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
    except (OSError, UnicodeDecodeError, ValueError, KeyError, TypeError) as e:
        raise VoxxError("invalid_cloned_voice", f"Cannot use the Cloned Voice at {path}: {e}",
                        "Add the Voice again with `voxx voice add --overwrite`, or remove its directory.",
                        {"path": str(file)}, USAGE)
    return ClonedVoice(path=path, transcribed_by=transcribed_by, **fields)
