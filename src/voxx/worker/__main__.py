"""`python -m voxx.worker`: JSON-RPC 2.0 requests on stdin, responses on stdout, NDJSON progress on stderr."""

import io
import json
import os
import sys
import traceback
from pathlib import Path
from typing import cast

from voxx.audio import finish, prepare_reference, write_wav
from voxx.engines import load_engine
from voxx.output import VoxxError, dumps, progress


class Worker:
    def __init__(self):
        self.engines = {}

    def synthesize_line(self, *, model, engine, model_path, capability, text, language, seed, path, **voice):
        """Reads a Line in a Preset Voice, given as voice and style, or with capability "clone" in a Cloned Voice,
        given as reference: the path of its Reference Recording (audio) and that recording's words (text)."""
        reader = self._engine(model, engine, model_path, capability)
        if capability == "clone":
            samples, sample_rate = reader.clone(text, model=model, reference=Path(voice["reference"]["audio"]),
                                                reference_text=voice["reference"]["text"], language=language, seed=seed)
        else:
            samples, sample_rate = reader.synthesize(text, model=model, voice=voice["voice"], style=voice["style"],
                                                     language=language, seed=seed)
        samples, warnings = finish(samples, sample_rate)
        write_wav(Path(path), samples, sample_rate)
        return {"sample_rate": sample_rate, "warnings": warnings}

    def prepare_reference(self, *, source, path):
        return {"warnings": prepare_reference(Path(source), Path(path))}

    def transcribe_line(self, *, model, engine, model_path, capability, language, path):
        return {"transcript": self._engine(model, engine, model_path, capability).transcribe(
            Path(path), model=model, language=language)}

    def align_line(self, *, model, engine, model_path, capability, text, language, path):
        """The Line's words as [word, start, end], or why the Model could not align them: that costs the Line only its words."""
        aligner = self._engine(model, engine, model_path, capability)
        try:
            return {"words": aligner.align(Path(path), model=model, text=text, language=language)}
        except Exception as e:
            return {"failure": f"{type(e).__name__}: {e}"}

    def _engine(self, model, engine, model_path, capability):
        if model not in self.engines:
            progress("model_loading", model=model)
            loaded = load_engine(engine)
            loaded.load(Path(model_path), capability)
            self.engines[model] = loaded
            progress("model_loaded", model=model)
        return self.engines[model]


def main():
    # Model libraries print to stdout; keep the protocol on a private copy of it and send their prints to stderr.
    rpc_out = os.fdopen(os.dup(1), "w", encoding="utf-8")
    os.dup2(2, 1)
    cast(io.TextIOWrapper, sys.stderr).reconfigure(encoding="utf-8")
    worker = Worker()
    methods = {"synthesize_line": worker.synthesize_line, "transcribe_line": worker.transcribe_line,
               "align_line": worker.align_line, "prepare_reference": worker.prepare_reference, "shutdown": lambda: None}
    for line in sys.stdin:
        request = json.loads(line)
        response = {"jsonrpc": "2.0", "id": request.get("id")}
        if request["method"] not in methods:
            response["error"] = {"code": -32601, "message": f"Unknown method {request['method']}"}
        else:
            try:
                response["result"] = methods[request["method"]](**request.get("params", {}))
            except VoxxError as e:
                response["error"] = {"code": -32000, "message": e.message, "data": {"voxx": e.to_json(), "exit_code": e.exit_code}}
            except Exception as e:
                response["error"] = {"code": -32603, "message": f"{type(e).__name__}: {e}", "data": {"traceback": traceback.format_exc()}}
        rpc_out.write(dumps(response) + "\n")
        rpc_out.flush()
        if request["method"] == "shutdown":
            return


if __name__ == "__main__":
    main()
