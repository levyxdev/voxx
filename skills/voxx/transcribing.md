# Transcribing an audio or video file

`transcribe` reads what is said in a Media File on the user's machine and prints its Transcript: the text and language of each Passage, at most five minutes each, and with `--words` each word's start and end, in seconds from the start of the file. `voxx schema transcribe` is the reference for the result and the warnings.

```
transcribe <media> [--language <tag>] [--model <id>] [--words]
```

1. **Check the format.** voxx decodes WAV, MP3 and FLAC itself. Anything else, video included, needs ffmpeg: when `unreadable_media` says it is not installed, offer `brew install ffmpeg` and wait for the user to agree.
2. **Settle the language.** Pass `--language` only when the user names it; otherwise leave it out, and each Passage is transcribed in the language heard, so a recording that switches language keeps both.
3. **Settle the words.** Pass `--words` only when the user needs timings, such as for subtitles, cutting or syncing to the screen: it loads the aligner, about 1.3 GB more memory. Japanese and Korean Passages get `not_aligned`; tell the user those have text but no timings.
4. **Run it.** A long file takes minutes: run it in the background when your shell would time out, and redirect stdout to a file in the user's project. A `passage_done` event on stderr marks each Passage.
5. **Settle the Model.** `transcribe` uses the installed transcribing Model that hears best. When it exits 3, offer `qwen3-asr-1.7b`, the more accurate one, following [setup.md](setup.md); when the user prefers a smaller download, `qwen3-asr-0.6b` works too.

Deliver the Transcript in the form the user asked for. A `language` of `null` with empty `text` means no speech was heard: say so rather than guessing. The Transcript is a machine's hearing, so names, numbers and terms of art may be misheard: point the user at any you doubt rather than silently correcting them.
