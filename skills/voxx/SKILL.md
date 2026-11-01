---
name: voxx
description: Voice a Narration locally with the voxx CLI: one WAV and word timings per Line, in a Preset Voice or a Cloned Voice, ready for `cuetake record --narration`. Use when a demo video or any other project needs spoken narration, voice-over or text-to-speech, or the user wants to clone a voice.
---

# voxx agent operating manual

voxx reads each Line of a Narration in one go with a local speech Model and hands back a WAV per Line, its word timings and a self-check. The CLI does what is deterministic; you make the judgment calls: language, Voice, `style`, whether a Line needs reading again, and asking the user before anything is downloaded. Run every command through `scripts/voxx` in this skill's folder; it launches the pinned voxx version with `uvx`, and this manual writes commands without that path. Read [setup.md](setup.md) when `uvx` is missing, `doctor` reports an unsupported platform, a command exits 3 or warns that a Model is not installed, or the user wants voxx removed. Read [cloning.md](cloning.md) before cloning a voice.

Every command prints one JSON object on stdout and NDJSON progress on stderr. `voxx schema` describes every command's arguments, the Narration file, the results, the warnings and the exit codes; it is the reference, so look things up there rather than guessing.

## Workflow

1. Run `doctor` and `schema`. `doctor` reports the platform, the installed Models and `$VOXX_HOME`; `narrate` itself never checks the platform, so a problem it would hit shows here first.
2. Settle the language. Use the one the user names; otherwise the language of the video's audience; otherwise the language the user writes to you in. Write it as a BCP 47 tag in canonical case, exactly as the Model registers it (`voxx models`): Mandarin is `zh`. voxx never guesses `language` and never falls back from `en-US` to `en`.
3. Settle the Voice with the user ([Voices](#voices)).
4. Write the Narration file in the user's project ([Writing Lines](#writing-lines)).
5. Run `narrate <file> --out <dir>`. One run loads the Model once for every Line, so voice the whole Narration in one call. A long Narration takes minutes: run it in the background when your shell would time out.
6. Check every Line ([Checking each Line](#checking-each-line)) and read the ones that need it again with `--line`.
7. Deliver ([Delivering](#delivering)).

## Voices

The user chooses the Voice, since they will hear it and you cannot. Run `voxx voices` and list each Voice's name with its own short description, and the Models that read it; offer the Voices native to the Narration's language first. Once the user has chosen in a project, keep that Voice for every later Narration there without asking again. When they do not care, leave `voice` out: the Model then reads in its first Voice native to the language.

A Cloned Voice is listed by `voxx voices` beside the Preset Voices once it has been added; [cloning.md](cloning.md) covers adding one.

For a quick draft, pass `--model qwen3-tts-0.6b-customvoice`: the same Preset Voices, faster, but it ignores `style` (each Line says so in `warnings`). Voice the final take with the default Model by leaving `--model` out.

## Writing Lines

- One Line per beat of the video: a sentence or two the viewer hears while one thing happens on screen. Each Line is read in one breath and never stitched, so a Line is also the unit you read again.
- Write numbers, units, symbols and abbreviations the way they are spoken ("三步", "twenty percent"): the Models read the text as written. Punctuation shapes the delivery; end a Line with the punctuation its tone needs.
- `style` is a short natural-language instruction to the Model: the tone, the pace and who is being addressed, in a sentence, such as "Warm and relaxed, a little slower than usual, like showing a colleague a new feature". Set it once at the top of the Narration, and give a Line its own `style` only for the beat that needs a different delivery, such as an excited reveal. Cloned Voices and the fast tier ignore `style`.
- Pauses between Lines belong to CueTake: the Scenario decides when each `d.say(id)` starts. Keep pauses, ellipses and stage directions out of `text`, because every Line is trimmed to 50 ms of silence at each end.
- When the Narration goes to CueTake, give Lines ids of letters, digits, `.`, `-` and `_`, such as `intro` or `send-invite`: CueTake accepts only those, though voxx accepts more.

## Checking each Line

`narrate` transcribes every Line back and reports `transcript` and `error_rate` (per character in Chinese, Japanese and Korean, per word otherwise). voxx only reports; deciding is your job.

- **Read the `transcript` before the number.** In a short Line one wrong word or character already gives 0.1–0.2, and it is often the transcriber mishearing ("Press send" heard as "Press in") rather than the voice misreading. A Line whose transcript differs only where such a mishearing explains it is good.
- **A Line is bad** when the transcript has a sentence the text does not, says something else, or stops early, or when `error_rate` is near or above 1. Read only the bad Lines again: `narrate` into the same `--out` with `--line <id>` for each of them reads them with new seeds and leaves every other Line's file byte for byte as it was.
- **Read a Line again at most three times.** If it is still bad, stop and show the user its text and transcript. Offer to rewrite it, usually a product name, number or abbreviation spelled out as it is spoken, and tell them the Subtitles show the rewritten text.
- `not_checked` means no Model can transcribe this language, so the Line went unchecked: tell the user in a sentence and ask them to listen to it.
- `not_aligned` means the Line has no `words`, either because no Model times words in this language or because timing this Line failed. The audio is fine, and CueTake then spreads the Subtitles over the Line by character count. When timing failed on a Line in a language other Lines were timed in, reading it again may fix it.
- `aligner_not_installed` or `checker_not_installed` means a Model that adds word timings or the check is missing. The audio is usable as it is. Ask the user whether to install it, as [setup.md](setup.md) describes. Once it is installed, run `narrate <dir>/narration.json --out <dir>` with the same `--model`: the completed Narration carries each Line's seed, so the audio comes out the same and gains `words` and the check.
- `stale_audio` after `--line` means a kept Line's audio no longer matches the Narration: its text, Voice, `style` or the language changed since it was read. Read that Line again too.

## Errors

The error's `hint` says what to do, and `schema` lists every exit code. Two need the user:

- **Exit 3, `model_not_installed`**: nothing was downloaded. Tell the user, from `details`, each missing Model's id, size, license and license link exactly as given, and the total. Run `voxx install <model>` only after they agree; follow [setup.md](setup.md).
- **Exit 4, `unsupported_language`**: pick from `details.languages` the tag that matches the language and accent the user asked for, and write it into the Narration. If none matches, tell the user this Model cannot read that language; substituting a related language is the user's call, not yours.

## Delivering

Give the user the absolute path of `<out>/narration.json` and one line per warning that is still open. For CueTake, pass that file to `cuetake record --narration`; it already has the shape CueTake reads, with `audio`, and `words` for the Subtitles.

Remind the user, every time you deliver, that this is AI-generated speech: many platforms require a video with it to be labeled as AI-generated content when it is published. With a Cloned Voice, the user is responsible for having the right to use that voice.
