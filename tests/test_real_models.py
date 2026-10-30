"""Slow tests with the real Models, in the user's own $VOXX_HOME. Opt in with VOXX_TEST_REAL=1; a test skips when
its Model is not installed. Listening is still a person's job: these only catch audio that is broken or silent."""

import json
import os
import subprocess
import wave

import numpy as np
import pytest
from conftest import VOXX

pytestmark = pytest.mark.skipif(os.environ.get("VOXX_TEST_REAL") != "1", reason="set VOXX_TEST_REAL=1 to use the real Models")

NARRATIONS = {
    "zh": {"language": "zh", "lines": [{"id": "intro", "text": "这是一个新的发送流程。"},
                                       {"id": "send", "text": "点一下发送就完成了。", "style": "语气兴奋"}]},
    "en": {"language": "en", "lines": [{"id": "intro", "text": "This is the new way to send a file."},
                                       {"id": "send", "text": "Press send, and you're done.", "style": "Excited."}]},
}


def real_voxx(*args):
    env = {k: v for k, v in os.environ.items() if not k.startswith("VOXX_TEST_")}
    process = subprocess.run([str(VOXX), *map(str, args)], capture_output=True, encoding="utf-8", timeout=900, env=env)
    return process.returncode, json.loads(process.stdout)


@pytest.fixture(scope="module")
def installed_models():
    code, result = real_voxx("models", "--installed")
    assert code == 0
    return {m["id"] for m in result["data"]["models"]}


@pytest.fixture(params=["qwen3-tts-1.7b-customvoice", "qwen3-tts-0.6b-customvoice"])
def model(request, installed_models):
    if request.param not in installed_models:
        pytest.skip(f"{request.param} is not installed")
    return request.param


def narrate(model, narration, out):
    path = out.with_suffix(".json")
    path.write_text(json.dumps(narration, ensure_ascii=False), encoding="utf-8")
    code, result = real_voxx("narrate", path, "--out", out, "--model", model)
    assert code == 0, result
    return result["data"]["narration"]["lines"]


@pytest.mark.parametrize("language", ["zh", "en"])
def test_a_real_model_reads_every_line_to_an_audible_wav(model, language, tmp_path):
    out = tmp_path / "out"
    for line in narrate(model, NARRATIONS[language], out):
        assert line["model"] == model
        with wave.open(str(out / line["audio"])) as audio:
            assert audio.getnchannels() == 1
            assert audio.getframerate() == line["sample_rate"] == 24_000
            samples = np.frombuffer(audio.readframes(audio.getnframes()), "<i2") / 32768
        seconds = len(samples) / line["sample_rate"]
        assert 1 < seconds < 15, f"{line['id']} is {seconds:.1f} s long"
        assert np.sqrt(np.mean(samples**2)) > 0.01, f"{line['id']} is silent"


def test_the_same_seed_reads_a_line_the_same_way(model, tmp_path):
    narration = {**NARRATIONS["en"], "seed": 42}
    first, second = narrate(model, narration, tmp_path / "first"), narrate(model, narration, tmp_path / "second")

    for a, b in zip(first, second):
        assert (tmp_path / "first" / a["audio"]).read_bytes() == (tmp_path / "second" / b["audio"]).read_bytes()
