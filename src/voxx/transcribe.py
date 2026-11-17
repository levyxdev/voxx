"""`voxx transcribe`: the Transcript of a Media File, Passage by Passage, with Word Timings on request (ADR 0011)."""

import tempfile
import unicodedata
from collections import Counter
from pathlib import Path

from voxx.models import (aligner_for, check_language, default_transcribe_model, find_model, is_installed, model_dir,
                         require_installed, unsupported_capability)
from voxx.narration import check_language_arg
from voxx.output import USAGE, VoxxError, progress
from voxx.words import word_timings
from voxx.worker.client import WorkerProcess


def transcribe(media, language=None, model_id=None, words=False):
    """What is said in the audio or video file at `media`: in `language`, else in whatever language each Passage is
    heard in; with `words`, each word's start and end, counted from the start of the file."""
    source = Path(media).absolute()
    if not source.is_file():
        raise VoxxError("media_not_found", f"No file at {source}.", "Pass the path of an audio or video file.",
                        {"media": str(source)}, USAGE)
    if language is not None:
        check_language_arg(language, "Leave --language out to transcribe whatever language is heard.")
    model = find_model(model_id) if model_id is not None else default_transcribe_model()
    if "transcribe" not in model.capabilities:
        raise unsupported_capability(model, "transcribe", "transcribe")
    if language is not None:
        check_language(model, language)
    require_installed([model])

    warnings, passages = [], []
    with tempfile.TemporaryDirectory(prefix="voxx-transcribe-") as directory, WorkerProcess("transcribe") as worker:
        split = worker.call("split_media", source=str(source), directory=directory)
        total = len(split["passages"])
        progress("transcription_started", duration=split["duration"], passages=total)
        for index, piece in enumerate(split["passages"], start=1):
            heard = worker.call("transcribe_line", model=model.id, engine=model.engine, model_path=str(model_dir(model)),
                                capability="transcribe", language=language, path=piece["path"])
            text = heard["transcript"].strip()
            passage = {"start": piece["start"], "end": piece["end"], "language": heard["language"] if text else None,
                       "text": text, "warnings": []}
            if words and text:
                _time_words(worker, model, passage, Path(piece["path"]), warnings)
            passages.append(passage)
            progress("passage_done", index=index, total=total)
    return {"source": str(source), "model": model.id, "language": language or _most_heard(passages),
            "duration": split["duration"], "text": _joined(p["text"] for p in passages), "passages": passages,
            "warnings": warnings}


def _time_words(worker, model, passage, path, warnings):
    """Gives the Passage its words, timed from the start of the Media File, or a warning on why it has none."""
    language = passage["language"]
    aligner = aligner_for(model, language) if language is not None else None
    if aligner is None:
        heard = repr(language) if language is not None else "the language heard, which has no BCP 47 tag in voxx"
        passage["warnings"].append({"code": "not_aligned", "message": f"No Model can align {heard}, so the Passage "
                                                                      "has no words."})
        return
    if not is_installed(aligner):
        if not any(w["details"]["model"] == aligner.id for w in warnings if w["code"] == "aligner_not_installed"):
            warnings.append({"code": "aligner_not_installed",
                             "message": f"Model {aligner.id} is not installed, so the Passages it would align have no "
                                        "words. Tell the user its size and license from details; once they agree, run "
                                        f"`voxx install {aligner.id}` and transcribe again with --words.",
                             "details": {**aligner.install_summary(), "command": f"voxx install {aligner.id}"}})
        return
    aligned = worker.call("align_line", model=aligner.id, engine=aligner.engine, model_path=str(model_dir(aligner)),
                          capability="align", text=passage["text"], language=language, path=str(path))
    timed = word_timings(passage["text"], aligned["words"], path) if "words" in aligned else None
    if timed is None:
        why = (f"failed: {aligned['failure']}" if "failure" in aligned
               else "returned words that do not spell out the Passage's text")
        passage["warnings"].append({"code": "not_aligned", "message": f"Model {aligner.id} {why}, so the Passage has "
                                                                      "no words."})
        return
    start, end = passage["start"], passage["end"]
    passage["words"] = [{"text": w["text"], "start": min(round(w["start"] + start, 3), end),
                         "end": min(round(w["end"] + start, 3), end)} for w in timed]


def _most_heard(passages):
    """The language heard for the longest time, or None if nothing was heard."""
    seconds = Counter()
    for passage in passages:
        if passage["language"] is not None:
            seconds[passage["language"]] += passage["end"] - passage["start"]
    return seconds.most_common(1)[0][0] if seconds else None


def _joined(texts):
    """The Passages' texts with a space between, but none between two full-width characters, as in Chinese."""
    joined = ""
    for text in texts:
        if text and joined and not (_wide(joined[-1]) and _wide(text[0])):
            joined += " "
        joined += text
    return joined


def _wide(character):
    return unicodedata.east_asian_width(character) in "WF"
