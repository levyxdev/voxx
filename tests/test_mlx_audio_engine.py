"""What the mlx-audio Engine hands each Model's generate, with mlx-audio's loader replaced by one that returns a Model
recording its arguments: no weights are loaded."""

import json
from pathlib import Path
from types import SimpleNamespace

import numpy as np
import pytest

from voxx.engines import mlx_audio
from voxx.engines.mlx_audio import MlxAudioEngine

NO_BGM = {"Genre": None, "Mood": None, "Instrument": None, "Theme": None, "ENV": None, "SNR": None}
REFERENCE = Path("me.wav")
REFERENCE_TEXT = "这是我自己的声音。"


class RecordingModel:
    """Stands in for a Model mlx-audio loaded: Ming-3.0 marks itself with `ming3`, the others name their architecture
    in config.model_type."""

    def __init__(self, model_type, ming3=False, channels=1):
        self.config = SimpleNamespace(model_type=model_type)
        self.ming3 = ming3
        self.channels = channels
        self.arguments = {}

    def generate(self, **arguments):
        self.arguments = arguments
        shape = (4410, self.channels) if self.channels > 1 else (4410,)
        yield SimpleNamespace(audio=np.full(shape, 0.1, dtype=np.float32), sample_rate=44_100)


def loaded(monkeypatch, model, capability="preset_voice", extra_repos=None):
    monkeypatch.setattr(mlx_audio, "load_tts", lambda path: model)
    engine = MlxAudioEngine()
    engine.load(Path("/models/any"), capability, extra_repos=extra_repos or {})
    return engine


@pytest.fixture
def ming(monkeypatch):
    return loaded(monkeypatch, RecordingModel("dense", ming3=True))


def arguments(engine):
    return engine.model.arguments


def caption(engine):
    """The one item of the control caption Ming was given, in the cookbook's Chinese field names."""
    [item] = json.loads(arguments(engine)["instruct"])["audio_sequence"]
    return item


def test_ming_reads_delivery_controls_in_its_own_words_beside_a_preset_voice(ming):
    ming.synthesize("你好。", model="ming-3.0-tts-0.5b", voice="灵小柔", style=None,
                    controls={"emotion": "happy", "speed": "slow", "pitch": "high", "volume": "low"}, language="zh", seed=1)

    # The cookbook's "Speech Control" values (inclusionAI/Ming-3.0-tts 9332fb9).
    assert caption(ming) == {"序号": 1, "说话人": "speaker_1", "方言": None, "风格": None, "语速": "慢速", "基频": "高",
                             "音量": "低", "情感": "高兴", "BGM": NO_BGM, "IP": "灵小柔"}
    assert "voice" not in arguments(ming)
    assert arguments(ming)["use_zero_spk_emb"] is True
    assert arguments(ming)["lang_code"] == "chinese"


@pytest.mark.parametrize("value, word", [("happy", "高兴"), ("sad", "悲伤"), ("angry", "愤怒"), ("fearful", "恐惧"),
                                         ("disgusted", "厌恶"), ("surprised", "惊讶"), ("neutral", "中性")])
def test_ming_reads_every_emotion_in_its_own_word(ming, value, word):
    ming.synthesize("Hello.", model="ming-3.0-tts-0.5b", voice="US_Emma", style=None, controls={"emotion": value},
                    language="en", seed=1)

    assert caption(ming)["情感"] == word


@pytest.mark.parametrize("field, key, words", [("speed", "语速", {"slow": "慢速", "medium": "中速", "fast": "快速"}),
                                               ("pitch", "基频", {"low": "低", "medium": "中", "high": "高"}),
                                               ("volume", "音量", {"low": "低", "medium": "中", "high": "高"})])
def test_ming_reads_every_speed_pitch_and_volume_in_its_own_words(ming, field, key, words):
    for value, word in words.items():
        ming.synthesize("Hello.", model="ming-3.0-tts-0.5b", voice="US_Emma", style=None, controls={field: value},
                        language="en", seed=1)

        assert caption(ming)[key] == word


def test_a_preset_voice_without_delivery_controls_is_still_named_in_the_caption(ming):
    ming.synthesize("你好。", model="ming-3.0-tts-0.5b", voice="蜡笔小新_野原美伢 (美伢)", style=None, controls={},
                    language="zh", seed=1)

    item = caption(ming)
    assert item["IP"] == "蜡笔小新_野原美伢 (美伢)"
    assert [item[key] for key in ("风格", "语速", "基频", "音量", "情感")] == [None] * 5


def test_ming_clones_from_the_reference_and_its_words_with_controls_in_the_caption(ming):
    ming.clone("你好。", model="ming-3.0-tts-0.5b", reference=REFERENCE, reference_text=REFERENCE_TEXT, style=None,
               controls={"speed": "fast"}, language="zh", seed=1)

    assert (arguments(ming)["ref_audio"], arguments(ming)["ref_text"]) == ("me.wav", REFERENCE_TEXT)
    assert (caption(ming)["语速"], caption(ming)["IP"]) == ("快速", None)
    assert arguments(ming)["use_zero_spk_emb"] is True


def test_ming_clones_without_a_caption_when_no_delivery_control_is_asked_for(ming):
    ming.clone("你好。", model="ming-3.0-tts-0.5b", reference=REFERENCE, reference_text=REFERENCE_TEXT, style=None,
               controls={}, language="zh", seed=1)

    assert arguments(ming) == {"text": "你好。", "ref_audio": "me.wav", "ref_text": REFERENCE_TEXT, "lang_code": "chinese",
                               "split_pattern": "", "verbose": False}


def test_ming_designs_a_voice_from_the_caption_style_field(ming):
    ming.design("Hello.", model="ming-3.0-tts-0.5b", description="A calm middle-aged man.", language="en", seed=1)

    assert (caption(ming)["风格"], caption(ming)["IP"]) == ("A calm middle-aged man.", None)
    assert arguments(ming)["use_zero_spk_emb"] is True
    assert arguments(ming)["lang_code"] == "english"


def test_a_preset_voice_goes_to_qwen3_tts_by_name_with_the_style_as_instruct(monkeypatch):
    engine = loaded(monkeypatch, RecordingModel("qwen3_tts"))

    engine.synthesize("你好。", model="qwen3-tts-1.7b-customvoice", voice="serena", style="温柔", controls={},
                      language="zh", seed=1)

    assert arguments(engine) == {"text": "你好。", "voice": "serena", "instruct": "温柔", "lang_code": "chinese",
                                 "split_pattern": "", "verbose": False}


def test_voxcpm2_continues_the_reference_unless_a_style_is_given(monkeypatch):
    engine = loaded(monkeypatch, RecordingModel("voxcpm2"), "clone")

    engine.clone("你好。", model="voxcpm2", reference=REFERENCE, reference_text=REFERENCE_TEXT, style=None, controls={},
                 language="zh", seed=1)
    plain = arguments(engine)
    engine.clone("你好。", model="voxcpm2", reference=REFERENCE, reference_text=REFERENCE_TEXT, style="温柔", controls={},
                 language="zh", seed=1)

    assert plain == {"text": "你好。", "ref_audio": "me.wav", "ref_text": REFERENCE_TEXT, "prompt_audio": "me.wav",
                     "prompt_text": REFERENCE_TEXT, "lang_code": "chinese", "split_pattern": "", "verbose": False}
    assert arguments(engine) == {"text": "你好。", "ref_audio": "me.wav", "instruct": "温柔", "lang_code": "chinese",
                                 "split_pattern": "", "verbose": False}


def test_voxcpm2_designs_from_the_description_as_instruct(monkeypatch):
    engine = loaded(monkeypatch, RecordingModel("voxcpm2"), "design")

    engine.design("Hello.", model="voxcpm2", description="A calm man.", language="en", seed=1)

    assert arguments(engine) == {"text": "Hello.", "instruct": "A calm man.", "lang_code": "english", "split_pattern": "",
                                 "verbose": False}


def test_chatterbox_is_given_the_language_tag_itself(monkeypatch):
    engine = loaded(monkeypatch, RecordingModel("chatterbox"), "clone")

    engine.clone("Hei.", model="chatterbox-multilingual-v3", reference=REFERENCE, reference_text="Hei.", style=None,
                 controls={}, language="no", seed=1)

    assert arguments(engine)["lang_code"] == "no"
    assert arguments(engine)["ref_audio"] == "me.wav"


def test_moss_clones_with_the_installed_audio_tokenizer_and_reads_in_mono(monkeypatch):
    tokenizer = Path("/voxx/hf-cache/models--OpenMOSS-Team--MOSS-Audio-Tokenizer-Nano/snapshots/0123")
    engine = loaded(monkeypatch, RecordingModel("moss_tts_nano", channels=2), "clone",
                    extra_repos={"OpenMOSS-Team/MOSS-Audio-Tokenizer-Nano": tokenizer})

    samples, sample_rate = engine.clone("你好。", model="moss-tts-nano-100m", reference=REFERENCE,
                                        reference_text=REFERENCE_TEXT, style=None, controls={}, language="zh", seed=1)

    assert arguments(engine) == {"text": "你好。", "ref_audio": "me.wav", "audio_tokenizer_source": str(tokenizer),
                                 "split_pattern": "", "verbose": False}
    assert samples.shape == (4410,)
    assert sample_rate == 44_100
