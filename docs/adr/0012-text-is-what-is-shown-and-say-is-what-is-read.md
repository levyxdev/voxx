# A Line's text is what is shown; `say` respells what is read

A Line had one `text`, read by the Model and shown by CueTake as the subtitle, so text rewritten to be read right (a product name spelled as it sounds, a Chinese character with two readings swapped for a homophone) showed in the subtitles too (levyxdev/voxx#46). Now `text` stays what is shown, and `say`, at the top of the Narration and on a Line, maps text as shown to text as read: a Respelling. Only the Model's synthesis gets the respelled text. The aligner always gets `text`, so `words` spell out what is shown, and the self-check compares the transcript with `text`.

Aligning `text` rather than the text as read needs no mapping back, and works: in a test with VoxCPM2 and Qwen3-ForcedAligner, aligning the shown text against audio read from a Respelling timed it as well as aligning the text as read, and better for pinyin, where aligning the text as read gave some words no length at all.

## Considered options

- **A `display` field, with `text` as what is read**, as the issue proposed. Rejected: the Narration is the contract voxx shares with CueTake (ADR 0001), so CueTake would have to read a new field, and every existing Narration would change meaning.
- **One whole-Line `say` string beside `text`.** Not needed: a Line's `say` can map its whole text, and a map at the top of the Narration already holds the Respellings of every Line.
- **Markup inside `text`**, such as `[CueTake](Q Take)`. Rejected: it collides with literal brackets, and the same word has to be marked on every Line.
- **Pinyin or other per-Model pronunciation marks.** Rejected (levyxdev/voxx#45): only VoxCPM2 follows `{gan4}`, and only partly; Ming reads it aloud. A homophone that has only the intended reading is plain text and reads right on every Model.

## Consequences

- The respelling is applied left to right, the longest matching key first, and what a key is respelled as is never respelled again, so the order of `say`'s entries does not matter.
- A respelled Line's completed form records what it was read as (`respelled`), so a Line kept by `--line` is warned `stale_audio` when its respelled text changed, even if `text` did not, and stays warned on later runs.
- Respellings live only in the Narration, not under `$VOXX_HOME`, so a Narration still reads the same on any machine.
