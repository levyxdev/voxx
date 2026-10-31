"""`--line`: read chosen Lines again, and leave every other Line of the earlier run as it was."""

import json

from conftest import assert_error

THREE_LINES = {
    "language": "zh",
    "voice": "fake-alice",
    "seed": 7,
    "lines": [
        {"id": "intro", "text": "这是一个新的发送流程。"},
        {"id": "send", "text": "点一下发送就完成了。", "style": "语气兴奋"},
        {"id": "outro", "text": "就这么简单。"},
    ],
}


def with_line(narration, line_id, **fields):
    return {**narration, "lines": [{**l, **fields} if l["id"] == line_id else l for l in narration["lines"]]}


def read_all(installed, write_narration, out, narration=THREE_LINES):
    run = installed("narrate", write_narration(narration), "--out", out)
    assert run.exit_code == 0, run.result
    return run


def snapshot(out):
    return {p.name: p.read_bytes() for p in out.iterdir()}


def lines_by_id(run):
    return {l["id"]: l for l in run.result["data"]["narration"]["lines"]}


def test_line_reads_only_that_line_again_and_keeps_every_other_line(installed, write_narration, tmp_path):
    out = tmp_path / "out"
    before = lines_by_id(read_all(installed, write_narration, out))
    files = snapshot(out)

    run = installed("narrate", write_narration(with_line(THREE_LINES, "send", seed=8)), "--out", out, "--line", "send")

    assert run.exit_code == 0, run.result
    after = lines_by_id(run)
    assert after["send"]["seed"] == 8 != before["send"]["seed"]
    assert (out / "send.wav").read_bytes() != files["send.wav"]
    for line_id in ("intro", "outro"):
        assert after[line_id] == before[line_id]
        assert (out / f"{line_id}.wav").read_bytes() == files[f"{line_id}.wav"]
    assert json.loads((out / "narration.json").read_text(encoding="utf-8")) == run.result["data"]["narration"]
    assert [e["id"] for e in run.events if e["event"] == "line_done"] == ["send"]


def test_a_line_read_again_without_a_seed_gets_a_new_one(installed, write_narration, tmp_path):
    out = tmp_path / "out"
    unseeded = {k: v for k, v in THREE_LINES.items() if k != "seed"}
    before = lines_by_id(read_all(installed, write_narration, out, unseeded))

    run = installed("narrate", write_narration(unseeded), "--out", out, "--line", "intro")

    assert lines_by_id(run)["intro"]["seed"] != before["intro"]["seed"]


def test_line_can_be_given_more_than_once(installed, write_narration, tmp_path):
    out = tmp_path / "out"
    read_all(installed, write_narration, out)
    files = snapshot(out)
    narration = with_line(with_line(THREE_LINES, "intro", seed=8), "outro", seed=9)

    run = installed("narrate", write_narration(narration), "--out", out, "--line", "outro", "--line", "intro")

    assert run.exit_code == 0, run.result
    assert [l["seed"] for l in run.result["data"]["narration"]["lines"]] == [8, 7, 9]
    assert (out / "send.wav").read_bytes() == files["send.wav"]
    assert [e["id"] for e in run.events if e["event"] == "line_done"] == ["outro", "intro"]


def test_an_unknown_line_id_is_an_argument_error(installed, write_narration, tmp_path):
    out = tmp_path / "out"
    read_all(installed, write_narration, out)
    files = snapshot(out)

    error = assert_error(installed("narrate", write_narration(THREE_LINES), "--out", out, "--line", "nope"), 2, "unknown_line")

    assert error["details"]["unknown"] == ["nope"]
    assert error["details"]["known_lines"] == ["intro", "send", "outro"]
    assert snapshot(out) == files


def test_line_without_an_earlier_run_is_an_argument_error(installed, write_narration, tmp_path):
    out = tmp_path / "out"
    error = assert_error(installed("narrate", write_narration(THREE_LINES), "--out", out, "--line", "send"),
                         2, "no_previous_output")

    assert "without --line" in error["hint"]
    assert not out.exists()


def test_an_unreadable_earlier_run_is_an_argument_error(installed, write_narration, tmp_path):
    out = tmp_path / "out"
    out.mkdir()
    (out / "narration.json").write_text("{", encoding="utf-8")

    error = assert_error(installed("narrate", write_narration(THREE_LINES), "--out", out, "--line", "send"),
                         2, "invalid_previous_output")
    assert "without --line" in error["hint"]


def test_a_line_whose_text_changed_but_is_not_read_again_is_warned_stale(installed, write_narration, tmp_path):
    out = tmp_path / "out"
    before = lines_by_id(read_all(installed, write_narration, out))
    files = snapshot(out)
    changed = with_line(THREE_LINES, "outro", text="就是这么简单。")

    run = installed("narrate", write_narration(changed), "--out", out, "--line", "send")

    outro = lines_by_id(run)["outro"]
    assert [w["code"] for w in outro["warnings"]] == ["stale_audio"]
    assert "--line outro" in outro["warnings"][0]["message"]
    assert {k: v for k, v in outro.items() if k != "warnings"} == {k: v for k, v in before["outro"].items() if k != "warnings"}
    assert (out / "outro.wav").read_bytes() == files["outro.wav"]
    assert lines_by_id(run)["intro"]["warnings"] == []

    # Running again does not repeat the warning, and reading the Line again clears it.
    again = installed("narrate", write_narration(changed), "--out", out, "--line", "send")
    assert [w["code"] for w in lines_by_id(again)["outro"]["warnings"]] == ["stale_audio"]
    fixed = installed("narrate", write_narration(changed), "--out", out, "--line", "outro")
    assert lines_by_id(fixed)["outro"]["text"] == "就是这么简单。"
    assert lines_by_id(fixed)["outro"]["warnings"] == []


def test_a_new_line_must_be_read_with_line(installed, write_narration, tmp_path):
    out = tmp_path / "out"
    read_all(installed, write_narration, out)
    files = snapshot(out)
    grown = {**THREE_LINES, "lines": [*THREE_LINES["lines"][:2], {"id": "tip", "text": "也可以按回车。"}, THREE_LINES["lines"][2]]}

    error = assert_error(installed("narrate", write_narration(grown), "--out", out, "--line", "send"), 2, "line_not_read")
    assert error["details"]["unread"] == ["tip"]
    assert snapshot(out) == files

    run = installed("narrate", write_narration(grown), "--out", out, "--line", "tip")
    assert run.exit_code == 0, run.result
    assert [l["id"] for l in run.result["data"]["narration"]["lines"]] == ["intro", "send", "tip", "outro"]
    assert (out / "tip.wav").exists()
    assert (out / "send.wav").read_bytes() == files["send.wav"]
