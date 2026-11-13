# Cloning a voice

A Cloned Voice is made once from a Reference Recording with `voice add`, then named in a Narration's `voice` like a Preset Voice.

## 1. Confirm the right to the voice

Before anything else, ask the user to confirm they have the right to use this voice: their own, or that of someone who agreed to it, such as a voice actor they hired. voxx cannot tell whose voice a recording is and checks nothing, so the responsibility is the user's, and the README says so. Clone only once the user confirms; if they are unsure, offer a Preset Voice instead.

## 2. Get a good Reference Recording

The clone copies everything in the recording, noise and room included, and its delivery too: the tone of the recording is the tone of every Line without a `style`. Ask for one speaker, no music or background voices, about 5 to 15 seconds of speech. Any common audio format works; voxx normalizes it.

Write the user a script to read: two or three sentences in the Narration's language, about 10 seconds aloud, in everyday words, in the tone the Narration should have, such as showing a colleague a new feature. Write it as spoken, like a Line. Ask the user to read it word for word in one take, and to record it again whenever they changed or stumbled over a word. Pass the script as `--ref-text`: an exact transcript gives the closest clone, and needs no transcribing Model.

When the user brings a recording of their own instead, pass its words as `--ref-text` if they know them exactly. Otherwise voxx transcribes the recording, which needs the transcribing Model installed (exit 3 otherwise; see [setup.md](setup.md)); show the user the `reference_text` it heard, and if it is wrong, add the voice again with `--ref-text` and `--overwrite`.

## 3. Choose the Model

A Cloned Voice is read by the Model it was added with: the default cloning Model unless `voice add --model` picks another one (`voxx models --capability clone`). VoxCPM2 follows `style`, but a Line with `style` may sound less like the speaker, so for a Cloned Voice leave `style` off the top of the Narration and give it only to the Lines that need a different delivery; Qwen3-TTS Base ignores `style` (each such Line says so in `warnings`); Ming-3.0-tts ignores `style` too but follows `emotion`, `speed`, `pitch` and `volume`. They sound different, and only the user can judge which sounds more like the speaker: to let them compare, read the same short Narration once more with `narrate --model <another one>` into a second `--out`, and play them both. Keep the one they choose by adding the voice again with that `--model` and `--overwrite`.
