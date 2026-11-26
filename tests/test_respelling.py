"""Respelling: `say` changes what a Line is read as, while its text, words and check stay as written (levyxdev/voxx#46)."""

import pytest
from conftest import assert_error
from test_clone import write_recording
from test_narrate import lines_of


def narration(text, say=None, line_say=None):
    line = {"id": "a", "text": text, **({"say": line_say} if line_say is not None else {})}
    return {"language": "zh", "voice": "fake-alice", "seed": 7, **({"say": say} if say is not None else {}), "lines": [line]}


def read(installed, write_narration, tmp_path, name, given, *args):
    run = installed("narrate", write_narration(given, f"{name}.json"), "--out", tmp_path / name, *args)
    assert run.exit_code == 0, run.result
    return run


def assert_read_as(installed, write_narration, tmp_path, respelled, said):
    """The fake Engine hears back, with --check, exactly the text it read."""
    run = read(installed, write_narration, tmp_path, "respelled", respelled, "--check")
    assert lines_of(run)[0]["transcript"] == said


def test_a_respelled_line_is_read_as_said_and_keeps_its_text_words_and_check(installed, write_narration, tmp_path):
    run = read(installed, write_narration, tmp_path, "out", narration("用CueTake录的。", say={"CueTake": "Q Take"}), "--check")

    line = lines_of(run)[0]
    assert line["transcript"] == "用Q Take录的。"
    assert line["text"] == "用CueTake录的。"
    assert [w["text"] for w in line["words"]] == ["用", "CueTake", "录", "的"]
    # Checked against the text: 用 CueTake 录 的 heard as 用 Q Take 录 的 is two edits in four units.
    assert line["error_rate"] == 0.5
    assert line["respelled"] == "用Q Take录的。"
    assert run.result["data"]["narration"]["say"] == {"CueTake": "Q Take"}


def test_a_line_no_respelling_matches_is_completed_as_before(installed, write_narration, tmp_path):
    run = read(installed, write_narration, tmp_path, "out", narration("用这个录的。", say={"CueTake": "Q Take"}))

    assert "respelled" not in lines_of(run)[0]


def test_an_invalid_say_names_where_it_is(installed, write_narration, tmp_path):
    run = installed("narrate", write_narration(narration("一", line_say={"一": ""})), "--out", tmp_path / "out")

    assert assert_error(run, 2, "invalid_narration")["details"] == {"at": "$.lines[0].say"}


def test_a_line_say_overrides_the_narration_say_and_keeps_its_other_entries(installed, write_narration, tmp_path):
    respelled = narration("用CueTake录的。", say={"CueTake": "Q Take", "录": "陆"}, line_say={"CueTake": "Q忒克"})
    assert_read_as(installed, write_narration, tmp_path, respelled, "用Q忒克陆的。")


def test_the_longest_respelling_wins_wherever_two_match(installed, write_narration, tmp_path):
    respelled = narration("给你调岗，再调一下。", say={"调": "条", "调岗": "掉岗"})
    assert_read_as(installed, write_narration, tmp_path, respelled, "给你掉岗，再条一下。")


def test_a_respelling_is_not_respelled_again(installed, write_narration, tmp_path):
    respelled = narration("甲乙", say={"甲": "乙乙乙", "乙": "丙"})
    assert_read_as(installed, write_narration, tmp_path, respelled, "乙乙乙丙")


GIVE = "要补给你。"


@pytest.mark.parametrize("mark", ["{gei3}", "{ma5}", "{lv3}", "{xiàng}", "{gei}"])
def test_pinyin_in_say_fails_before_anything_is_read_on_a_model_that_would_read_it_aloud(installed, write_narration,
                                                                                        tmp_path, mark):
    given = {**narration(GIVE), "lines": [{"id": "a", "text": GIVE, "say": {"补给你": f"补{mark}你"}}, {"id": "b", "text": "一"}]}
    out = tmp_path / "out"
    error = assert_error(installed("narrate", write_narration(given), "--out", out), 4, "pinyin_unsupported")

    assert error["details"] == {"lines": ["a"], "models": ["fake-tts"]}
    # No Model that follows pinyin reads fake-alice, so none is offered.
    assert "--model" not in error["hint"]
    assert not out.exists()


def test_pinyin_in_say_is_read_by_a_model_that_follows_it_and_offered_to_one_that_does_not(installed, write_narration,
                                                                                         tmp_path):
    assert installed("voice", "add", "me", "--ref", write_recording(tmp_path / "me.wav"), "--model", "fake-clone").exit_code == 0
    given = {**narration(GIVE, say={"补给你": "补{gei3}你"}), "voice": "me"}

    run = read(installed, write_narration, tmp_path, "clone", given)
    assert lines_of(run)[0]["respelled"] == "要补{gei3}你。"
    alt = installed("narrate", write_narration(given), "--out", tmp_path / "alt", "--model", "fake-clone-alt")
    assert "--model fake-clone" in assert_error(alt, 4, "pinyin_unsupported")["hint"]


@pytest.mark.parametrize("text, say, said", [("要补{gei3}你。", None, "要补{gei3}你。"),
                                             (GIVE, {"补给你": "补{第三}你"}, "要补{第三}你。"),
                                             (GIVE, {"补给你": "补{×}你"}, "要补{×}你。")])
def test_braces_that_say_does_not_fill_with_pinyin_are_read_as_given(installed, write_narration, tmp_path, text, say,
                                                                    said):
    assert_read_as(installed, write_narration, tmp_path, narration(text, say=say), said)
