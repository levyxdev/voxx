REAL_MODELS = {
    "qwen3-tts-1.7b-customvoice": ("preset_voice", 3_080_141_538),
    "qwen3-tts-0.6b-customvoice": ("preset_voice", 1_973_575_388),
    "qwen3-tts-1.7b-base": ("clone", 3_104_158_788),
    "voxcpm2": ("clone", 3_226_617_581),
    "qwen3-forcedaligner-0.6b": ("align", 1_276_475_979),
    "qwen3-asr-0.6b": ("transcribe", 1_010_773_761),
}


def by_id(run):
    return {m["id"]: m for m in run.result["data"]["models"]}


def test_models_lists_every_registered_model_with_its_license(voxx):
    run = voxx("models")

    assert run.exit_code == 0
    models = by_id(run)
    assert set(REAL_MODELS) | {"fake-tts"} == set(models)
    for id, (capability, size) in REAL_MODELS.items():
        model = models[id]
        assert model["capabilities"] == [capability]
        assert model["size_bytes"] == size
        assert model["languages"] == ["zh", "en"]
        assert model["installed"] is False
        assert model["weights_license"]["id"] == "Apache-2.0"
        assert model["weights_license"]["url"].startswith("https://huggingface.co/")
        assert model["code_license"]["url"].startswith("https://github.com/")
        assert model["verified"] == "2026-10-30"
    assert models["qwen3-tts-1.7b-customvoice"]["sample_rate"] == 24_000
    assert models["voxcpm2"]["sample_rate"] == 48_000


def test_the_fake_model_is_listed_only_for_tests(voxx):
    run = voxx("models", env={"VOXX_TEST_FAKE_ENGINE": "0"})

    assert "fake-tts" not in by_id(run)


def test_models_can_be_filtered_by_capability(voxx):
    run = voxx("models", "--capability", "clone")

    assert set(by_id(run)) == {"qwen3-tts-1.7b-base", "voxcpm2"}


def test_an_unknown_capability_is_an_argument_error(voxx):
    run = voxx("models", "--capability", "sing")

    assert run.exit_code == 2
    assert run.result["error"]["code"] == "invalid_arguments"


def test_models_can_be_filtered_by_install_state(installed):
    assert set(by_id(installed("models", "--installed"))) == {"fake-tts"}
    assert set(by_id(installed("models", "--not-installed"))) == set(REAL_MODELS)
    assert by_id(installed("models"))["fake-tts"]["installed"] is True


def test_installed_and_not_installed_together_are_an_argument_error(voxx):
    assert voxx("models", "--installed", "--not-installed").exit_code == 2
