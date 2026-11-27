---
name: voxx
description: "Voice a Narration locally with the voxx CLI: one WAV and word timings per Line, in a Preset Voice, a Cloned Voice or a Designed Voice, ready for `cuetake record --narration`; or transcribe what is said in a local audio or video file. Use when a demo video or any other project needs spoken narration, voice-over or text-to-speech, the user wants to clone or design a voice, or the user wants the words, or word timings, of a recording or video on their machine."
---

# voxx agent operating manual

voxx reads each Line of a Narration in one go with a local speech Model and hands back a WAV per Line and its word timings. The CLI does what is deterministic; you make the judgment calls: language, Voice, `style`, whether a Line needs reading again, and asking the user before anything is downloaded. Run every command through `scripts/voxx` in this skill's folder; it launches the pinned voxx version with `uvx`, and this manual writes commands without that path. Read [setup.md](setup.md) when `uvx` is missing, `doctor` reports an unsupported platform, a command exits 3 or warns that a Model is not installed, or the user wants voxx removed. Read [cloning.md](cloning.md) before cloning a voice, [designing.md](designing.md) before designing one, and [transcribing.md](transcribing.md) before transcribing an audio or video file.

Every command prints one JSON object on stdout and NDJSON progress on stderr. `voxx schema` describes every command's arguments, the Narration file, the results, the warnings and the exit codes; it is the reference, so look things up there rather than guessing.

## Workflow

1. Run `doctor` and `schema`. `doctor` reports the platform, the installed Models and `$VOXX_HOME`; `narrate` itself never checks the platform, so a problem it would hit shows here first.
2. Settle the language. Use the one the user names; otherwise the language of the video's audience; otherwise the language the user writes to you in. Write it as a BCP 47 tag in canonical case, exactly as the Model registers it (`voxx models`): Mandarin is `zh`. voxx never guesses `language` and never falls back from `en-US` to `en`.
3. Settle the Voice with the user ([Voices](#voices)).
4. Write the Narration file in the user's project ([Writing Lines](#writing-lines)).
5. Run `narrate <file> --out <dir>`. One run loads the Model once for every Line, so voice the whole Narration in one call. A long Narration takes minutes: run it in the background when your shell would time out. Run one `narrate`, `voice design` or `voice add` at a time: they take turns anyway, so starting several at once finishes no sooner. One that waits for its turn says so with a `waiting` event naming the command it waits for; it is not stuck.
6. Check every Line ([Checking each Line](#checking-each-line)) and read the ones that need it again with `--line`.
7. Deliver ([Delivering](#delivering)).

## Voices

The user chooses the Voice, since they will hear it and you cannot. First check `defaults` in `voxx voices`: when the Narration's language has a Default Voice there, the user has already chosen; leave `voice` out of the Narration and it is read in that Voice, without asking again. If its `kind` in `voxx voices` is cloned or designed, follow the `style` rule for those Voices in [Writing Lines](#writing-lines). Otherwise run `voxx voices` and list each Voice's name with its own short description, and the Models that read it; offer the Voices native to the Narration's language first. A Model with hundreds of Preset Voices, such as `ming-3.0-tts-0.5b`, shows up only in `unlisted`, as a count per language and the command that lists them; when the listed Voices do not suit the user, such as for an English female voice, run that command with `--language` to list only the ones native to the Narration's language. Once the user has chosen, ask whether to use that Voice for every later Narration in this language; if they agree, run `voxx voice default <name> --language <tag>`, which holds on this machine for every project, and leave `voice` out from then on. When they want a different Voice for one video only, name it as the Narration's `voice` instead: a Voice the Narration or a Line names always wins over the default. When they do not care, leave `voice` out: the Model then reads in its first Voice native to the language. A default `narrate` cannot read, such as one a `--model` cannot read or one since removed, fails with `details.default_voice`; tell the user and let them pick another default or `--clear` it.

A Cloned Voice or Designed Voice is listed by `voxx voices` beside the Preset Voices once it has been added; [cloning.md](cloning.md) covers cloning one. When the user wants a voice of their own but not their own voice, has no voice actor who agreed to be cloned, and no Preset Voice fits, offer to design one from a description: [designing.md](designing.md).

## Writing Lines

- One Line per beat of the video: a sentence or two the viewer hears while one thing happens on screen. Each Line is read in one breath and never stitched, so a Line is also the unit you read again. A passage that need not follow the screen, such as an opening or a closing, sounds more natural as one Line.
- Write numbers, units, symbols and abbreviations the way they are spoken ("三步", "twenty percent"): the Models read the text as written. Punctuation shapes the delivery; end a Line with the punctuation its tone needs.
- When a word must be written otherwise to be read right, such as a product name the Model misreads, keep `text` as the viewer should see it and put the respelling in `say`, from the text as shown to the text as read: `"say": {"CueTake": "Q Take"}`, at the top of the Narration for a word every Line may use. Only the Model reads the respelled text: `text`, `words`, the Subtitles and `--check` keep the text as written.
- In Chinese, a character with two readings (多音字) is often read with the wrong one, such as 调 in 调岗 or 干 in 该干干. As you write each Line, find the ones whose context leaves the reading open, and settle each with the first of these that works:
  1. Respell it in `say` with a homophone that has only the reading you mean: `{"调岗": "掉岗"}` for diào, `{"干干": "赣赣"}` for gàn. A homophone is plain text, so every Model reads it the same way.
  2. When no character has only that reading, such as gěi in 补给你, and the Narration is read by `voxcpm2`, respell it in `say` with pinyin: `{"补给你": "补{gei3}你"}`. Write the letters, then the tone as a digit from 1 to 4, or 5 for the neutral tone, with `v` for ü: `{ma5}`, `{lv3}`. Only `voxcpm2` follows pinyin, and not always right; Ming reads it aloud, so `narrate` refuses it for every other Model (`pinyin_unsupported`). Write pinyin only in `say`: `text` is what the Subtitles show.
  3. When another Model reads the Narration, or the user still hears the wrong reading, reword the Line so its context settles the reading, such as 补发给你 for 补给你, and take its pinyin out of `say`. The Subtitles show the new words, so show the user the Line as it is and as reworded, and change `text` only once they agree.

  A Line's reading is unsettled when you are unsure which reading its context calls for, or it uses pinyin: note those Lines, with the character and the reading meant.
- `style` is a short natural-language instruction to the Model: the tone, the pace and who is being addressed, in a sentence, such as "Warm and relaxed, a little slower than usual, like showing a colleague a new feature". With a Preset Voice, set it once at the top of the Narration. With a Cloned Voice or Designed Voice, leave it off the top: a Line with `style` sounds less like the voice, so the Lines drift apart. Either way, give a Line its own `style` only for the beat that needs a different delivery, such as an excited reveal. Qwen3-TTS Base ignores `style`.
- `emotion`, `speed`, `pitch` and `volume` ask for a delivery by value instead of in words; `voxx schema narrate` lists the values. Like `style`, set them at the top and override them on a Line. Only `ming-3.0-tts-0.5b` follows them, in a Preset Voice and in a Cloned or Designed Voice, and it ignores `style`, so with Ming use these instead; any other Model reads the Line without them and warns `controls_ignored`. With Ming, `emotion` is the strongest; `speed` is a nudge of 5 to 20 percent, and next to an `emotion` it moves even less; `pitch` moves a little, and in tests only in Chinese; `volume` made no difference anyone could measure, since every Line is brought to the same loudness anyway. Promise the user no more than that, and let them listen.
- When the Lines come out longer or shorter than the video needs, set `rate`: it works with every Model, where `speed` does not. Divide the length the Lines came out at by the length they must fit, such as 1.1 for 22 seconds that must fit in 20. Between 0.8 and 1.25 it sounds natural; beyond that, ask the user to listen. To keep the takes the user has heard, set `rate` in `<dir>/narration.json`, the completed Narration, and run `narrate <dir>/narration.json --out <dir>` with the same `--model`, reading every Line with the seed it carries.
- Pauses between Lines belong to CueTake: the Scenario decides when each `d.say(id)` starts. Keep pauses, ellipses and stage directions out of `text`, because every Line is trimmed to 50 ms of silence at each end.
- When the Narration goes to CueTake, give Lines ids of letters, digits, `.`, `-` and `_`, such as `intro` or `send-invite`: CueTake accepts only those, though voxx accepts more.

## Checking each Line

The user listens to the Lines: hand over each Line's audio ([Handing over audio](#handing-over-audio)), asking them to listen first to the Lines with an unsettled reading, for the character and the reading you noted, and read again with `--line <id>` the ones they want read again, then hand those over too. `narrate` reads them with new seeds and leaves every other Line's file byte for byte as it was.

`narrate --check` also transcribes every Line back and reports `transcript` and `error_rate` (per character in Chinese, Japanese and Korean, per word otherwise). It loads the transcriber beside the reading Model, which takes about 1 GB more memory and a few seconds more per Line, so pass it only when the user asks for the check or will not listen to every Line, such as for a long Narration. voxx only reports; deciding is your job.

- **Read the `transcript` before the number.** In a short Line one wrong word or character already gives 0.1–0.2, and it is often the transcriber mishearing ("Press send" heard as "Press in") rather than the voice misreading. A Line whose transcript differs only where such a mishearing explains it is good.
- **Leave a character's reading to the user's ear.** The transcriber writes the character its context calls for, whichever reading it heard: 干干 read as gān and as gàn both come back as 干干, at `error_rate` 0. A misreading shows only when the transcriber happens to write another character, such as 调岗 heard as 挑岗; respell that Line in `say` and read it again.
- **A Line is bad** when the transcript has a sentence the text does not, says something else, or stops early, or when `error_rate` is near or above 1. Read only the bad Lines again: `narrate` into the same `--out` with `--line <id>` for each of them reads them with new seeds and leaves every other Line's file byte for byte as it was.
- **Read a Line again at most three times.** If it is still bad, stop and show the user its text and transcript. Offer to respell it in `say`, usually a product name, number or abbreviation spelled out as it is spoken.
- `not_checked`, with `--check`, means no Model can transcribe this language, so the Line went unchecked: tell the user in a sentence and ask them to listen to it.
- `not_aligned` means the Line has no `words`, either because no Model times words in this language or because timing this Line failed. The audio is fine, and CueTake then spreads the Subtitles over the Line by character count. When timing failed on a Line in a language other Lines were timed in, reading it again may fix it.
- `aligner_not_installed` or, with `--check`, `checker_not_installed` means a Model that adds word timings or the check is missing. The audio is usable as it is. Ask the user whether to install it, as [setup.md](setup.md) describes. Once it is installed, run `narrate <dir>/narration.json --out <dir>` with the same `--model` (and `--check` for the check): the completed Narration carries each Line's seed, so the audio comes out the same and gains `words` and the check.
- `stale_audio` after `--line` means a kept Line's audio no longer matches the Narration: its text, how `say` respells it, Voice, `style`, `emotion`, `speed`, `pitch`, `volume`, `rate` or the language changed since it was read. Read that Line again too.

## Handing over audio

Every WAV the user listens to, a Line, a Design Take or a comparison between Models, reaches them the same way. When you have a tool that attaches files to the conversation, send the file itself: where the user sees the conversation but not your filesystem, a path is only text they cannot play. Send a copy, since `--line` overwrites a Line's file and every run names its files alike (`<id>.wav`, `take-1.wav`): copy each file into a temporary directory outside `--out`, under a name no file you have sent has, made of the Line id or take and what tells it from the others, such as its Model, Voice, round or reading: `gei-pinyin__voxcpm2.wav`, `round-2__take-1.wav`, `intro__reading-2.wav`. Give the original's absolute path beside it, or alone when you have no such tool.

## Errors

The error's `hint` says what to do, and `schema` lists every exit code. Two need the user:

- **Exit 3, `model_not_installed`**: nothing was downloaded. Tell the user, from `details`, each missing Model's id, size, license and license link exactly as given, any `extra_repos` it downloads with it, and the total. Run `voxx install <model>` only after they agree; follow [setup.md](setup.md).
- **Exit 4, `unsupported_language`**: pick from `details.languages` the tag that matches the language and accent the user asked for, and write it into the Narration. If none matches, tell the user this Model cannot read that language; substituting a related language is the user's call, not yours.

## Delivering

Give the user the absolute path of `<out>/narration.json` and one line per warning that is still open. For CueTake, pass that file to `cuetake record --narration`; it already has the shape CueTake reads, with `audio`, and `words` for the Subtitles.

Remind the user, every time you deliver, that this is AI-generated speech: many platforms require a video with it to be labeled as AI-generated content when it is published. With a Cloned Voice, the user is responsible for having the right to use that voice.
