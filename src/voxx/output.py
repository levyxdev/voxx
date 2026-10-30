"""The CLI contract: one JSON object on stdout, NDJSON progress on stderr, and the exit codes."""

import json
import sys
import threading

OK, INTERNAL, USAGE, NOT_INSTALLED, UNSUPPORTED = 0, 1, 2, 3, 4

_stderr_lock = threading.Lock()


class VoxxError(Exception):
    def __init__(self, code, message, hint="", details=None, exit_code=INTERNAL):
        super().__init__(message)
        self.code, self.message, self.hint = code, message, hint
        self.details = details or {}
        self.exit_code = exit_code

    def to_json(self):
        return {"code": self.code, "message": self.message, "hint": self.hint, "details": self.details}


def dumps(value):
    return json.dumps(value, ensure_ascii=False)


def print_result(data):
    sys.stdout.write(dumps({"ok": True, "data": data}) + "\n")
    sys.stdout.flush()


def print_error(error):
    sys.stdout.write(dumps({"ok": False, "error": error.to_json()}) + "\n")
    sys.stdout.flush()


def progress(event, **fields):
    emit_event({"event": event, **fields})


def emit_event(event):
    with _stderr_lock:
        sys.stderr.write(dumps(event) + "\n")
        sys.stderr.flush()
