"""What the mlx-audio Engine hands Ming-3.0-tts, with mlx-audio's loaded Model replaced by one that records its
arguments: no weights are loaded."""

import json
from pathlib import Path
from types import SimpleNamespace

import numpy as np
import pytest

from voxx.engines.mlx_audio import MlxAudioEngine

NO_BGM = {"Genre": None, "Mood": None, "Instrument": None, "Theme": None, "ENV": None, "SNR": None}


class RecordingMing:
    """Stands in for mlx-audio's Ming-3.0 Model, which marks itself with `ming3`."""
    ming3 = True

    def __init__(self):
        self.arguments = {}

    def generate(self, **arguments):
        self.arguments = arguments
        yield SimpleNamespace(audio=np.zeros(4410, dtype=np.float32), sample_rate=44_100)


@pytest.fixture
def ming():
    engine = MlxAudioEngine()
    engine.model = RecordingMing()
    return engine


def caption(arguments):
    """The one item of the control caption Ming was given, in the cookbook's Chinese field names."""
    [item] = json.loads(arguments["instruct"])["audio_sequence"]
    return item


def test_ming_reads_delivery_controls_in_its_own_words_beside_a_preset_voice(ming):
    ming.synthesize("你好。", model="ming-3.0-tts-0.5b", voice="灵小柔", style=None,
                    controls={"emotion": "happy", "speed": "slow", "pitch": "high", "volume": "low"}, language="zh", seed=1)

    arguments = ming.model.arguments
    # The cookbook's "Speech Control" values (inclusionAI/Ming-3.0-tts 9332fb9).
    assert caption(arguments) == {"序号": 1, "说话人": "speaker_1", "方言": None, "风格": None, "语速": "慢速", "基频": "高",
                                  "音量": "低", "情感": "高兴", "BGM": NO_BGM, "IP": "灵小柔"}
    assert "voice" not in arguments
    assert arguments["use_zero_spk_emb"] is True
    assert arguments["lang_code"] == "chinese"


@pytest.mark.parametrize("value, word", [("happy", "高兴"), ("sad", "悲伤"), ("angry", "愤怒"), ("fearful", "恐惧"),
                                         ("disgusted", "厌恶"), ("surprised", "惊讶"), ("neutral", "中性")])
def test_ming_reads_every_emotion_in_its_own_word(ming, value, word):
    ming.synthesize("Hello.", model="ming-3.0-tts-0.5b", voice="US_Emma", style=None, controls={"emotion": value},
                    language="en", seed=1)

    assert caption(ming.model.arguments)["情感"] == word


@pytest.mark.parametrize("field, key, words", [("speed", "语速", {"slow": "慢速", "medium": "中速", "fast": "快速"}),
                                               ("pitch", "基频", {"low": "低", "medium": "中", "high": "高"}),
                                               ("volume", "音量", {"low": "低", "medium": "中", "high": "高"})])
def test_ming_reads_every_speed_pitch_and_volume_in_its_own_words(ming, field, key, words):
    for value, word in words.items():
        ming.synthesize("Hello.", model="ming-3.0-tts-0.5b", voice="US_Emma", style=None, controls={field: value},
                        language="en", seed=1)

        assert caption(ming.model.arguments)[key] == word


def test_a_preset_voice_without_delivery_controls_is_still_named_in_the_caption(ming):
    ming.synthesize("你好。", model="ming-3.0-tts-0.5b", voice="蜡笔小新_野原美伢 (美伢)", style=None, controls={},
                    language="zh", seed=1)

    item = caption(ming.model.arguments)
    assert item["IP"] == "蜡笔小新_野原美伢 (美伢)"
    assert [item[key] for key in ("风格", "语速", "基频", "音量", "情感")] == [None] * 5


def test_ming_clones_from_the_reference_and_its_words_with_controls_in_the_caption(ming):
    ming.clone("你好。", model="ming-3.0-tts-0.5b", reference=Path("me.wav"), reference_text="这是我自己的声音。",
               style=None, controls={"speed": "fast"}, language="zh", seed=1)

    arguments = ming.model.arguments
    assert (arguments["ref_audio"], arguments["ref_text"]) == ("me.wav", "这是我自己的声音。")
    item = caption(arguments)
    assert (item["语速"], item["IP"]) == ("快速", None)
    assert arguments["use_zero_spk_emb"] is True


def test_ming_clones_without_a_caption_when_no_delivery_control_is_asked_for(ming):
    ming.clone("你好。", model="ming-3.0-tts-0.5b", reference=Path("me.wav"), reference_text="这是我自己的声音。",
               style=None, controls={}, language="zh", seed=1)

    arguments = ming.model.arguments
    assert (arguments["ref_audio"], arguments["ref_text"]) == ("me.wav", "这是我自己的声音。")
    assert "instruct" not in arguments and "use_zero_spk_emb" not in arguments


def test_ming_designs_a_voice_from_the_caption_style_field(ming):
    ming.design("Hello.", model="ming-3.0-tts-0.5b", description="A calm middle-aged man.", language="en", seed=1)

    arguments = ming.model.arguments
    item = caption(arguments)
    assert (item["风格"], item["IP"]) == ("A calm middle-aged man.", None)
    assert arguments["use_zero_spk_emb"] is True
    assert arguments["lang_code"] == "english"
