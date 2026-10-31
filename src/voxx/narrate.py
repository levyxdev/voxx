"""`voxx narrate`: read every Line of a Narration in one worker, then write the completed Narration."""

import errno
import json
import os
import secrets
from pathlib import Path

from voxx.files import replacing
from voxx.models import find_model, model_dir, require_installed, resolve_voice, transcriber_for
from voxx.narration import MAX_SEED, line_setting, load_narration
from voxx.output import USAGE, VoxxError, progress
from voxx.self_check import error_rate
from voxx.worker.client import WorkerProcess

OUTPUT_NAME = "narration.json"


def narrate(narration_path, out_dir, model_id=None):
    narration = load_narration(narration_path)
    out = Path(out_dir).resolve()
    chosen = find_model(model_id) if model_id is not None else None
    # Resolve every Line before starting the worker, so a bad Voice fails fast.
    plans = []
    for line in narration["lines"]:
        model, voice = resolve_voice(line_setting(narration, line, "voice"), narration["language"], chosen)
        style, warnings = line_setting(narration, line, "style"), []
        if style is not None and not model.reads_style:
            style = None
            warnings.append({"code": "style_ignored", "message": f"Model {model.id} cannot follow style; read the Line without it."})
        # The self-check: a Line is transcribed back, unless no Model can transcribe its language.
        transcriber = transcriber_for(model, narration["language"])
        if transcriber is None:
            warnings.append({"code": "not_checked", "message": f"No Model can transcribe {narration['language']!r}, "
                                                               "so the Line has no transcript or error_rate."})
        seed = line_setting(narration, line, "seed")
        plans.append({"model": model, "voice": voice, "style": style, "warnings": warnings, "transcriber": transcriber,
                      "seed": secrets.randbelow(MAX_SEED + 1) if seed is None else seed})
    require_installed(dict.fromkeys(m for plan in plans for m in (plan["model"], plan["transcriber"]) if m))
    try:
        out.mkdir(parents=True, exist_ok=True)
        if not os.access(out, os.W_OK):
            raise PermissionError(errno.EACCES, "Permission denied")
    except OSError as e:
        raise VoxxError("invalid_out", f"Cannot use {out} as the output directory: {e.strerror}.",
                        "Pass a writable directory for --out.", {"out": str(out)}, USAGE)

    progress("narration_started", lines=len(plans))
    with WorkerProcess() as worker:
        for index, (line, plan) in enumerate(zip(narration["lines"], plans), start=1):
            progress("line_started", id=line["id"], index=index, total=len(plans))
            audio = f"{line['id']}.wav"
            model = plan["model"]
            result = worker.call("synthesize_line", model=model.id, engine=model.engine, model_path=str(model_dir(model)),
                                 capability="preset_voice", text=line["text"], voice=plan["voice"], style=plan["style"],
                                 language=narration["language"], seed=plan["seed"], path=str(out / audio))
            line.update(audio=audio, model=model.id, voice=plan["voice"], seed=plan["seed"],
                        sample_rate=result["sample_rate"], warnings=plan["warnings"] + result["warnings"])
            if transcriber := plan["transcriber"]:
                transcript = worker.call("transcribe_line", model=transcriber.id, engine=transcriber.engine,
                                         model_path=str(model_dir(transcriber)), capability="transcribe",
                                         language=narration["language"], path=str(out / audio))["transcript"]
                line.update(transcript=transcript, error_rate=error_rate(line["text"], transcript))
            progress("line_done", id=line["id"], index=index, total=len(plans))

    path = out / OUTPUT_NAME
    with replacing(path) as partial:
        partial.write_text(json.dumps(narration, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    progress("narration_done", path=str(path))
    return {"path": str(path), "narration": narration}
