# Designing a voice

A Designed Voice is a new voice made from a text description. `voice design` reads one text in several Design Takes; the user listens and chooses one, and `voice add --from-design` stores it. From then on a Narration names it in `voice` like any other Voice, and every Line sounds like the chosen take.

## 1. Write the descriptions

Describe the voice by its traits: age, gender, timbre, pace, tone, and the setting it speaks in, such as "a warm woman in her forties, slightly slow, calm and friendly, like explaining a product to a customer". Write the tone into the description: a Design Take's tone is how the voice sounds on every Line without a `style`.

Open with the gender and age, stated plainly ("an adult man in his thirties, a male voice, mid-low pitch"), and keep away from words the Model ties to the other gender: a male voice described as "清亮" or "sweet" can come back a woman's. When a take comes back the wrong gender or age, rewrite the description; designing again with the same one only rolls the dice. The `transcript` cannot show this, so ask the user to listen for it.

Describe traits only. When the user asks for a voice that sounds like a real person, a celebrity, a character's actor, or someone they know, decline that part and rewrite the request as traits ("a deep, slow, authoritative male voice"); show the user the rewritten description.

## 2. Write the text the takes read

Write it as in [cloning.md](cloning.md) step 2: two or three sentences in the Narration's language, about 10 seconds aloud, in everyday words, in the tone the Narration should have, written as spoken. Pass that language as `--language`.

## 3. Let the user choose

Design in two rounds, each into a new `--out`:

```
voice design --describe <description> [--describe <description>]... --text <text> --language <tag> --out <dir> [--takes <n>]
```

1. **The style**: two or three different descriptions, one take each, into `voice-design/1/`. The user picks the description they like.
2. **The voice**: that one description with `--takes 2` or `3`, into `voice-design/2/`. Every take is a different person; the user picks one.

Each take takes about 15–30 seconds, so run the command in the background when your shell would time out. Before showing the takes, read each one's `transcript`: drop a take whose transcript contains the description, or anything the text does not say, and design again if none is left. Then give the user each remaining take's absolute path with its description, and let them listen: the choice is theirs, since only they can hear the takes.

## 4. Store it

Ask where the voice lives, as in [cloning.md](cloning.md) step 3, then store the chosen take:

```
voice add <name> --from-design <the round's --out> --take <n> [--voices-dir <dir>]
```

It is read like a Cloned Voice: the Model and the `style` rules of [cloning.md](cloning.md) step 4 apply. It reads in any language its Model reads, not only the one it was designed in.

When delivering, a Designed Voice needs no reminder about the right to use a voice, since no real person's voice is in it; the reminder to label AI-generated speech still applies.
