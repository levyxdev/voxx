# Models are downloaded only by an explicit install command

No command downloads a Model by itself. When a Model is missing, the command fails as "not installed" and says which Model to install, how large it is, and under what license; the agent, as the skill requires, tells the user, and runs `voxx install <model>` only after the user agrees. This is the same rule as CueTake's `install-browser`, so an agent learns it once.

Which missing Models count as a failure is in [ADR 0006](0006-only-the-model-that-reads-must-be-installed.md): only the Model needed to read; a missing helper Model degrades to a warning.

## Extra Repos (added 2026-11-07)

Some Models need another repo when they load, such as Chatterbox needing `mlx-community/S3TokenizerV2`. The registry records it as the Model's Extra Repo, with the size and license as checked; `voxx install` downloads it with the Model, counts it in the size told to the user before installing, and says which repos come along. Only a `voxx install` the user agreed to downloads anything; that does not change. If any file of an Extra Repo is missing, the Model counts as not installed.

Extra Repos are **not pinned**: `voxx install` downloads the latest revision at the time, records the revision actually downloaded in the install manifest, and installs even when the size differs from the checked one. The reason is that the Engine fetches it by repo name with no revision (Chatterbox hard-codes the repo name), so it gets the latest anyway; and it is only companion weights such as a tokenizer, whose license follows upstream. The cost is that two installs may get different revisions, so the install manifest records which one was installed. The main repo stays pinned to its revision, and a size mismatch refuses the install.

2026-11-09: after the audition neither Chatterbox nor MOSS-TTS-Nano stayed (levyxdev/voxx#25), so no Model carries an Extra Repo now; the mechanism stays, for future Models that need another repo when they load.

Extra Repos sit in `$VOXX_HOME/hf-cache` in the Hugging Face cache layout, and the worker points `HF_HUB_CACHE` there, so the Engine finds them by repo name offline and never reads the user's own Hugging Face cache.

## Considered options

- **A consent token plus a dedicated exit code (DESIGN.md draft).** Rejected: the CLI cannot verify that anyone really agreed, so the token only adds complexity without adding protection.

## Consequences

- The registry lists only Models whose weight license allows commercial use, since voxx's main use is voicing demos of products that get published.
