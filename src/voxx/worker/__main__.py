"""`python -m voxx.worker`: JSON-RPC 2.0 requests on stdin, responses on stdout, NDJSON progress on stderr."""

import json
import os
import sys
import traceback
from pathlib import Path

from voxx.audio import write_wav
from voxx.engines import load_engine
from voxx.output import VoxxError, dumps, progress


class Worker:
    def __init__(self):
        self.engines = {}

    def synthesize_line(self, *, model, engine, text, voice, style, language, seed, path):
        samples, sample_rate = self._engine(model, engine).synthesize(
            text, model=model, voice=voice, style=style, language=language, seed=seed)
        write_wav(Path(path), samples, sample_rate)
        return {"sample_rate": sample_rate}

    def _engine(self, model, engine):
        if model not in self.engines:
            progress("model_loading", model=model)
            loaded = load_engine(engine)
            loaded.load(model)
            self.engines[model] = loaded
            progress("model_loaded", model=model)
        return self.engines[model]


def main():
    # Model libraries print to stdout; keep the protocol on a private copy of it and send their prints to stderr.
    rpc = os.fdopen(os.dup(1), "w", encoding="utf-8")
    os.dup2(2, 1)
    worker = Worker()
    methods = {"synthesize_line": worker.synthesize_line, "shutdown": lambda: None}
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
        rpc.write(dumps(response) + "\n")
        rpc.flush()
        if request["method"] == "shutdown":
            return


if __name__ == "__main__":
    main()
