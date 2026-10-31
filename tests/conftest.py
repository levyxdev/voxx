"""Tests run `voxx` the way an agent does: as a process, judged by stdout, exit code, stderr and files."""

import json
import os
import shutil
import subprocess
import sys
from dataclasses import dataclass
from pathlib import Path

import pytest
from fake_hub import FakeHub

from voxx.models import FAKE_MODEL, FAKE_MODELS

VOXX = Path(sys.executable).with_name("voxx")
FAKE_CONFIG = b'{"model_type": "fake"}'
# Each fake Model's files add up to the size its registry entry declares.
FAKE_FILES = {"config.json": FAKE_CONFIG,
              "model.safetensors": bytes(i % 251 for i in range(FAKE_MODEL.size_bytes - len(FAKE_CONFIG)))}


def assert_error(run, exit_code, code):
    assert run.exit_code == exit_code
    assert run.result["ok"] is False
    error = run.result["error"]
    assert error["code"] == code
    assert error["message"] and error["hint"]
    return error


def snapshot(out):
    """Every file in `out`, hidden ones too, by name."""
    return {p.name: p.read_bytes() for p in out.iterdir()}


@dataclass
class Run:
    exit_code: int
    result: dict
    events: list


@dataclass
class Voxx:
    """Runs `voxx` with its own VOXX_HOME, the fake Engine, and the fake hub."""
    home: Path
    hub: FakeHub

    def __call__(self, *args, env=None):
        process = subprocess.run(
            [str(VOXX), *map(str, args)], capture_output=True, encoding="utf-8", timeout=60,
            env={**os.environ, "VOXX_HOME": str(self.home), "VOXX_TEST_FAKE_ENGINE": "1", "HF_ENDPOINT": self.hub.url,
                 **(env or {})})
        # stdout is exactly one JSON object; stderr is only NDJSON events.
        result = json.loads(process.stdout)
        assert process.stdout.count("\n") == 1, process.stdout
        events = [json.loads(line) for line in process.stderr.splitlines()]
        assert all(isinstance(e, dict) and "event" in e for e in events), process.stderr
        return Run(process.returncode, result, events)


def fake_hub():
    return FakeHub({(m.repo, m.revision): FAKE_FILES for m in FAKE_MODELS}).start()


@pytest.fixture
def hub():
    hub = fake_hub()
    yield hub
    hub.stop()


@pytest.fixture
def voxx(tmp_path, hub):
    return Voxx(tmp_path / "voxx-home", hub)


@pytest.fixture(scope="session")
def installed_home(tmp_path_factory):
    """A VOXX_HOME with every fake Model installed, made once and copied into each test that needs it."""
    hub = fake_hub()
    home = tmp_path_factory.mktemp("installed") / "voxx-home"
    for model in FAKE_MODELS:
        assert Voxx(home, hub)("install", model.id).exit_code == 0
    hub.stop()
    return home


@pytest.fixture
def installed(voxx, installed_home):
    """voxx with the fake Models installed, as `voxx narrate` needs."""
    shutil.copytree(installed_home, voxx.home)
    return voxx


@pytest.fixture
def write_narration(tmp_path):
    def write(narration, name="narration.json"):
        path = tmp_path / name
        path.write_text(json.dumps(narration, ensure_ascii=False), encoding="utf-8")
        return path

    return write
