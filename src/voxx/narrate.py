"""`voxx narrate`: read every Line of a Narration in one worker, then write the completed Narration."""

import json
import secrets
from pathlib import Path

from voxx.models import resolve_voice
from voxx.narration import load_narration
from voxx.output import USAGE, VoxxError, progress
from voxx.worker.client import WorkerProcess

OUTPUT_NAME = "narration.json"


def narrate(narration_path, out_dir):
    narration = load_narration(narration_path)
    out = Path(out_dir).resolve()
    # Resolve every Line before starting the worker, so a bad Voice fails fast.
    plans = []
    for line in narration["lines"]:
        model, voice = resolve_voice(line.get("voice", narration.get("voice")), narration["language"])
        plans.append({"model": model, "voice": voice, "style": line.get("style", narration.get("style")),
                      "seed": secrets.randbelow(2**31)})
    try:
        out.mkdir(parents=True, exist_ok=True)
    except (FileExistsError, NotADirectoryError):
        raise VoxxError("invalid_out", f"{out} exists and is not a directory.", "Pass a directory for --out.", {"out": str(out)}, USAGE)

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
    partial = path.with_name(path.name + ".partial")
    partial.write_text(json.dumps(narration, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    partial.replace(path)
    progress("narration_done", path=str(path))
    return {"path": str(path), "narration": narration}
