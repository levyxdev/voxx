"""The example Narration in examples/invite, read with the real Models, in the shape CueTake reads:
{ language, lines: [{ id, text, audio, words? }] }, with words as [{ text, start, end }] in seconds from the Line's start."""

import json
import re
from pathlib import Path

from scipy.io import wavfile

EXAMPLE = Path(__file__).parent.parent / "examples/invite"
# The ids CueTake accepts.
CUETAKE_ID = re.compile(r"[A-Za-z0-9._-]+")


def test_the_example_output_is_a_narration_cuetake_reads():
    given = json.loads((EXAMPLE / "narration.json").read_text(encoding="utf-8"))
    out = EXAMPLE / "out"
    narration = json.loads((out / "narration.json").read_text(encoding="utf-8"))

    assert narration["language"] == given["language"]
    assert [(l["id"], l["text"]) for l in narration["lines"]] == [(l["id"], l["text"]) for l in given["lines"]]
    for line in narration["lines"]:
        assert CUETAKE_ID.fullmatch(line["id"])
        rate, samples = wavfile.read(out / line["audio"])
        assert rate == line["sample_rate"]
        assert samples.ndim == 1
        duration = len(samples) / rate
        words = line["words"]
        assert "".join(w["text"] for w in words) == re.sub(r"[，。！]", "", line["text"])
        for word in words:
            assert set(word) == {"text", "start", "end"}
            assert 0 <= word["start"] <= word["end"] <= duration
        assert [w["start"] for w in words] == sorted(w["start"] for w in words)
        assert line["warnings"] == []
        assert line["error_rate"] < 0.2
