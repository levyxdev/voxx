"""`voxx narrate`: read every Line of a Narration in one worker, then write the completed Narration.

The output directory changes only once every Line has been read: until then the new audio waits in a staging directory
inside it, so a run that fails leaves the earlier output exactly as it was."""

import errno
import json
import os
import secrets
from pathlib import Path

from voxx.files import replacing, staging
from voxx.models import aligner_for, find_model, is_installed, model_dir, require_installed, transcriber_for
from voxx.narration import MAX_SEED, check_narration, line_setting, load_narration
from voxx.output import USAGE, VoxxError, progress
from voxx.self_check import error_rate
from voxx.voices import resolve_voice
from voxx.words import word_timings
from voxx.worker.client import WorkerProcess

OUTPUT_NAME = "narration.json"
READ_ALL_HINT = "Read the whole Narration first: run `voxx narrate` without --line."


def narrate(narration_path, out_dir, model_id=None, line_ids=(), voices_dir=None):
    """Read every Line, or with `line_ids` only those Lines, keeping every other Line of the earlier output as it is.
    Cloned Voices are found in `voices_dir`, else in $VOXX_HOME/voices."""
    narration = load_narration(narration_path)
    out = Path(out_dir).resolve()
    chosen = find_model(model_id) if model_id is not None else None
    to_read, kept, earlier_seeds = narration["lines"], {}, {}
    if line_ids:
        to_read = _lines_to_read_again(narration, list(dict.fromkeys(line_ids)))
        earlier = _earlier_output(out)
        kept = _lines_to_keep(narration, earlier, to_read, chosen, voices_dir)
        earlier_seeds = {line["id"]: line.get("seed") for line in earlier["lines"]}
    # Plan every Line before starting the worker, so a bad Voice fails fast. Only the Models that read are required
    # (ADR 0006): a Line whose aligner or transcriber is not installed is read without it.
    plans = [_plan_line(narration, line, chosen, voices_dir, earlier_seeds.get(line["id"])) for line in to_read]
    require_installed(dict.fromkeys(plan["model"] for plan in plans))
    try:
        out.mkdir(parents=True, exist_ok=True)
        if not os.access(out, os.W_OK):
            raise PermissionError(errno.EACCES, "Permission denied")
    except OSError as e:
        raise VoxxError("invalid_out", f"Cannot use {out} as the output directory: {e.strerror}.",
                        "Pass a writable directory for --out.", {"out": str(out)}, USAGE)

    progress("narration_started", lines=len(plans))
    path = out / OUTPUT_NAME
    with staging(out) as stage:
        with WorkerProcess() as worker:
            for index, (line, plan) in enumerate(zip(to_read, plans), start=1):
                progress("line_started", id=line["id"], index=index, total=len(plans))
                _read_line(worker, narration, line, plan, stage)
                progress("line_done", id=line["id"], index=index, total=len(plans))
        narration["lines"] = [kept.get(line["id"], line) for line in narration["lines"]]
        with replacing(path) as partial:
            partial.write_text(json.dumps(narration, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
        # Only renames from here on, so the audio and the Narration disagree for as short a time as can be.
        for line in to_read:
            (stage / line["audio"]).replace(out / line["audio"])
    progress("narration_done", path=str(path))
    return {"path": str(path), "narration": narration}


def _plan_line(narration, line, chosen, voices_dir, earlier_seed=None):
    """How a Line will be read: its Model, Voice (and the Cloned Voice it names, if any), style and seed, the Model
    that times its words, and the Model that transcribes it back.

    A Line read again never reuses `earlier_seed`, the seed it was read with before, so it always sounds different.
    """
    model, voice, cloned = resolve_voice(line_setting(narration, line, "voice"), narration["language"], chosen, voices_dir)
    style, warnings = line_setting(narration, line, "style"), []
    if style is not None and not model.reads_style:
        style = None
        warnings.append({"code": "style_ignored", "message": f"Model {model.id} cannot follow style; read the Line without it."})
    aligner = aligner_for(model, narration["language"])
    if aligner is None:
        warnings.append({"code": "not_aligned", "message": f"No Model can align {narration['language']!r}, "
                                                           "so the Line has no words."})
    elif not is_installed(aligner):
        warnings.append(_not_installed("aligner_not_installed", aligner, "words"))
        aligner = None
    # The self-check: a Line is transcribed back, unless no Model can transcribe its language.
    transcriber = transcriber_for(model, narration["language"])
    if transcriber is None:
        warnings.append({"code": "not_checked", "message": f"No Model can transcribe {narration['language']!r}, "
                                                           "so the Line has no transcript or error_rate."})
    elif not is_installed(transcriber):
        warnings.append(_not_installed("checker_not_installed", transcriber, "transcript or error_rate"))
        transcriber = None
    seed = line_setting(narration, line, "seed")
    while seed is None or seed == earlier_seed:
        seed = secrets.randbelow(MAX_SEED + 1)
    return {"model": model, "voice": voice, "cloned": cloned, "style": style, "warnings": warnings, "aligner": aligner,
            "transcriber": transcriber, "seed": seed}


def _not_installed(code, model, fields):
    """The warning on a Line read without a Model that only completes it, because that Model is not installed."""
    return {"code": code, "message": f"Model {model.id} is not installed, so the Line has no {fields}. Tell the user "
                                     f"its size and license from details; once they agree, run `voxx install {model.id}` "
                                     "and read the Line again with --line.",
            "details": {**model.install_summary(), "command": f"voxx install {model.id}"}}


def _read_line(worker, narration, line, plan, stage):
    """Every step that turns one Line into its audio file in `stage` and completes its fields, for a whole run and
    --line alike."""
    audio = f"{line['id']}.wav"
    model = plan["model"]
    if cloned := plan["cloned"]:
        voice = {"capability": "clone", "reference": {"audio": str(cloned.reference), "text": cloned.reference_text}}
    else:
        voice = {"capability": "preset_voice", "voice": plan["voice"], "style": plan["style"]}
    result = worker.call("synthesize_line", model=model.id, engine=model.engine, model_path=str(model_dir(model)),
                         text=line["text"], language=narration["language"], seed=plan["seed"], path=str(stage / audio),
                         **voice)
    line.update(audio=audio, model=model.id, voice=plan["voice"], seed=plan["seed"],
                sample_rate=result["sample_rate"], warnings=plan["warnings"] + result["warnings"])
    # A Line given back from an earlier run may still carry the words and self-check of its earlier audio.
    for field in ("words", "transcript", "error_rate"):
        line.pop(field, None)
    if aligner := plan["aligner"]:
        aligned = worker.call("align_line", model=aligner.id, engine=aligner.engine, model_path=str(model_dir(aligner)),
                              capability="align", text=line["text"], language=narration["language"], path=str(stage / audio))
        words = word_timings(line["text"], aligned["words"], stage / audio) if "words" in aligned else None
        if words is not None:
            line["words"] = words
        else:
            why = (f"failed: {aligned['failure']}" if "failure" in aligned
                   else "returned words that do not spell out the Line's text")
            line["warnings"].append({"code": "not_aligned", "message": f"Model {aligner.id} {why}, so the Line has no words."})
    if transcriber := plan["transcriber"]:
        transcript = worker.call("transcribe_line", model=transcriber.id, engine=transcriber.engine,
                                 model_path=str(model_dir(transcriber)), capability="transcribe",
                                 language=narration["language"], path=str(stage / audio))["transcript"]
        line.update(transcript=transcript, error_rate=error_rate(line["text"], transcript))


def _lines_to_read_again(narration, line_ids):
    by_id = {line["id"]: line for line in narration["lines"]}
    unknown = [i for i in line_ids if i not in by_id]
    if unknown:
        raise VoxxError("unknown_line", f"The Narration has no Line with id {', '.join(map(repr, unknown))}.",
                        "Pass the id of a Line in the Narration to --line.", {"unknown": unknown, "known_lines": list(by_id)}, USAGE)
    return [by_id[i] for i in line_ids]


def _earlier_output(out):
    path = out / OUTPUT_NAME
    try:
        earlier = json.loads(path.read_text(encoding="utf-8"))
        check_narration(earlier)
    except FileNotFoundError:
        raise VoxxError("no_earlier_output", f"--line reads Lines again, but {out} has no {OUTPUT_NAME} from an "
                                              "earlier run.", READ_ALL_HINT, {"path": str(path)}, USAGE)
    except (OSError, UnicodeDecodeError, json.JSONDecodeError, VoxxError) as e:
        raise VoxxError("invalid_earlier_output", f"Cannot use {path} from the earlier run: {e}", READ_ALL_HINT,
                        {"path": str(path)}, USAGE)
    return earlier


def _lines_to_keep(narration, earlier, to_read, chosen, voices_dir):
    """The earlier run's Line for every Line not read again, each warned if the Narration now asks it to sound otherwise."""
    earlier_lines = {line["id"]: line for line in earlier["lines"]}
    reading = {line["id"] for line in to_read}
    unread = [line["id"] for line in narration["lines"] if line["id"] not in reading and line["id"] not in earlier_lines]
    if unread:
        raise VoxxError("line_not_read", f"Line {', '.join(map(repr, unread))} has no audio from the earlier run.",
                        "Pass every new Line to --line as well, or read the whole Narration again.", {"unread": unread}, USAGE)
    kept = {}
    for line in narration["lines"]:
        if line["id"] in reading:
            continue
        old = earlier_lines[line["id"]]
        # A warning from an earlier --line run is judged again against this Narration.
        warnings = [w for w in old.get("warnings", []) if w.get("code") != "stale_audio"]
        changes = []
        if line["text"] != old["text"]:
            changes.append(f"its text is now {line['text']!r}")
        if narration["language"] != earlier["language"]:
            changes.append(f"the Narration's language is now {narration['language']!r}")
        # The Voice this run would read the Line with, as _plan_line resolves it.
        _, voice, _ = resolve_voice(line_setting(narration, line, "voice"), narration["language"], chosen, voices_dir)
        if voice != old.get("voice"):
            changes.append(f"its voice is now {voice!r}, not {old.get('voice')!r}")
        style, old_style = line_setting(narration, line, "style"), line_setting(earlier, old, "style")
        if style != old_style:
            changes.append(f"its style is now {_or_none(style)}, not {_or_none(old_style)}")
        if changes:
            warnings.append({"code": "stale_audio", "message": f"The audio reads {old['text']!r} in {earlier['language']!r}, "
                                                               f"but {' and '.join(changes)}. Pass --line {line['id']} to read it again."})
        kept[line["id"]] = {**old, "warnings": warnings}
    return kept


def _or_none(value):
    return "none" if value is None else repr(value)
