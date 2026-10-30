QWEN3_TTS_LANGUAGES = ["zh", "en", "ja", "ko", "fr", "de", "it", "pt", "ru", "es"]
CUSTOM_VOICE_MODELS = ["qwen3-tts-1.7b-customvoice", "qwen3-tts-0.6b-customvoice"]


def by_name(run):
    return {v["name"]: v for v in run.result["data"]["voices"]}


def test_voices_lists_every_preset_voice_with_what_an_agent_needs_to_pick_one(voxx):
    run = voxx("voices", env={"VOXX_TEST_FAKE_ENGINE": "0"})

    assert run.exit_code == 0
    voices = by_name(run)
    assert set(voices) == {"vivian", "serena", "uncle_fu", "dylan", "eric", "ryan", "aiden", "ono_anna", "sohee"}
    for voice in voices.values():
        assert voice["kind"] == "preset"
        assert voice["description"]
        assert voice["languages"] == QWEN3_TTS_LANGUAGES
        assert voice["models"] == [{"model": m, "installed": False} for m in CUSTOM_VOICE_MODELS]
    assert [voices[v]["native_language"] for v in ("vivian", "ryan", "ono_anna", "sohee")] == ["zh", "en", "ja", "ko"]
    assert "Beijing" in voices["dylan"]["description"]


def test_voices_shows_which_models_are_installed(voxx):
    assert voxx("install", "fake-tts").exit_code == 0
    voices = by_name(voxx("voices"))

    assert voices["fake-alice"]["models"] == [{"model": "fake-tts", "installed": True},
                                              {"model": "fake-tts-small", "installed": False}]
