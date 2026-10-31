"""The CLI's side of the worker: starts it, calls it, and turns its death into a structured error."""

import collections
import contextlib
import json
import os
import signal
import subprocess
import sys
import threading
from typing import IO, cast

from voxx.output import BUG_HINT, INTERNAL, VoxxError, emit_event

# Model libraries reach for Hugging Face on their own; only `voxx install` may download (ADR 0003).
OFFLINE = {"HF_HUB_OFFLINE": "1", "TRANSFORMERS_OFFLINE": "1"}
CRASH_HINT = "The worker process died, often because memory ran out. Close other apps or use a smaller Model, then retry."


class WorkerProcess:
    def __enter__(self):
        self.process = subprocess.Popen(
            [sys.executable, "-m", "voxx.worker"], stdin=subprocess.PIPE, stdout=subprocess.PIPE,
            stderr=subprocess.PIPE, encoding="utf-8", bufsize=1, env={**os.environ, **OFFLINE})
        # Popen types its pipes as optional; all three are pipes here.
        self.stdin, self.stdout, self.stderr = cast(tuple[IO[str], IO[str], IO[str]],
                                                    (self.process.stdin, self.process.stdout, self.process.stderr))
        self.stderr_tail = collections.deque(maxlen=40)
        self.stderr_thread = threading.Thread(target=self._forward_stderr, daemon=True)
        self.stderr_thread.start()
        self.next_id = 0
        return self

    def call(self, method, **params):
        self.next_id += 1
        try:
            self.stdin.write(json.dumps({"jsonrpc": "2.0", "id": self.next_id, "method": method, "params": params}) + "\n")
            self.stdin.flush()
        except BrokenPipeError:
            raise self._crashed()
        line = self.stdout.readline()
        if not line:
            raise self._crashed()
        response = json.loads(line)
        if "error" not in response:
            return response["result"]
        error = response["error"]
        data = error.get("data", {})
        if "voxx" in data:
            voxx_error = data["voxx"]
            raise VoxxError(voxx_error["code"], voxx_error["message"], voxx_error["hint"], voxx_error["details"], data["exit_code"])
        raise VoxxError("worker_error", error["message"], BUG_HINT, {"traceback": data.get("traceback", "")}, INTERNAL)

    def __exit__(self, exc_type, exc, tb):
        try:
            if exc_type is None:
                self.call("shutdown")
        finally:
            with contextlib.suppress(BrokenPipeError):
                self.stdin.close()
            self._reap()
            self.stdout.close()

    def _reap(self):
        """Waits for the worker to exit, killing it if it will not, and drains its stderr."""
        try:
            code = self.process.wait(timeout=10)
        except subprocess.TimeoutExpired:
            self.process.kill()
            code = self.process.wait()
        self.stderr_thread.join()
        return code

    def _crashed(self):
        code = self._reap()
        details = {"worker_pid": self.process.pid, "exit_code": code, "stderr_tail": list(self.stderr_tail)}
        if code < 0:
            details["signal"] = signal.Signals(-code).name
        return VoxxError("worker_crashed", "The synthesis worker exited unexpectedly.", CRASH_HINT, details, INTERNAL)

    def _forward_stderr(self):
        # Everything voxx writes to stderr is NDJSON, so wrap anything else the worker prints.
        for line in self.stderr:
            line = line.rstrip("\n")
            if not line:
                continue
            self.stderr_tail.append(line)
            try:
                event = json.loads(line)
            except json.JSONDecodeError:
                event = None
            emit_event(event if isinstance(event, dict) and "event" in event else {"event": "log", "source": "worker", "message": line})
        self.stderr.close()
