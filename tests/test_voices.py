from conftest import assert_error
from test_clone import write_recording

QWEN3_TTS_LANGUAGES =["zh", "en", "ja", "ko", "fr", "de", "it", "pt", "ru", "es"]
CUSTOM_VOICE_MODELS = ["qwen3-tts-1.7b-customvoice", "qwen3-tts-0.6b-customvoice"]


def by_name(run):
    return {v["name"]: v for v in run.result["data"]["voices"]}


REAL = {"VOXX_TEST_FAKE_ENGINE": "0"}
MING = "ming-3.0-tts-0.5b"
# The English Voices in the Ming cookbook at the commit voxx copied.
MING_ENGLISH = {"US_Emma", "UK_George", "UK_Charlotte"}


def test_voices_lists_every_preset_voice_with_what_an_agent_needs_to_pick_one(voxx):
    run = voxx("voices", env=REAL)

    assert run.exit_code == 0
    voices = by_name(run)
    # Ming's Voices are too many to list unasked; it gets one line instead.
    assert set(voices) == {"vivian", "serena", "uncle_fu", "dylan", "eric", "ryan", "aiden", "ono_anna", "sohee"}
    assert run.result["data"]["unlisted"] == [{"model": MING, "installed": False, "voices": 241,
                                                "native_languages": {"zh": 238, "en": 3},
                                                "command": f"voxx voices --model {MING}"}]
    for voice in voices.values():
        assert voice["kind"] == "preset"
        assert voice["description"]
        assert voice["languages"] == QWEN3_TTS_LANGUAGES
        assert voice["models"] == [{"model": m, "installed": False} for m in CUSTOM_VOICE_MODELS]
    assert [voices[v]["native_language"] for v in ("vivian", "ryan", "ono_anna", "sohee")] == ["zh", "en", "ja", "ko"]
    assert "Beijing" in voices["dylan"]["description"]


def test_voices_of_one_model_lists_every_one_of_its_preset_voices(voxx):
    run = voxx("voices", "--model", MING, env=REAL)

    assert run.exit_code == 0
    voices = by_name(run)
    assert len(voices) == 241
    assert run.result["data"]["unlisted"] == []
    assert {n for n, v in voices.items() if v["native_language"] == "en"} == MING_ENGLISH
    # Each emotion variant is a Voice of its own, and a name keeps its space and parentheses.
    assert {"灵晓声_高兴", "灵晓声_悲伤", "蜡笔小新_野原美伢 (美伢)", "康熙王朝_康熙"} <= set(voices)
    assert voices["US_Emma"]["description"].startswith("Female, American.")
    assert voices["灵小锋"]["description"].startswith("Male, young adult.")
    assert all(v["models"] == [{"model": MING, "installed": False}] for v in voices.values())
    assert voices["US_Emma"]["languages"] == ["zh", "en", "ja", "ko", "de", "fr", "es"]


def test_voices_can_be_filtered_by_native_language(voxx):
    assert set(by_name(voxx("voices", "--model", MING, "--language", "en", env=REAL))) == MING_ENGLISH

    run = voxx("voices", "--language", "en", env=REAL)
    assert set(by_name(run)) == {"ryan", "aiden"}
    assert run.result["data"]["unlisted"] == [{"model": MING, "installed": False, "voices": 3,
                                                "native_languages": {"en": 3},
                                                "command": f"voxx voices --model {MING} --language en"}]
    nothing = voxx("voices", "--language", "it", env=REAL).result["data"]
    assert (nothing["voices"], nothing["unlisted"]) == ([], [])


def test_a_cloned_voice_is_listed_for_a_model_that_clones_in_its_language(voxx, tmp_path):
    recording = write_recording(tmp_path / "me.wav")
    assert voxx("voice", "add", "me", "--ref", recording, "--ref-text", "这是我的声音。").exit_code == 0

    assert "me" in by_name(voxx("voices", "--model", "fake-clone"))
    assert "me" not in by_name(voxx("voices", "--model", "fake-tts"))
    assert "me" in by_name(voxx("voices", "--language", "en"))
    assert "me" not in by_name(voxx("voices", "--language", "yue"))


def test_voices_of_an_unknown_model_or_a_malformed_language_are_usage_errors(voxx):
    assert_error(voxx("voices", "--model", "nope"), 2, "unknown_model")
    error = assert_error(voxx("voices", "--language", "EN"), 2, "invalid_language")
    assert "'en'" in error["message"]


def test_voices_shows_which_models_are_installed(voxx):
    assert voxx("install", "fake-tts").exit_code == 0
    voices = by_name(voxx("voices"))

    assert voices["fake-alice"]["models"] == [{"model": "fake-tts", "installed": True},
                                              {"model": "fake-tts-small", "installed": False}]
