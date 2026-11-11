# A Designed Voice is fixed by a chosen take, then read in cloning mode

Models such as VoxCPM2 can make a voice from a text description, but every generation is a new person: the same description with another sentence or another seed gives another voice. A Narration has a dozen Lines that must all be one person, so designing a Voice takes two steps: first make several Design Takes from the description, all reading the same sample text, and have the user listen and choose one; the chosen one is stored as the Designed Voice's Reference Recording, and from then on cloning mode reads every Line after it. The cost is one more listening and choosing step.

## Considered options

- **Generate every Line directly from the description.** Rejected: the voice changes from Line to Line, and re-voicing one Line with `--line` can change it too.

## Consequences

- `narrate` needs no separate path for Designed Voices: a cloning Model reads them like Cloned Voices, the first cloning Model by default, and `voice add --model` and `narrate --model` can switch it as usual.
- Whether a Designed Voice follows `style` is decided, as for a Cloned Voice, by the cloning Model that reads it; no separate rule.
