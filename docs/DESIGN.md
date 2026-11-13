# voxx v0.1 design

> Status: grilled and settled (2026-10-30). Terms are in [GLOSSARY.md](../GLOSSARY.md), key decisions in [docs/adr/](adr/), the model survey in [research/tts-models-2026-10.md](research/tts-models-2026-10.md). Next: `/to-spec` → `/to-tickets`.

## In one sentence

voxx is a local voice CLI plus a skill, **for agents only**: an agent hands it a Narration, it reads each Line in one continuous take, and returns one audio file per Line plus word timings. Its main use is voicing CueTake screen recordings: the voice-over comes first, the screen is recorded to it, and the picture follows the sound.

## Core principle: what is deterministic is fixed in the CLI, judgement goes to the agent

| Fixed in the CLI (the same input always gives the same result) | Left to the agent (guided by the skill) |
|---|---|
| Model registry, licenses, mapping tasks to checkpoints | Choosing the Model and Voice, writing `style` |
| Synthesis, loudness normalization, silence trimming, forced alignment, self-check scoring | Reading the error rate to decide whether to re-voice with another seed |
| The Narration file format, JSON output, exit codes | Telling the user the size and license before a download, and waiting for their consent |
| No implicit downloads, no stitching audio inside a Line | Before cloning, reminding the user to confirm they may use the voice; at publication, reminding them to disclose it is AI-generated |
| | How long to pause between Lines (set in CueTake's Scenario) |

## Relation to CueTake

```
agent writes the Narration ──► voxx narrate ──► Narration file (audio + words filled in) + one WAV per Line
                                                        │
                                                        ▼
                                        cuetake record --narration <file>
```

The two tools hand over only through files and never call each other ([ADR 0001](adr/0001-narration-file-is-the-contract.md)). The Narration format matches levyxdev/cuetake#7, but voxx defines it itself, and its code does not depend on CueTake.

## The Narration file

Input:

```json
{
  "language": "zh",
  "voice": "my-voice",
  "style": "语气轻松，语速稍慢",
  "lines": [
    { "id": "intro", "text": "这是一个新的发送流程。" },
    { "id": "send",  "text": "点一下发送就完成了。", "style": "语气兴奋" }
  ]
}
```

- `language`: a BCP 47 tag in canonical case (such as zh, yue, en-US), one language per Narration, which must exactly match a language the Model registers (ADR 0005). Which languages work follows the Model that reads it (Qwen3-TTS supports zh, en, ja, ko, fr, de, it, pt, ru, es); voxx sets no limit of its own, and exits 4 when the Model does not read the language.
- `voice`, `style` and `seed` at the top level hold for every Line, and a single Line can override them. `style` is natural language, passed to the Model as its instruct. With a Cloned Voice or Designed Voice, VoxCPM2 reads a Line with `style` from the Reference Recording alone, which sounds less like the voice, so each Line that takes `style` from the top level warns `style_weakens_clone`. A Model without `style` support (Qwen3-TTS Base, Ming-3.0-tts) still reads the Line and only says in its `warnings` that it ignored `style`.
- The four Delivery Controls are also top-level defaults with Line overrides: `emotion` (happy, sad, angry, fearful, disgusted, surprised, neutral), `speed` (slow, medium, fast), `pitch` and `volume` (both low, medium, high). Only Ming-3.0-tts follows them: voxx translates the values into Ming's Chinese values and joins them with the Preset Voice into the caption Ming reads (a JSON string); when cloning it also needs an all-zero speaker embedding, or short Lines often come out as a fraction of a second of noise. Ming does not follow `style` (with a Preset Voice or a Reference Recording the voice holds, but `style` has no effect, measured in levyxdev/voxx#33), so it ignores it with a warning. Other Models still read the Line, and list what they ignored under `controls_ignored` in `warnings`. A Line is still normalized to -18 LUFS at the end, so `volume` cannot change loudness. Measured (levyxdev/voxx#33): emotion is the clearest; speed differs by only 5% to 20%, less when combined with emotion; pitch shows a little only in Chinese; volume shows no measurable difference.
- Without `voice` on the Line or the Narration, the Default Voice of the language is used, if the user set one; else the Model's first Voice native to the language (vivian for Chinese, ryan for English), or its first Voice if none is.
- Without `seed`, voxx picks one at random for the whole run and reads every Line with it: a seed per Line made the Lines of one Voice sound like different speakers (levyxdev/voxx#44). The seed is set again before each Line is synthesized, so the same Model, Voice, `style`, text and seed give a byte-identical WAV on the same machine (verified by the real-model tests), independent of the order of the Lines. Feeding the output Narration file back as input with the same `--model` reproduces the previous run (the input ignores `model` on a Line).

On output each Line gains: `audio`, `words` (`[{ text, start, end }]`, relative to the start of the Line's audio; per character for Chinese), `model`, `voice`, `seed`, `sample_rate`, the self-check error rate, and `warnings`.

## Commands

```
voxx narrate <narration.json> --out <dir> [--model <id>] [--line <id>...]   # voice a whole Narration; --model picks the Model that reads it; --line re-voices only those Lines
voxx voice add <name> --ref <recording> [--ref-text <text>] [--model <id>] [--overwrite]   # store a Cloned Voice
voxx voice design --describe <description>... --text <sample text> --language <tag> --out <dir> [--takes <n>] [--model <id>]   # make Design Takes from descriptions for the user to choose from
voxx voice add <name> --from-design <dir> --take <n> [--model <id>] [--overwrite]   # store the chosen Design Take as a Designed Voice
voxx voices [--model <id>] [--language <tag>]   # list Preset, Cloned and Designed Voices, with the languages each is the Default Voice of
voxx voice default (<name> | --clear) --language <tag>   # set or clear the Default Voice of a language
voxx models                                                   # the registry (commercially usable Models only)
voxx install <model>                                          # the only command that downloads, Extra Repos included
voxx doctor                                                   # platform, installed Models, disk
voxx schema                                                   # every command's arguments and result shape
```

`align`, `transcribe` and `batch` are not exposed: they are only internal steps of `narrate`.

## How one Narration is processed

1. The CLI validates the Narration file, confirms the Models it needs are installed, then starts the worker.
2. The worker loads the Models once.
3. Line by Line: synthesize the whole Line in one take → trim leading and trailing silence to 50 ms → normalize loudness to -18 LUFS, with a limiter holding down any instant peaking above -1 dBFS (warning if it still misses by 0.5 LU or more) → force-align to get `words` (on failure, no `words`, only a warning) → with `--check`, transcribe it back with ASR to compute the error rate (off by default, [ADR 0008](adr/0008-the-self-check-is-opt-in.md)) → write a mono WAV (at the Model's native sample rate).
4. The worker exits, the CLI writes the completed Narration file and prints one JSON result to stdout.

## CLI and worker

The agent only ever runs the `voxx` CLI and never sees the worker.

- The CLI is light: it parses arguments, reads the registry and the Narration file, manages Voices and prints JSON. It does not import mlx, so commands like `models` and `schema` return at once.
- To synthesize, the CLI starts `python -m voxx.worker` as a **subprocess** and exchanges JSON-RPC messages over its stdin/stdout ("load the Model", "synthesize this Line", "align this Line", …), with stderr relaying progress.
- Once the Narration is read, the worker exits and the memory its Models held is released. When the worker crashes (say, out of GPU memory), the CLI can still return a structured JSON error to the agent.
- Workers take turns: before starting one, the CLI takes a lock under `$VOXX_HOME` and holds it until the worker exits, so a second `narrate`, `voice design` or `voice add` waits, with a `waiting` event naming the command and PID it waits for. Two runs side by side share one GPU, so they finish little sooner, and once their Models outgrow memory the Mac swaps and both slow down several times over ([ADR 0009](adr/0009-one-model-run-at-a-time.md)).

JSON-RPC over stdio is the same transport MCP and LSP use, but here it is only a private pipe between voxx's two halves, not an interface for agents. The agent's interface is the CLI alone; like CueTake, voxx does no MCP. The decision is in [ADR 0002](adr/0002-synthesis-runs-in-a-worker-process.md).

In v0.1 the worker and the CLI share one Python environment. When the first Engine with conflicting dependencies arrives (say, the official PyTorch-based CosyVoice package), it gets a venv of its own, with the protocol unchanged.

## Models

Only Models whose weight license allows commercial use are registered ([ADR 0003](adr/0003-models-are-installed-only-by-an-explicit-command.md)), all as mlx 8-bit, run through mlx-audio:

| Use | Model |
|---|---|
| Preset Voice (default) | Qwen3-TTS-12Hz-1.7B-CustomVoice |
| Cloned Voice and Designed Voice (default), voice design | VoxCPM2 |
| Cloned Voice (for comparison) | Qwen3-TTS-12Hz-1.7B-Base |
| Preset Voice, Cloned Voice, voice design, Delivery Control | Ming-3.0-tts-0.5B (levyxdev/voxx#33) |
| Voice design (10 languages) | Qwen3-TTS-12Hz-1.7B-VoiceDesign (levyxdev/voxx#36) |
| Forced alignment | Qwen3-ForcedAligner-0.6B |
| Self-check transcription, filling in Reference Recording text | Qwen3-ASR-0.6B |

There is no third-party evaluation of how Chinese sounds; the defaults get adjusted after real listening. The reasons and data are in the survey.

## Voices

- A Preset Voice is chosen by name from the Voices a Model ships with. `voxx voices` lists each Voice's native language, the one-line upstream description and the Models that can read it, so the agent can have the user choose. All 9 Qwen3-TTS CustomVoice Voices are registered, read by the default 1.7B. Ming-3.0-tts's 241 Voices are copied from the upstream cookbook (commit `9332fb9`): the 3 starting with `US_` or `UK_` are English, the rest Chinese, and each emotion-suffixed variant counts as one. For a Model with more than 20 Voices, the default `voxx voices` output carries only a one-line summary under `unlisted` (the count and the command that lists them all); `--model` lists all its Voices, and `--language` keeps only those native to that language.
- A Cloned Voice is stored before use: `voice add` normalizes the Reference Recording (mono, 24 kHz, -18 LUFS, 50 ms of leading and trailing silence), fills in its text (without `--ref-text`, Qwen3-ASR transcribes it, and must then be installed) and stores it as a named Voice; a Narration refers to it as `voice: "<name>"`. It is stored in `$VOXX_HOME/voices/`, the one place every project finds it ([ADR 0010](adr/0010-voices-live-only-under-voxx-home.md)). `voice.json` records the cloning Model `voice add --model` chose (VoxCPM2 by default); `narrate` reads with it by default, and `narrate --model` can switch to another cloning Model. VoxCPM2 follows `style`: a Line with `style` takes only the voice from the Reference Recording and passes `style` as the instruct, no longer continuing from the Reference Recording (continuing would read `style` aloud as text), so it may sound less alike; a Line without `style` continues as before and clones closest. Qwen3-TTS Base takes no instruct, so it ignores `style` and says so in `warnings`. Ming-3.0-tts also ignores `style`, but follows Delivery Controls.
- A Designed Voice takes two steps ([ADR 0007](adr/0007-designed-voice-is-fixed-by-a-chosen-take.md)): `voice design` makes `--takes` Design Takes per description, all reading the same sample text, writes them into `--out` as take-<n>.wav and design.json, and transcribes them back for a self-check like Lines; once the user chooses, `voice add --from-design <dir> --take <n>` stores that Design Take as the Reference Recording, with the sample text as its text, and `voice.json` records `kind: "designed"` and the description. From then on a cloning Model reads it like a Cloned Voice, in any language. Descriptions name traits only and point at no real person, which the skill enforces (ADR 0004).
- A Default Voice is the Voice a Line is read in when neither it nor its Narration names one: at most one per language, stored in `$VOXX_HOME/default-voices.json` and set with `voice default <name> --language <tag>`, which first checks that a Model reads that Voice in that language. The order is the Line's `voice`, the Narration's `voice`, the Default Voice of the language, then the Model's first Voice native to it. A Default Voice that cannot be read, such as under a `--model` that cannot read it or after its directory is removed, fails like a Voice the Narration names, with `details.default_voice`; voxx never swaps in another Voice. The completed Narration records each Line's `voice`, so reading it again gives the same Voice whatever the default is by then.
- The code checks no consent; users answer for the voices they clone, and README carries a disclaimer ([ADR 0004](adr/0004-cloning-does-not-check-consent.md)). No watermark is added.

## CLI contract

- stdout is always one JSON object: `{"ok": true, "data": {...}}` or `{"ok": false, "error": {"code", "message", "hint", "details"}}`.
- stderr carries NDJSON progress. No colors, tables or interactive prompts.

| Exit code | Meaning | What the agent should do |
|---|---|---|
| 0 | Success | — |
| 1 | Internal error | Report it |
| 2 | Bad arguments | Fix the arguments |
| 3 | Model not installed | Tell the user the size and license, and after their consent run `voxx install` |
| 4 | Model lacks the Capability | Switch Models |

## Storage

```
$VOXX_HOME (default ~/.voxx)
  models/            # Model files
  voices/<name>/     # voice.json (kind, source, reference text, the cloning Model that reads it, the Model that transcribed it, creation time; a Designed Voice adds the description, the Model that designed it, the take and the seed) + reference.wav (the normalized Reference Recording)
```

## Platform and distribution

- v0.1 supports only Apple Silicon Macs.
- Written in Python, published to PyPI as `voxx`. A one-line launcher in the skill runs `uvx voxx@<pinned version>`, and the skill and the CLI are released from the same tag.
- The project is Apache-2.0; it distributes no weights, and the upstream projects it depends on are in `NOTICE`.

## Open / later

- **Pronunciation**: what to do when a Model misreads a product name or an abbreviation. The candidate is a pronunciation dictionary plus inline `{text|reading}` marks, replaced in the text before synthesis (the Line is still read in one take), with word timings mapped back to the original text. Try it out before deciding.
- Numeric speed, a resident service mode, a venv per Engine, Linux/CUDA, CosyVoice3.
