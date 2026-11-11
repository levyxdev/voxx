# The Narration file is voxx's only input and output contract

One voxx call voices a whole Narration: it reads `{ language, lines: [{ id, text }] }`, writes one audio file per Line, then writes back the same Narration file with `audio` and `words` filled in. The format matches CueTake's Narration (levyxdev/cuetake#7), so an agent can hand voxx's output straight to `cuetake record --narration`; the two tools hand over only through files, never call each other, and run no resident service. voxx defines the format itself, and its code does not depend on CueTake.

## Considered options

- **One CLI call per Line.** Rejected: every call reloads several GB of Model, so a Narration of a dozen Lines takes minutes longer.
- **A resident service (HTTP or `serve --stdio`).** Not in v0.1: every caller is an agent, one call per Narration already loads the Model only once, and managing a resident process's lifecycle is not worth it.
- **Exposing atomic commands such as `align`, `transcribe` and `batch`.** Rejected: forced alignment, speech recognition and batch synthesis are only internal steps of voicing a Narration.

## Consequences

- Changing a field of the Narration file has to consider CueTake too: it is a cross-repo change.
- Re-voicing a single Line goes through the same file: given Line ids, only those Lines are regenerated, and the other Lines' audio is left alone.
- A Line is always read by the Model in one continuous take, never stitched together inside the Line, so it sounds like a person speaking.
