# Cloning a voice

A Cloned Voice is made once from a Reference Recording with `voice add`, then named in a Narration's `voice` like a Preset Voice.

## 1. Confirm the right to the voice

Before anything else, ask the user to confirm they have the right to use this voice: their own, or that of someone who agreed to it, such as a voice actor they hired. voxx cannot tell whose voice a recording is and checks nothing, so the responsibility is the user's, and the README says so. Clone only once the user confirms; if they are unsure, offer a Preset Voice instead.

## 2. Get a good Reference Recording

The clone copies everything in the recording, noise and room included. Ask for one speaker, no music or background voices, in the Narration's language, about 5 to 15 seconds of natural speech. Any common audio format works; voxx normalizes it.

If the user knows exactly what the recording says, pass it as `--ref-text`: an exact transcript gives the closest clone. Without it, voxx transcribes the recording, which needs the transcribing Model installed (exit 3 otherwise; see [setup.md](setup.md)); show the user the `reference_text` it heard, and if it is wrong, add the voice again with `--ref-text` and `--overwrite`.

## 3. Choose where it lives

Ask the user whether the voice belongs to one project or to this machine:

- **The project**: pass `--voices-dir` with a folder in the project, such as `voices/`. The voice then travels with the project, and may be committed with it. Pass the same `--voices-dir` to every `voices` and `narrate` call in that project.
- **This machine**: leave `--voices-dir` out, and it is stored under `$VOXX_HOME/voices`.

## 4. Choose the Model

A Cloned Voice is read by the Model it was added with: the default cloning Model unless `voice add --model` picks the other one (`voxx models --capability clone`). Neither cloning Model follows `style`. The two sound different, and only the user can judge which sounds more like the speaker: to let them compare, read the same short Narration once more with `narrate --model <the other one>` into a second `--out`, and play them both. Keep the one they choose by adding the voice again with that `--model` and `--overwrite`.
