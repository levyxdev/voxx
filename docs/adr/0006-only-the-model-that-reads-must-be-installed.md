# Only a missing Model needed to read fails; a missing helper Model degrades to a warning

2026-11-09: the transcription self-check now runs only with `--check` ([ADR 0008](0008-the-self-check-is-opt-in.md)); without it, a missing transcription Model gives no warning either.

ADR 0003 says a command fails as "not installed" when a Model is missing. `narrate` first applied that to every Model a Line uses: if any of the reading Model, the alignment Model or the transcription Model was missing, the whole run failed with exit code 3. But the three are not equal: the reading Model makes the audio, and without it nothing works; the alignment Model only makes `words`, and the transcription Model only makes the quality report `transcript` and `error_rate`; without them the audio is still usable. So now only a missing reading Model fails, with `model_not_installed`; when the alignment or transcription Model is missing, each Line is read as usual, just without those fields, each with an `aligner_not_installed` or `checker_not_installed` warning whose details give that Model's id, size, license and install command. So a user can use voxx with just one TTS Model installed, and the agent still has enough to ask the user whether to install the rest.

## Considered options

- **Keep them all required.** Rejected: a first use of voxx would need three Models downloaded, two of which are only nice-to-haves for many uses (no subtitles needed, or the user listens anyway).
- **Report a missing helper Model once, at the result's top level.** Rejected: the warning and the missing field both sit on the Line, so an agent judging Line by Line need not look elsewhere; a Line re-voiced with `--line` naturally carries its own warning too.

## Consequences

- These warning codes are separate from `not_aligned`/`not_checked`, meaning no Model exists for the language: installing nothing can fix the latter, while the former is fixed by installing one Model and re-voicing with `--line`.
- The rule looks only at whether the step can go on. `voice add` without Reference Recording text needs the transcription Model to fill in the text, and that step cannot go on without it, so there the transcription Model is still required.
