import json
import wave

import numpy as np
from conftest import assert_error, snapshot

TEXT = "大家好，这是一段试读稿。"
WARM = "温和的中年女声，语速偏慢"
BRIGHT = "明亮的年轻男声，语气轻快"
NARRATION = {"language": "zh", "voice": "host", "lines": [{"id": "intro", "text": "这是一个新的发送流程。"},
                                                          {"id": "send", "text": "点一下发送就完成了。"}]}


def design(voxx, out, *describes, takes=1):
    args = ["voice", "design", *(a for d in describes for a in ("--describe", d)), "--text", TEXT, "--language", "zh",
            "--out", out, "--takes", takes, "--model", "fake-clone"]
    run = voxx(*args)
    assert run.exit_code == 0, run.result
    return run.result["data"]["design"]


def read_wav(path):
    with wave.open(str(path)) as audio:
        return audio.getnchannels(), audio.getframerate(), np.frombuffer(audio.readframes(audio.getnframes()), "<i2")


def lines(run):
    return {line["id"]: line for line in run.result["data"]["narration"]["lines"]}


def test_a_chosen_design_take_is_stored_as_a_designed_voice_that_narrate_reads(installed, write_narration, tmp_path):
    takes = design(installed, tmp_path / "design", WARM, BRIGHT)["takes"]

    run = installed("voice", "add", "host", "--from-design", tmp_path / "design", "--take", 2, "--model", "fake-clone")

    assert run.exit_code == 0, run.result
    voice = run.result["data"]
    path = installed.home / "voices" / "host"
    assert (voice["name"], voice["kind"], voice["description"]) == ("host", "designed", BRIGHT)
    assert (voice["design_model"], voice["take"], voice["seed"]) == ("fake-clone", 2, takes[1]["seed"])
    # The Design Take is the Reference Recording, and the words it read are its text.
    assert (voice["reference_text"], voice["model"], voice["transcribed_by"]) == (TEXT, "fake-clone", None)
    assert voice["source"] == str(tmp_path / "design" / "take-2.wav")
    channels, rate, _ = read_wav(path / "reference.wav")
    assert (channels, rate) == (1, 24_000)
    stored = json.loads((path / "voice.json").read_text(encoding="utf-8"))
    assert stored == {k: voice[k] for k in ("name", "kind", "reference_text", "model", "source", "created",
                                            "transcribed_by", "description", "design_model", "take", "seed")}

    [listed] = [v for v in installed("voices").result["data"]["voices"] if v["name"] == "host"]
    assert (listed["kind"], listed["description"]) == ("designed", BRIGHT)
    # Not limited to the language it was designed in: any Model that clones reads it in its languages.
    assert {"zh", "en"} <= set(listed["languages"])

    run = installed("narrate", write_narration(NARRATION), "--out", tmp_path / "out")
    assert run.exit_code == 0, run.result
    assert {(l["model"], l["voice"]) for l in lines(run).values()} == {("fake-clone", "host")}


def test_a_take_that_is_not_there_or_a_design_that_cannot_be_read_is_an_argument_error(installed, tmp_path):
    out = tmp_path / "design"
    design(installed, out, WARM, takes=2)

    def add(path, take):
        return installed("voice", "add", "host", "--from-design", path, "--take", take, "--model", "fake-clone")

    error = assert_error(add(out, 3), 2, "take_not_found")
    assert error["details"]["takes"] == [1, 2]
    assert_error(add(tmp_path / "nowhere", 1), 2, "design_not_found")
    (out / "take-1.wav").unlink()
    assert_error(add(out, 1), 2, "invalid_design")
    (out / "design.json").write_text("{", encoding="utf-8")
    error = assert_error(add(out, 2), 2, "invalid_design")
    assert "voxx voice design" in error["hint"]
    assert not (installed.home / "voices" / "host").exists()


def test_from_design_goes_with_take_and_not_with_ref_or_ref_text(installed, tmp_path):
    out = tmp_path / "design"
    design(installed, out, WARM)
    take = out / "take-1.wav"

    for args in (["--from-design", out], ["--take", 1], ["--from-design", out, "--take", 1, "--ref", take],
                 ["--from-design", out, "--take", 1, "--ref-text", TEXT], []):
        assert_error(installed("voice", "add", "host", *args), 2, "invalid_arguments")
    assert not (installed.home / "voices" / "host").exists()


def test_a_designed_voice_is_read_by_the_default_model_that_clones_unless_model_names_another(installed, tmp_path):
    out = tmp_path / "design"
    design(installed, out, WARM)

    # Storing it needs no Model installed: the words are the text the Design Take read.
    run = installed("voice", "add", "host", "--from-design", out, "--take", 1)
    assert run.exit_code == 0, run.result
    assert run.result["data"]["model"] == "voxcpm2"
    error = assert_error(installed("voice", "add", "other", "--from-design", out, "--take", 1, "--model", "fake-tts"),
                         4, "capability_unsupported")
    assert error["details"] == {"model": "fake-tts", "capability": "clone"}


def test_a_designed_voice_overwrites_only_with_overwrite(installed, tmp_path):
    out = tmp_path / "design"
    design(installed, out, WARM, takes=2)
    assert installed("voice", "add", "host", "--from-design", out, "--take", 1).exit_code == 0
    before = snapshot(installed.home / "voices" / "host")

    assert_error(installed("voice", "add", "host", "--from-design", out, "--take", 2), 2, "voice_exists")
    assert snapshot(installed.home / "voices" / "host") == before
    run = installed("voice", "add", "host", "--from-design", out, "--take", 2, "--overwrite")
    assert run.exit_code == 0, run.result
    assert run.result["data"]["take"] == 2


def test_a_cloned_voice_stored_before_designed_voices_lists_and_reads_as_cloned(installed, write_narration, tmp_path):
    out = tmp_path / "design"
    design(installed, out, WARM)
    assert installed("voice", "add", "host", "--ref", out / "take-1.wav", "--ref-text", TEXT, "--model",
                     "fake-clone").exit_code == 0
    file = installed.home / "voices" / "host" / "voice.json"
    stored = json.loads(file.read_text(encoding="utf-8"))
    assert stored.pop("kind") == "cloned"
    file.write_text(json.dumps(stored), encoding="utf-8")

    [listed] = [v for v in installed("voices").result["data"]["voices"] if v["name"] == "host"]
    assert listed["kind"] == "cloned" and "description" not in listed
    run = installed("narrate", write_narration(NARRATION), "--out", tmp_path / "out")
    assert run.exit_code == 0, run.result


def test_a_designed_voice_reads_as_the_cloned_voice_of_its_take_would(installed, write_narration, tmp_path):
    out = tmp_path / "design"
    design(installed, out, WARM)
    assert installed("voice", "add", "host", "--from-design", out, "--take", 1, "--model", "fake-clone").exit_code == 0
    assert installed("voice", "add", "copy", "--ref", out / "take-1.wav", "--ref-text", TEXT, "--model",
                     "fake-clone").exit_code == 0
    first = installed("narrate", write_narration(NARRATION), "--out", tmp_path / "designed")
    assert first.exit_code == 0, first.result

    # The same Lines with the same seeds, in the Cloned Voice made from the same Design Take.
    done = first.result["data"]["narration"]
    path = write_narration({**done, "voice": "copy", "lines": [{k: l[k] for k in ("id", "text", "seed")}
                                                              for l in done["lines"]]}, name="copy.json")
    second = installed("narrate", path, "--out", tmp_path / "cloned")
    assert second.exit_code == 0, second.result
    for line in done["lines"]:
        assert (tmp_path / "designed" / line["audio"]).read_bytes() == (tmp_path / "cloned" / line["audio"]).read_bytes()
