# voxx also transcribes the speech in audio and video files, with `voxx transcribe`

voxx registered Qwen3-ASR and Qwen3-ForcedAligner only to check Lines and time their words, and DESIGN.md kept `transcribe` and `align` internal. But an agent working on a demo video also needs to read what is said in a recording or a video, such as a screen recording's voice-over or a meeting, and the Models, the install flow, the worker and its lock were all there already. So `voxx transcribe <media>` now prints the Transcript of any audio or video file: its text and its language, Passage by Passage; with `--words`, each word's start and end too. voxx now listens as well as speaks, and is still local, agent-only and CLI-only.

How it transcribes:

- **Passages of at most five minutes.** The worker decodes the Media File to mono 16 kHz (mlx-audio's reader, else ffmpeg for formats it cannot decode, such as most video) and cuts it into Passages of at most 300 seconds, each cut at the quietest tenth of a second in the last 60 seconds before the limit. The forced aligner times at most five minutes of speech at once, so the same Passages serve both; Qwen3-ASR stays within its token budget, and progress comes Passage by Passage.
- **The language is detected unless `--language` names one.** Each Passage is transcribed, and with `--words` aligned, in its own language, so a recording that changes language keeps its words.
- **Word timings are opt-in.** As with `--check` (ADR 0008), the step that costs a second Model's memory runs only when asked for. A Passage in a language no aligner reads gets `not_aligned`, and a missing aligner gives one `aligner_not_installed` warning (ADR 0006).
- **Qwen3-ASR-1.7B is registered beside 0.6B.** It is the more accurate of the two (upstream reports the 1.7B as state of the art among open models) and Apache-2.0, at 2.5 GB. `transcribe` uses the installed transcribing Model that hears best, the 1.7B before the 0.6B, unless `--model` names one. The self-check and `voice add` keep using the 0.6B, so `narrate` holds no more memory than before.

## Considered options

- **A separate tool.** Rejected: it would repeat voxx's registry, install flow, worker and lock, and use the same Models.
- **Transcribe the whole file in one call.** Rejected: mlx-audio cuts at 20 minutes and caps the tokens of one call, the aligner stops at five minutes, and an hour-long file would report no progress.
- **Word timings by default.** Rejected: the aligner adds 1.3 GB of memory, and reading what is said needs only the text.
- **Japanese and Korean word timings.** Not now: mlx-audio splits their words with nagisa and soynlp, which voxx would have to install. Their Passages get `not_aligned`.

## Consequences

- A Transcript's Word Timings count from the start of the Media File, not of a Passage.
- The Passages' texts are joined with a space, but none between two East Asian full-width characters, so Chinese and Japanese text is not broken up.
- Qwen3-ASR names the language it heard in English; a name voxx has no BCP 47 tag for leaves the Passage's `language` null and the Passage unaligned.
