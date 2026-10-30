"""Tests run `voxx` the way an agent does: as a process, judged by stdout, exit code, stderr and files."""

import json
import os
import subprocess
import sys
from dataclasses import dataclass
from pathlib import Path

import pytest

VOXX = Path(sys.executable).with_name("voxx")


@dataclass
class Run:
    exit_code: int
    result: dict
    events: list


@pytest.fixture
def voxx(tmp_path):
    home = tmp_path / "voxx-home"

    def run(*args, env=None):
        process = subprocess.run(
            [str(VOXX), *map(str, args)], capture_output=True, encoding="utf-8", timeout=60,
            env={**os.environ, "VOXX_HOME": str(home), "VOXX_TEST_FAKE_ENGINE": "1", **(env or {})})
        # stdout is exactly one JSON object; stderr is only NDJSON events.
        result = json.loads(process.stdout)
        assert process.stdout.count("\n") == 1, process.stdout
        events = [json.loads(line) for line in process.stderr.splitlines()]
        assert all(isinstance(e, dict) and "event" in e for e in events), process.stderr
        return Run(process.returncode, result, events)

    return run


@pytest.fixture
def write_narration(tmp_path):
    def write(narration, name="narration.json"):
        path = tmp_path / name
        path.write_text(json.dumps(narration, ensure_ascii=False), encoding="utf-8")
        return path

    return write
