"""Finishing and writing a Line's audio. Worker-side only."""

import warnings
import wave

import numpy as np
import pyloudnorm
from scipy.ndimage import minimum_filter1d, uniform_filter1d

from voxx.files import replacing

LOUDNESS = -18.0  # LUFS, integrated
TOLERANCE = 0.5  # LU a Line may fall short of LOUDNESS before it warns
SILENCE = 0.05  # seconds of silence left before and after the speech
QUIET = 10 ** (-50 / 20)  # a sample this far below the Line's peak counts as silence
BLOCK = 0.4  # seconds: the loudness meter's gating block
CEILING = 10 ** (-1 / 20)  # the highest peak a Line may reach, a little below full scale so it never clips
REACH = 0.01  # seconds either side of a peak over which the limiter turns the Line down and back up


def finish(samples, sample_rate):
    """The same loudness and the same short silences for every Line, at the Engine's native sample rate.
    Returns the samples and the Line's warnings."""
    samples = _trim(samples.astype(np.float64), round(sample_rate * SILENCE))
    loudness = _loudness(samples, sample_rate)
    if not np.isfinite(loudness):
        return samples, [{"code": "silent", "message": "The Model read the Line as silence."}]
    samples = _limit(samples * 10 ** ((LOUDNESS - loudness) / 20), round(sample_rate * REACH))
    reached = _loudness(samples, sample_rate)
    if reached >= LOUDNESS - TOLERANCE:
        return samples, []
    return samples, [{"code": "loudness_below_target",
                      "message": f"The Line peaks too often to reach {LOUDNESS:g} LUFS without clipping; it is {reached:.1f} LUFS."}]


def _loudness(samples, sample_rate):
    """Integrated loudness in LUFS; -inf for a Line too quiet to measure."""
    # A Line shorter than one block is measured as one block; a sample short of its length, so rounding never makes it longer.
    meter = pyloudnorm.Meter(sample_rate, block_size=min(BLOCK, (len(samples) - 1) / sample_rate))
    with warnings.catch_warnings(), np.errstate(divide="ignore"):
        warnings.simplefilter("ignore", RuntimeWarning)
        return meter.integrated_loudness(samples)


def _limit(samples, reach):
    """Turns down only the moments that would peak above CEILING, ramping in and out over `reach` samples."""
    needed = CEILING / np.maximum(np.abs(samples), CEILING)
    width = 2 * reach + 1
    # Each over-ceiling sample holds its gain across every window it falls in, so averaging those windows never lets it
    # through; the final minimum only absorbs rounding.
    gain = uniform_filter1d(minimum_filter1d(needed, width, mode="nearest"), width, mode="nearest")
    return samples * np.minimum(gain, needed)


def _trim(samples, margin):
    """Keeps `margin` samples around the speech: the Engine's own where it left that many, silence where it did not."""
    level = np.abs(samples)
    loud = np.flatnonzero(level >= level.max() * QUIET)
    start, end = loud[0], loud[-1] + 1
    kept = samples[max(0, start - margin):end + margin]
    return np.pad(kept, (margin - min(start, margin), margin - min(len(samples) - end, margin)))


def write_wav(path, samples, sample_rate):
    """Mono 16-bit PCM at the Engine's native sample rate."""
    pcm = (np.clip(samples, -1.0, 1.0) * 32767).astype("<i2")
    with replacing(path) as partial, wave.open(str(partial), "wb") as f:
        f.setnchannels(1)
        f.setsampwidth(2)
        f.setframerate(sample_rate)
        f.writeframes(pcm.tobytes())
