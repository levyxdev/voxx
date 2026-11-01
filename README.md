# voxx

**Local narration for AI agents.**

voxx is a text-to-speech CLI built only for agents. An agent writes a Narration, a list of Lines in one language, and `voxx narrate` reads each Line in one breath with a local speech Model, then hands back one WAV per Line with word timings and a self-check. The completed Narration file goes straight to [CueTake](https://github.com/levyxdev/cuetake) (`cuetake record --narration`), so a product demo can be recorded to fit its voice-over.

- Every Line is read whole by the Model, never stitched, then trimmed to 50 ms of silence at each end and normalized to -18 LUFS, as a mono WAV at the Model's native sample rate.
- Word timings for each Line (per character in Chinese), for Subtitles.
- A self-check: every Line is transcribed back and compared with its text, so the agent knows which Lines to read again with a new seed, leaving the others byte for byte as they were.
- Preset Voices, or a Cloned Voice made from a short Reference Recording.
- Only Models whose weights allow commercial use, run locally through [mlx-audio](https://github.com/Blaizzy/mlx-audio). Nothing is downloaded until the user agrees.
- Every command prints one JSON object, and `voxx schema` describes them all, so an agent never guesses.

voxx 0.1 runs on Apple Silicon Macs only.

## For AI agents

If a user hands you this repository to set up voxx:

1. Install the skill with `npx skills add levyxdev/voxx`. In Claude Code you can instead run `/plugin marketplace add levyxdev/voxx`, then `/plugin install voxx`.
2. The skill's `scripts/voxx` runs the pinned [`voxx`](https://pypi.org/project/voxx/) package with `uvx`, so nothing else needs installing besides [uv](https://docs.astral.sh/uv/). To run a source checkout instead, export `VOXX_BIN="uv run --project /absolute/path/to/voxx voxx"`.
3. Follow the [skill](skills/voxx/SKILL.md): run `scripts/voxx doctor`, and install uv or a Model only after the user agrees ([setup](skills/voxx/setup.md)).

## Example

[`examples/invite/narration.json`](examples/invite/narration.json) is a Narration as an agent writes it:

```json
{
  "language": "zh",
  "style": "语气亲切自然，语速适中，像在给同事演示一个新功能",
  "lines": [
    { "id": "intro", "text": "这是新的邀请流程，只要三步。" },
    { "id": "email", "text": "先填上同事的邮箱，再选好对方的角色。" },
    { "id": "send", "text": "点一下发送，邀请就发出去了！", "style": "语气轻快，带一点兴奋" }
  ]
}
```

`voxx narrate examples/invite/narration.json --out examples/invite/out` read it with the default Models into [`examples/invite/out/`](examples/invite/out/): a WAV per Line, and a `narration.json` that keeps every field above and adds each Line's `audio`, `words`, `model`, `voice`, `seed`, `sample_rate`, `transcript`, `error_rate` and `warnings`.

## Models

`voxx models` lists the registry. Each Model is pinned to one upstream revision, and its weights license was checked against the upstream model card on 2026-10-30. Only Models whose weights allow commercial use are registered.

| Model | Used for | Download | Weights license |
| --- | --- | --- | --- |
| `qwen3-tts-1.7b-customvoice` | Preset Voices (default) | 3.1 GB | [Apache-2.0](https://huggingface.co/Qwen/Qwen3-TTS-12Hz-1.7B-CustomVoice) |
| `qwen3-tts-0.6b-customvoice` | Preset Voices, fast drafts | 2.0 GB | [Apache-2.0](https://huggingface.co/Qwen/Qwen3-TTS-12Hz-0.6B-CustomVoice) |
| `voxcpm2` | Cloned Voices (default) | 3.2 GB | [Apache-2.0](https://huggingface.co/openbmb/VoxCPM2) |
| `qwen3-tts-1.7b-base` | Cloned Voices | 3.1 GB | [Apache-2.0](https://huggingface.co/Qwen/Qwen3-TTS-12Hz-1.7B-Base) |
| `qwen3-forcedaligner-0.6b` | Word timings | 1.3 GB | [Apache-2.0](https://huggingface.co/Qwen/Qwen3-ForcedAligner-0.6B) |
| `qwen3-asr-0.6b` | Self-check, Reference Recording text | 1.0 GB | [Apache-2.0](https://huggingface.co/Qwen/Qwen3-ASR-0.6B) |

Only the Model that reads must be installed; without the aligner or the transcriber, Lines are read without word timings or the self-check. `voxx install <model>` is the only command that downloads anything ([ADR 0003](docs/adr/0003-models-are-installed-only-by-an-explicit-command.md)). It fetches the 8-bit MLX conversions from Hugging Face into `~/.voxx/models` (or `$VOXX_HOME/models`), and honors `HF_ENDPOINT` for a mirror.

## Disclaimer

- **You are responsible for the voices you clone.** voxx cannot tell whose voice a Reference Recording is, and does not check consent or add a watermark ([ADR 0004](docs/adr/0004-cloning-does-not-check-consent.md)). Clone only your own voice, or a voice whose owner has agreed to it, and follow the laws where you publish.
- **voxx distributes no model weights.** `voxx install` downloads them from their publishers' Hugging Face repositories only when you run it. Each Model stays under its own license, which voxx shows before you install it. The licenses in the registry were checked on the date shown; check the license yourself before you rely on it.
- **Label AI-generated speech.** Many platforms and jurisdictions require content with synthetic speech to be labeled as AI-generated when it is published. voxx records the Model, Voice and seed of every Line in its output.
- voxx is provided as is, without warranty of any kind, under the [Apache License 2.0](LICENSE). The third-party projects it builds on are listed in [NOTICE](NOTICE).

## Run from source

Requirements: an Apple Silicon Mac and [uv](https://docs.astral.sh/uv/).

```sh
uv sync
uv run voxx doctor
uv run voxx schema
```

## Development

```sh
uv run basedpyright
uv run pytest
# With the Models installed:
VOXX_TEST_REAL=1 uv run pytest tests/test_real_models.py
```

The tests run `voxx` as a process, the way an agent does, against a fake Engine and a local stand-in for Hugging Face, so they need no Model and never reach Hugging Face. The design is in [docs/DESIGN.md](docs/DESIGN.md), the terms in [GLOSSARY.md](GLOSSARY.md), the decisions in [docs/adr/](docs/adr/), and the release steps in [docs/releasing.md](docs/releasing.md).
