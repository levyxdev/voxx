# Every Line and Design Take audio file has a name of its own

A Line's audio was `<id>.wav` and a Design Take's `take-<n>.wav`. Reading a Line again overwrote its file, and two runs, such as one per Model or two design rounds, wrote files of the same name, which a user handed them in a conversation cannot tell apart (levyxdev/voxx#50). Each such file now ends in the local time its run started, to the second, with the UTC offset: `intro-20261127-182201+0800.wav`, `take-1-20261127-182201+0800.wav`. A run reads the clock once it holds the lock of ADR 0009 and takes a later second than the last run under the same `$VOXX_HOME` did, so no two of its runs share a time; when two start within one second, the later one's name is a second ahead of the clock. voxx never deletes an earlier file: the Narration or `design.json` names the one that counts.

## Considered options

- **A number per `--out`** (`intro-2.wav`): rejected, since runs into separate `--out`s still write the same names.
- **A random suffix**: unique, but tells neither the order of the runs nor which files were read together.
- **Keep the names and have the skill copy each file under a telling name before sending it**: rejected, since every agent would have to repeat it, and a host that only shows paths still loses the overwritten audio.

## Consequences

- `--out` keeps files no Narration names any more; deleting them is the user's call.
- A Line id may be 21 bytes shorter than before, the length of the suffix.
