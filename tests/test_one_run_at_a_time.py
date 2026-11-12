"""Commands that start a worker take turns, so two of them never hold Models in memory at once (ADR 0009)."""

import json
import time

TWO_LINES = {
    "language": "zh",
    "voice": "fake-alice",
    "lines": [
        {"id": "intro", "text": "这是一个新的发送流程。"},
        {"id": "send", "text": "点一下发送就完成了。"},
    ],
}


def wait_for(found, timeout=30):
    deadline = time.monotonic() + timeout
    while not (result := found()):
        assert time.monotonic() < deadline, "timed out"
        time.sleep(0.05)
    return result


def events_until(process, name):
    """Reads `process`'s stderr up to and including the first event called `name`."""
    events = []
    for line in process.stderr:
        events.append(json.loads(line))
        if events[-1]["event"] == name:
            return events
    raise AssertionError(f"{name} never came: {events}")


def test_a_second_run_waits_for_the_first_and_says_which_command_it_waits_for(installed, write_narration, tmp_path):
    paused = tmp_path / "paused"
    paused.mkdir()
    pause = {"VOXX_TEST_FAKE_PAUSE": str(paused)}
    narration = write_narration(TWO_LINES)
    first = installed.start("narrate", narration, "--out", tmp_path / "first", env=pause)
    wait_for(lambda: list(paused.glob("loaded-*")))

    second = installed.start("voice", "design", "--describe", "低沉的男声", "--text", "你好。", "--language", "zh",
                             "--model", "fake-clone", "--out", tmp_path / "design", env=pause)
    waiting = events_until(second, "waiting")[-1]

    assert waiting["command"] == "narrate"
    assert waiting["pid"] == first.pid
    # The second run has not loaded a Model while the first holds its own.
    assert [p.name for p in paused.glob("loaded-*")] == [f"loaded-{first.pid}"]

    (paused / "go").touch()
    assert installed.finish(first).exit_code == 0
    assert installed.finish(second).exit_code == 0
    assert sorted(p.name for p in paused.glob("loaded-*")) == sorted([f"loaded-{first.pid}", f"loaded-{second.pid}"])


def test_a_run_that_finds_no_other_does_not_wait(installed, write_narration, tmp_path):
    run = installed("narrate", write_narration(TWO_LINES), "--out", tmp_path / "out")

    assert run.exit_code == 0
    assert "waiting" not in [e["event"] for e in run.events]
