"""Writing a Line's audio. Worker-side only."""

import wave

import numpy as np

from voxx.files import replacing


def write_wav(path, samples, sample_rate):
    """Mono 16-bit PCM at the Engine's native sample rate."""
    pcm = (np.clip(samples, -1.0, 1.0) * 32767).astype("<i2")
    with replacing(path) as partial, wave.open(str(partial), "wb") as f:
        f.setnchannels(1)
        f.setsampwidth(2)
        f.setframerate(sample_rate)
        f.writeframes(pcm.tobytes())
