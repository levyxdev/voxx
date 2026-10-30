"""`voxx narrate`: read every Line of a Narration in one worker, then write the completed Narration."""

import errno
import json
import os
import secrets
from pathlib import Path

from voxx.files import replacing
from voxx.models import resolve_voice
from voxx.narration import line_setting, load_narration
from voxx.output import USAGE, VoxxError, progress
from voxx.worker.client import WorkerProcess

OUTPUT_NAME = "narration.json"


def narrate(narration_path, out_dir):
    narration = load_narration(narration_path)
    out = Path(out_dir).resolve()
    # Resolve every Line before starting the worker, so a bad Voice fails fast.
    plans = []
    for line in narration["lines"]:
        model, voice = resolve_voice(line_setting(narration, line, "voice"), narration["language"])
        plans.append({"model": model, "voice": voice, "style": line_setting(narration, line, "style"),
                      "seed": secrets.randbelow(2**31)})
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
            result = worker.call("synthesize_line", model=plan["model"].id, engine=plan["model"].engine, text=line["text"],
                                 voice=plan["voice"], style=plan["style"], language=narration["language"],
                                 seed=plan["seed"], path=str(out / audio))
            line.update(audio=audio, model=plan["model"].id, voice=plan["voice"], seed=plan["seed"],
                        sample_rate=result["sample_rate"])
            progress("line_done", id=line["id"], index=index, total=len(plans))

    path = out / OUTPUT_NAME
    with replacing(path) as partial:
        partial.write_text(json.dumps(narration, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    progress("narration_done", path=str(path))
    return {"path": str(path), "narration": narration}
