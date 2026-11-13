"""A Default Voice per language: what a Line is read in when neither it nor its Narration names a Voice."""

from conftest import assert_error
from test_clone import write_recording

NO_VOICE = {"language": "zh", "lines": [{"id": "intro", "text": "这是一个新的发送流程。"},
                                        {"id": "send", "text": "点一下发送就完成了。"}]}


def voices_read(run):
    assert run.exit_code == 0, run.result
    return {line["id"]: line["voice"] for line in run.result["data"]["narration"]["lines"]}


def test_a_narration_without_a_voice_is_read_in_the_default_voice_of_its_language(installed, write_narration, tmp_path):
    assert installed("voice", "default", "fake-bob", "--language", "zh").exit_code == 0

    run = installed("narrate", write_narration(NO_VOICE), "--out", tmp_path / "out")

    assert voices_read(run) == {"intro": "fake-bob", "send": "fake-bob"}


def test_a_voice_the_narration_or_a_line_names_wins_over_the_default(installed, write_narration, tmp_path):
    assert installed("voice", "default", "fake-bob", "--language", "zh").exit_code == 0
    narration = {**NO_VOICE, "voice": "fake-alice",
                 "lines": [NO_VOICE["lines"][0], {**NO_VOICE["lines"][1], "voice": "fake-bob"}]}

    assert voices_read(installed("narrate", write_narration(narration), "--out", tmp_path / "out")) == {
        "intro": "fake-alice", "send": "fake-bob"}


def test_the_default_voice_of_another_language_does_not_apply(installed, write_narration, tmp_path):
    assert installed("voice", "default", "fake-bob", "--language", "zh").exit_code == 0

    run = installed("narrate", write_narration({**NO_VOICE, "language": "fr"}), "--out", tmp_path / "out",
                    "--model", "fake-tts")

    # fr has no Default Voice, and no Voice native to it: the Model reads in its first Voice, as without any default.
    assert voices_read(run) == {"intro": "fake-alice", "send": "fake-alice"}


def test_only_a_voice_some_model_reads_in_that_language_can_be_its_default(installed, write_narration, tmp_path):
    assert installed("voice", "default", "fake-bob", "--language", "zh").exit_code == 0

    assert_error(installed("voice", "default", "nobody", "--language", "zh"), 2, "unknown_voice")
    assert_error(installed("voice", "default", "fake-alice", "--language", "ja"), 4, "unsupported_language")
    error = assert_error(installed("voice", "default", "fake-alice", "--language", "ZH"), 2, "invalid_language")
    assert "'zh'" in error["message"]

    # None of them replaced the Default Voice of zh.
    assert voices_read(installed("narrate", write_narration(NO_VOICE), "--out", tmp_path / "out")) == {
        "intro": "fake-bob", "send": "fake-bob"}


def default_for(run):
    assert run.exit_code == 0, run.result
    return {v["name"]: v["default_for"] for v in run.result["data"]["voices"]}


def test_voices_says_which_languages_each_voice_is_the_default_of_and_clear_takes_it_back(installed):
    assert installed("voice", "default", "fake-bob", "--language", "zh").exit_code == 0
    assert installed("voice", "default", "fake-bob", "--language", "en").exit_code == 0

    assert default_for(installed("voices", "--model", "fake-tts")) == {
        "fake-alice": [], "fake-bob": ["en", "zh"]}

    run = installed("voice", "default", "--language", "zh", "--clear")
    assert run.result == {"ok": True, "data": {"language": "zh", "voice": None}}
    assert default_for(installed("voices", "--model", "fake-tts"))["fake-bob"] == ["en"]


def test_voice_default_needs_either_a_voice_or_clear(installed):
    assert_error(installed("voice", "default", "--language", "zh"), 2, "invalid_arguments")
    assert_error(installed("voice", "default", "fake-bob", "--language", "zh", "--clear"), 2, "invalid_arguments")


def test_a_cloned_voice_can_be_the_default_too(installed, tmp_path):
    recording = write_recording(tmp_path / "me.wav")
    assert installed("voice", "add", "me", "--ref", recording, "--ref-text", "这是我自己的声音。",
                     "--model", "fake-clone").exit_code == 0

    assert installed("voice", "default", "me", "--language", "zh").exit_code == 0
    assert default_for(installed("voices", "--model", "fake-clone")) == {"me": ["zh"]}


def test_a_default_voice_that_cannot_be_read_fails_as_one_the_narration_names_would_and_says_it_is_the_default(
        installed, write_narration, tmp_path):
    recording = write_recording(tmp_path / "me.wav")
    assert installed("voice", "add", "me", "--ref", recording, "--ref-text", "这是我自己的声音。",
                     "--model", "fake-clone").exit_code == 0
    assert installed("voice", "default", "me", "--language", "zh").exit_code == 0
    path = write_narration(NO_VOICE)

    # A Model that reads only Preset Voices cannot read the Cloned Voice the default names.
    error = assert_error(installed("narrate", path, "--out", tmp_path / "out", "--model", "fake-tts"), 4,
                         "capability_unsupported")
    assert error["details"]["default_voice"] == {"language": "zh", "voice": "me"}
    assert "voxx voice default" in error["hint"]

    # Nor can a default whose Voice is gone.
    for f in (installed.home / "voices" / "me").iterdir():
        f.unlink()
    (installed.home / "voices" / "me").rmdir()
    error = assert_error(installed("narrate", path, "--out", tmp_path / "out"), 2, "unknown_voice")
    assert error["details"]["default_voice"] == {"language": "zh", "voice": "me"}


def test_a_default_voices_file_voxx_did_not_write_is_an_error_that_says_how_to_recover(installed, write_narration,
                                                                                        tmp_path):
    (installed.home / "default-voices.json").write_text('["fake-bob"]', encoding="utf-8")

    error = assert_error(installed("narrate", write_narration(NO_VOICE), "--out", tmp_path / "out"), 2,
                         "invalid_default_voices")
    assert error["details"]["path"] == str(installed.home / "default-voices.json")


def test_voices_lists_every_default_voice_even_one_its_filters_leave_out(installed):
    # fake-alice is native to zh, so --language en leaves it out of voices.
    assert installed("voice", "default", "fake-alice", "--language", "en").exit_code == 0

    run = installed("voices", "--model", "fake-tts", "--language", "en")

    assert "fake-alice" not in default_for(run)
    assert run.result["data"]["defaults"] == {"en": "fake-alice"}


def test_reading_one_line_again_after_the_default_changed_warns_that_the_other_lines_sound_otherwise(
        installed, write_narration, tmp_path):
    out, path = tmp_path / "out", write_narration(NO_VOICE)
    assert installed("voice", "default", "fake-bob", "--language", "zh").exit_code == 0
    assert installed("narrate", path, "--out", out).exit_code == 0

    assert installed("voice", "default", "fake-alice", "--language", "zh").exit_code == 0
    run = installed("narrate", path, "--out", out, "--line", "intro")

    lines = {line["id"]: line for line in run.result["data"]["narration"]["lines"]}
    assert lines["intro"]["voice"] == "fake-alice"
    assert lines["send"]["voice"] == "fake-bob"
    assert [w["code"] for w in lines["send"]["warnings"]] == ["stale_audio"]
