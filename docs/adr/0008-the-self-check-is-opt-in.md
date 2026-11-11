# The transcription self-check is off by default and runs with `--check`

`narrate` and `voice design` first transcribed every Line and every Design Take back with Qwen3-ASR to compute `transcript` and `error_rate`. That step keeps the transcription Model in the worker beside the reading Model and the alignment Model: one `narrate` peaks around 5.7 GB, which runs out of memory on a 16 GB Mac alongside other programs, and every Line costs one more transcription. And the user listens anyway: a machine transcription only tells whether the words were read right, not whether it sounds good, and the transcription itself mishears ("Press send" heard as "Press in"). So now nothing is transcribed by default: Lines and Design Takes carry no `transcript` or `error_rate`, and there is no warning for a missing transcription Model or for a language with none; `--check` transcribes as before, and a missing transcription Model degrades to a warning per ADR 0006.

## Considered options

- **Keep transcribing by default.** Rejected: it costs about 1 GB more memory and one transcription per Line, for a verdict the user reaches by listening anyway.
- **Drop the transcription self-check.** Rejected: when the user cannot easily listen to each Line (many Lines, unattended re-voicing), `error_rate` is still the agent's only way to find the misread Lines.

## Consequences

- The skill now has the user listen; the agent passes `--check` only when the user asks for a check or will not listen to each Line.
- `voice add` without `--ref-text` still uses the transcription Model to fill in the Reference Recording's text: that step cannot go on without text, and it has nothing to do with the self-check.
- The alignment Model still runs by default: `words` is for subtitles, not for checking.
