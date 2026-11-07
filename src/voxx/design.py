"""`voxx voice design`: read one text in new voices that fit text descriptions, as Design Takes for the user to choose
from (ADR 0007). Stores no Voice.

The output directory gets its Design Takes first and design.json last, so design.json exists only once every take is
there; a run that fails leaves no design.json, and a second run into the same directory is refused."""

import json
import re
import secrets
from pathlib import Path

from voxx.files import replacing, staging, writable_out
from voxx.models import (check_language, default_design_model, find_model, is_installed, model_dir, require_installed,
                         transcriber_for, unsupported_capability)
from voxx.narration import LANGUAGE_PATTERN, LANGUAGE_RULE, MAX_SEED, canonical_case
from voxx.output import USAGE, VoxxError, progress
from voxx.self_check import error_rate
from voxx.worker.client import WorkerProcess

OUTPUT_NAME = "design.json"
ARGS_HINT = "Run `voxx schema voice design` to see its arguments."


def design(descriptions, text, language, out_dir, takes=1, model_id=None):
    """Reads `text` `takes` times for each description, each time with a new seed, into <out_dir>/take-<n>.wav, and
    writes <out_dir>/design.json. Each Design Take is transcribed back to check it, as a Line is."""
    if not descriptions or not all(d.strip() for d in descriptions):
        _invalid("Each --describe must be a non-empty description of the voice.")
    if not text.strip():
        _invalid("--text must be the words each Design Take reads.")
    if takes < 1:
        _invalid("--takes must be 1 or more.")
    if not re.fullmatch(LANGUAGE_PATTERN, language):
        canonical = canonical_case(language)
        raise VoxxError("invalid_language", f"--language {language!r}: {LANGUAGE_RULE}"
                        + (f" Write it as {canonical!r}." if canonical else ""), ARGS_HINT, {"language": language}, USAGE)
    out = Path(out_dir).resolve()
    path = out / OUTPUT_NAME
    if path.exists():
        raise VoxxError("design_exists", f"{out} already holds the Design Takes of an earlier run.",
                        "Pass a new directory to --out, so the takes the user has heard are kept.", {"path": str(path)},
                        USAGE)
    model = find_model(model_id) if model_id is not None else default_design_model()
    if "design" not in model.capabilities:
        raise unsupported_capability(model, "design", "design a voice")
    check_language(model, language)
    require_installed([model])
    # The self-check is what shows a take that read its description out loud, but without it the takes still play
    # (ADR 0006).
    transcriber, warnings = transcriber_for(model, language), []
    if transcriber is None:
        warnings.append({"code": "not_checked", "message": f"No Model can transcribe {language!r}, so the Design Take "
                                                           "has no transcript or error_rate."})
    elif not is_installed(transcriber):
        warnings.append({"code": "checker_not_installed",
                         "message": f"Model {transcriber.id} is not installed, so the Design Take has no transcript or "
                                    "error_rate. Tell the user its size and license from details; once they agree, run "
                                    f"`voxx install {transcriber.id}` and design again into a new --out.",
                         "details": {**transcriber.install_summary(), "command": f"voxx install {transcriber.id}"}})
        transcriber = None
    writable_out(out)

    # Every take gets its own seed, so no two takes of one description come out the same.
    seeds = set()
    while len(seeds) < len(descriptions) * takes:
        seeds.add(secrets.randbelow(MAX_SEED + 1))
    planned = list(zip((d for d in descriptions for _ in range(takes)), seeds))
    result = {"model": model.id, "language": language, "text": text, "takes": []}
    progress("design_started", takes=len(planned))
    with staging(out) as stage:
        with WorkerProcess() as worker:
            for number, (description, seed) in enumerate(planned, start=1):
                progress("take_started", take=number, total=len(planned))
                audio = f"take-{number}.wav"
                read = worker.call("synthesize_line", model=model.id, engine=model.engine, model_path=str(model_dir(model)),
                                   capability="design", text=text, language=language, seed=seed,
                                   path=str(stage / audio), description=description)
                take = {"take": number, "description": description, "seed": seed, "audio": audio,
                        "sample_rate": read["sample_rate"], "warnings": warnings + read["warnings"]}
                if transcriber is not None:
                    transcript = worker.call("transcribe_line", model=transcriber.id, engine=transcriber.engine,
                                             model_path=str(model_dir(transcriber)), capability="transcribe",
                                             language=language, path=str(stage / audio))["transcript"]
                    take.update(transcript=transcript, error_rate=error_rate(text, transcript))
                result["takes"].append(take)
                progress("take_done", take=number, total=len(planned))
        for take in result["takes"]:
            (stage / take["audio"]).replace(out / take["audio"])
        with replacing(path) as partial:
            partial.write_text(json.dumps(result, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    progress("design_done", path=str(path))
    return {"path": str(path), "design": result}


def _invalid(message):
    raise VoxxError("invalid_arguments", message, ARGS_HINT, {}, USAGE)
