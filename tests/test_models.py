# Each Model's capabilities, download size, license, and the date its license was checked.
REAL_MODELS = {
    "qwen3-tts-1.7b-customvoice": (["preset_voice"], 3_080_141_538, "Apache-2.0", "2026-10-30"),
    "qwen3-tts-0.6b-customvoice": (["preset_voice"], 1_973_575_388, "Apache-2.0", "2026-10-30"),
    "qwen3-tts-1.7b-base": (["clone"], 3_104_158_788, "Apache-2.0", "2026-10-30"),
    "voxcpm2": (["clone", "design"], 3_226_617_581, "Apache-2.0", "2026-10-30"),
    "qwen3-forcedaligner-0.6b": (["align"], 1_276_475_979, "Apache-2.0", "2026-10-30"),
    "qwen3-asr-0.6b": (["transcribe"], 1_010_773_761, "Apache-2.0", "2026-10-30"),
    "ming-3.0-tts-0.5b": (["preset_voice", "clone", "design"], 1_617_181_518, "MIT", "2026-11-06"),
    # 2,713,107,406 B of its own and 494,869,110 B of S3TokenizerV2.
    "chatterbox-multilingual-v3": (["clone"], 3_207_976_516, "MIT", "2026-11-06"),
    # 285,462,910 B of its own and 87,976,790 B of its audio tokenizer.
    "moss-tts-nano-100m": (["clone"], 373_439_700, "Apache-2.0", "2026-11-06"),
    "qwen3-tts-1.7b-voicedesign": (["design"], 3_080_140_867, "Apache-2.0", "2026-11-06"),
}


def by_id(run):
    return {m["id"]: m for m in run.result["data"]["models"]}


def test_models_lists_every_registered_model_with_its_license(voxx):
    run = voxx("models")

    assert run.exit_code == 0
    models = by_id(run)
    assert set(REAL_MODELS) | {"fake-tts", "fake-tts-small", "fake-asr", "fake-aligner", "fake-clone", "fake-clone-alt", "fake-clone-extra"} == set(models)
    for id, (capabilities, size, license, verified) in REAL_MODELS.items():
        model = models[id]
        assert model["capabilities"] == capabilities
        assert model["size_bytes"] == size
        assert model["installed"] is False
        assert model["weights_license"]["id"] == model["code_license"]["id"] == license
        assert model["weights_license"]["url"].startswith("https://huggingface.co/")
        assert model["code_license"]["url"].startswith("https://github.com/")
        assert model["verified"] == verified
    # Each Model reads the languages it supports upstream.
    assert models["qwen3-tts-1.7b-customvoice"]["languages"] == ["zh", "en", "ja", "ko", "fr", "de", "it", "pt", "ru", "es"]
    # Qwen3-ASR transcribes every language Qwen3-TTS reads, so each of their Lines is checked.
    assert set(models["qwen3-tts-1.7b-customvoice"]["languages"]) <= set(models["qwen3-asr-0.6b"]["languages"])
    assert models["qwen3-tts-1.7b-customvoice"]["sample_rate"] == 24_000
    assert models["voxcpm2"]["sample_rate"] == 48_000
    assert models["ming-3.0-tts-0.5b"]["languages"] == ["zh", "en", "ja", "ko", "de", "fr", "es"]
    assert models["ming-3.0-tts-0.5b"]["sample_rate"] == 44_100
    assert models["ming-3.0-tts-0.5b"]["repo"] == "mlx-community/Ming-3.0-tts-0.5B-8bit"
    assert models["ming-3.0-tts-0.5b"]["revision"] == "d0d1da6f627e4b3f20cc2db6ba4aee86d45343ad"
    chatterbox = models["chatterbox-multilingual-v3"]
    assert chatterbox["languages"] == ["ar", "da", "de", "el", "en", "es", "fi", "fr", "he", "hi", "it", "ja", "ko", "ms",
                                       "nl", "no", "pl", "pt", "ru", "sv", "sw", "tr", "zh"]
    assert chatterbox["sample_rate"] == 24_000
    assert (chatterbox["repo"], chatterbox["revision"]) == ("mlx-community/chatterbox-multilingual-v3",
                                                            "03565773edd72e949572557597af8063bb49a18a")
    # Its Engine loads S3TokenizerV2 by name; that repo has no license of its own, so it carries CosyVoice2's.
    assert chatterbox["extra_repos"] == [{"repo": "mlx-community/S3TokenizerV2", "size_bytes": 494_869_110,
                                          "license": {"id": "Apache-2.0",
                                                      "url": "https://huggingface.co/FunAudioLLM/CosyVoice2-0.5B"}}]
    moss = models["moss-tts-nano-100m"]
    assert moss["languages"] == ["zh", "en", "de", "es", "fr", "ja", "it", "he", "ko", "ru", "fa", "ar", "pl", "pt", "cs",
                                 "da", "sv", "hu", "el", "tr"]
    assert moss["sample_rate"] == 48_000
    assert (moss["repo"], moss["revision"]) == ("mlx-community/MOSS-TTS-Nano-100M", "229a9c51bb0ffff6fd0dbe53b5bf0c441e438a79")
    assert moss["extra_repos"] == [{"repo": "OpenMOSS-Team/MOSS-Audio-Tokenizer-Nano", "size_bytes": 87_976_790,
                                    "license": {"id": "Apache-2.0",
                                                "url": "https://huggingface.co/OpenMOSS-Team/MOSS-Audio-Tokenizer-Nano"}}]
    voice_design = models["qwen3-tts-1.7b-voicedesign"]
    assert voice_design["languages"] == ["zh", "en", "ja", "ko", "fr", "de", "it", "pt", "ru", "es"]
    assert voice_design["sample_rate"] == 24_000
    assert (voice_design["repo"], voice_design["revision"]) == ("mlx-community/Qwen3-TTS-12Hz-1.7B-VoiceDesign-8bit",
                                                                "f90d617701d9f7f4ca499291e0b57f2b3c2fd2ee")
    assert "extra_repos" not in voice_design


def test_the_fake_model_is_listed_only_for_tests(voxx):
    run = voxx("models", env={"VOXX_TEST_FAKE_ENGINE": "0"})

    assert "fake-tts" not in by_id(run)


def test_models_can_be_filtered_by_capability(voxx):
    run = voxx("models", "--capability", "clone")

    assert set(by_id(run)) == {"qwen3-tts-1.7b-base", "voxcpm2", "ming-3.0-tts-0.5b", "chatterbox-multilingual-v3", "moss-tts-nano-100m", "fake-clone", "fake-clone-alt", "fake-clone-extra"}


def test_voxcpm2_ming_and_qwen3_voicedesign_design_voices(voxx):
    run = voxx("models", "--capability", "design")

    assert set(by_id(run)) == {"voxcpm2", "ming-3.0-tts-0.5b", "qwen3-tts-1.7b-voicedesign", "fake-clone"}


def test_an_unknown_capability_is_an_argument_error(voxx):
    run = voxx("models", "--capability", "sing")

    assert run.exit_code == 2
    assert run.result["error"]["code"] == "invalid_arguments"


def test_models_can_be_filtered_by_install_state(installed):
    assert set(by_id(installed("models", "--installed"))) == {"fake-tts", "fake-tts-small", "fake-asr", "fake-aligner", "fake-clone", "fake-clone-alt", "fake-clone-extra"}
    assert set(by_id(installed("models", "--not-installed"))) == set(REAL_MODELS)
    assert by_id(installed("models"))["fake-tts"]["installed"] is True


def test_installed_and_not_installed_together_are_an_argument_error(voxx):
    assert voxx("models", "--installed", "--not-installed").exit_code == 2
