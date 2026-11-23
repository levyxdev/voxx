"""Finishing and writing a Line's audio and a Reference Recording, and cutting a Media File into Passages.
Worker-side only."""

import math
import shutil
import subprocess
import warnings
import wave

import numpy as np
import pyloudnorm
from scipy.ndimage import minimum_filter1d, uniform_filter1d
from scipy.signal import correlate, resample_poly
from scipy.signal.windows import hann

from voxx.files import replacing
from voxx.output import BUG_HINT, USAGE, VoxxError

LOUDNESS = -18.0  # LUFS, integrated
TOLERANCE = 0.5  # LU a Line may fall short of LOUDNESS before it warns
SILENCE = 0.05  # seconds of silence left before and after the speech
QUIET = 10 ** (-50 / 20)  # a sample this far below the Line's peak counts as silence
BLOCK = 0.4  # seconds: the loudness meter's gating block
CEILING = 10 ** (-1 / 20)  # the highest peak a Line may reach, a little below full scale so it never clips
REACH = 0.01  # seconds either side of a peak over which the limiter turns the Line down and back up
# Every Reference Recording is stored at one sample rate: as high as any cloning Model hears (Qwen3-TTS Base hears 24 kHz,
# VoxCPM2 16 kHz), so storing more would keep nothing a Model uses.
REFERENCE_SAMPLE_RATE = 24_000
# Passages are cut at the rate Qwen3-ASR and Qwen3-ForcedAligner hear at, at most PASSAGE_MAX seconds long, since the
# aligner times at most five minutes at once; each cut is at the quietest QUIET_SPAN in the PASSAGE_SEARCH seconds
# before the limit (ADR 0011).
MEDIA_SAMPLE_RATE = 16_000
PASSAGE_MAX = 300
PASSAGE_SEARCH = 60
QUIET_SPAN = 0.1
# A Line given a Rate is time-stretched in frames of about STRETCH_FRAME seconds, as ffmpeg's atempo does, each taken from
# within STRETCH_SEARCH seconds of where the rate puts it, which spans a period of even a low voice.
STRETCH_FRAME = 1 / 24
STRETCH_SEARCH = 0.01
UNREADABLE_MEDIA_HINT = ("Pass an audio or video file. voxx decodes WAV, MP3 and FLAC itself, and other formats, "
                         "video included, with ffmpeg")


def finish(samples, sample_rate):
    """The same loudness and the same short silences for every Line, at the Engine's native sample rate.
    Returns the samples and the Line's warnings."""
    if samples.ndim != 1:
        # Trimming pads every axis: a [samples, channels] Line would grow to gigabytes before anything noticed.
        raise VoxxError("engine_not_mono", f"The Engine returned audio shaped {samples.shape}, not one channel.",
                        BUG_HINT, {"shape": list(samples.shape)})
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


def stretch(samples, sample_rate, rate):
    """The samples played `rate` times as fast at the same pitch, about len(samples) / rate long: WSOLA, as ffmpeg's
    atempo. Hann frames at 50% overlap are laid one after another, each read from where it best continues the frame
    before it, by cross-correlation, within STRETCH_SEARCH of where the rate puts it in the input, so the read position
    never drifts from the rate."""
    size = round(sample_rate * STRETCH_FRAME) // 2 * 2
    hop, search = size // 2, round(sample_rate * STRETCH_SEARCH)
    window = hann(size, sym=False)
    # Silence around the input, so every frame and every place it is searched for lies inside it.
    padded = np.concatenate([np.zeros(search), samples.astype(np.float64), np.zeros(2 * size + search)])
    length = round(len(samples) / rate)
    stretched = np.zeros(length + size)
    read = None
    for start in range(0, length, hop):
        nominal = min(round(start * rate) + search, len(padded) - size - search)
        if read is not None:
            # The input that would have come next after the frame before, and where near nominal it is most alike.
            following = padded[read + hop:read + hop + size]
            region = padded[nominal - search:nominal + search + size]
            # Of the places most alike, the one nearest nominal: in silence every place is alike.
            likeness = correlate(region, following, mode="valid")
            offsets = np.flatnonzero(likeness == likeness.max()) - search
            nominal += int(offsets[np.argmin(np.abs(offsets))])
        read = nominal
        stretched[start:start + size] += padded[read:read + size] * window
    return stretched[:length]


def prepare_reference(source, path):
    """Normalizes the Reference Recording at `source` into a WAV at `path`, as a Line is finished: mono, at
    REFERENCE_SAMPLE_RATE, at the same loudness and with the same short silences. Returns its warnings."""
    # mlx-audio's reader decodes WAV, MP3 and FLAC itself, and M4A, Ogg, AIFF and more through ffmpeg if installed.
    from mlx_audio.audio_io import read

    try:
        samples, sample_rate = read(str(source), always_2d=True, dtype="float64")
    except Exception as e:
        raise VoxxError("unreadable_reference", f"Cannot decode {source}: {type(e).__name__}: {e}",
                        "Pass a WAV, MP3 or FLAC file to --ref, or install ffmpeg for other formats.",
                        {"ref": str(source)}, USAGE)
    samples = samples.mean(axis=1)
    if not len(samples):
        raise VoxxError("silent_reference", f"{source} has no audio.", "Pass a recording of the voice to --ref.",
                        {"ref": str(source)}, USAGE)
    gcd = math.gcd(REFERENCE_SAMPLE_RATE, sample_rate)
    samples, found = finish(resample_poly(samples, REFERENCE_SAMPLE_RATE // gcd, sample_rate // gcd), REFERENCE_SAMPLE_RATE)
    if any(w["code"] == "silent" for w in found):
        raise VoxxError("silent_reference", f"{source} is silent.", "Pass a recording of the voice to --ref.",
                        {"ref": str(source)}, USAGE)
    write_wav(path, samples, REFERENCE_SAMPLE_RATE)
    return found


def split_media(source, directory):
    """Decodes the Media File at `source` and writes its Passages into `directory` as passage-<n>.wav. Returns its
    duration and each Passage's path, start and end, in seconds."""
    samples = _read_media(source)
    if not len(samples):
        raise VoxxError("silent_media", f"{source} has no audio.", "Pass a file with speech in it.",
                        {"media": str(source)}, USAGE)
    passages = []
    for number, (start, end) in enumerate(passage_bounds(samples, MEDIA_SAMPLE_RATE), start=1):
        path = directory / f"passage-{number}.wav"
        write_wav(path, samples[start:end], MEDIA_SAMPLE_RATE)
        passages.append({"path": str(path), "start": round(start / MEDIA_SAMPLE_RATE, 3),
                         "end": round(end / MEDIA_SAMPLE_RATE, 3)})
    return {"duration": round(len(samples) / MEDIA_SAMPLE_RATE, 3), "passages": passages}


def passage_bounds(samples, sample_rate):
    """[start, end) of each Passage, in samples: contiguous, covering every sample, none longer than PASSAGE_MAX."""
    limit, search, span = PASSAGE_MAX * sample_rate, PASSAGE_SEARCH * sample_rate, round(QUIET_SPAN * sample_rate)
    bounds, start = [], 0
    while len(samples) - start > limit:
        searched = samples[start + limit - search:start + limit].astype(np.float64)
        cut = start + limit - search + int(np.argmin(uniform_filter1d(searched**2, span, mode="nearest")))
        bounds.append((start, cut))
        start = cut
    return bounds + [(start, len(samples))]


def _read_media(source):
    """Mono float32 samples at MEDIA_SAMPLE_RATE: through mlx-audio's reader, else ffmpeg for what it cannot decode."""
    from mlx_audio.audio_io import read

    try:
        samples, _ = read(str(source), dtype="float32", sample_rate=MEDIA_SAMPLE_RATE, nchannels=1)
        return np.asarray(samples, dtype=np.float32).reshape(-1)
    except Exception as e:
        failure = f"{type(e).__name__}: {e}"
    ffmpeg = shutil.which("ffmpeg")
    if ffmpeg is None:
        raise VoxxError("unreadable_media", f"Cannot decode {source}: {failure}",
                        UNREADABLE_MEDIA_HINT + ", which is not installed: install it, such as with `brew install ffmpeg`.",
                        {"media": str(source)}, USAGE)
    decoded = subprocess.run([ffmpeg, "-nostdin", "-loglevel", "error", "-i", str(source), "-vn", "-f", "s16le", "-ac", "1",
                              "-ar", str(MEDIA_SAMPLE_RATE), "pipe:1"], capture_output=True)
    if decoded.returncode != 0:
        raise VoxxError("unreadable_media", f"Neither mlx-audio nor ffmpeg can decode {source}: "
                                            f"{decoded.stderr.decode(errors='replace').strip() or failure}",
                        UNREADABLE_MEDIA_HINT + "; ffmpeg could not decode this one either.", {"media": str(source)}, USAGE)
    return np.frombuffer(decoded.stdout, "<i2").astype(np.float32) / 32768


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
