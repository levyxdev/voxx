# Setting up voxx on the user's machine

voxx runs only on Apple Silicon Macs. Nothing installs without the user's agreement: say what each step downloads, how large it is and under what license, and act only after the user agrees. The user may also prefer to run the commands themselves.

## uv

`scripts/voxx` runs voxx with `uvx`, which comes with uv. Check with `uvx --version`. If it is missing, offer:

- **Homebrew**: `brew install uv`, if Homebrew is there.
- **The official installer**: `curl -LsSf https://astral.sh/uv/install.sh | sh`, from https://docs.astral.sh/uv/.

The first `scripts/voxx` run downloads voxx and its Python dependencies, including Python itself if uv has none that fits, about 700 MB into uv's cache. Tell the user before that first run.

## Models

voxx downloads a Model only through `voxx install <model>`, and no other command ever downloads one. A command that needs a missing Model fails with exit 3, and `details` gives each Model's size, license and license link:

1. Tell the user each missing Model's id, size, license and license link, exactly as `details` gives them, and the total. Check the free space `doctor` reports.
2. Run `voxx install <model>` for each one they agree to, in the background if your shell would time out: a Model is one to three GB.
3. If a download stops or fails, run the same `install` again: it resumes where it stopped. When Hugging Face is slow or unreachable, such as from mainland China, set `HF_ENDPOINT` to a mirror, for example `HF_ENDPOINT=https://hf-mirror.com`, for that `install`.

Only the Model that reads must be installed. The aligner, which adds word timings for Subtitles, and the transcriber, which checks each Line, are worth offering too: without them every Line warns `aligner_not_installed` or `checker_not_installed`, with the same `details`.

## Check

Run `voxx doctor` again: `platform.supported` is true and the Models appear under `models.installed`.

## Uninstall

voxx has no uninstall command.

- **A Model**: delete `$VOXX_HOME/models/<id>/`. `doctor` reports `$VOXX_HOME` (by default `~/.voxx`).
- **Cloned Voices** are the user's work: `voxx voices` lists them with their paths. Ask about each before deleting its folder.
- **voxx itself**: `uv cache clean voxx` removes it from uv's cache. Leave uv, which other tools use.
- **This skill**: remove it with the tool that installed it, for example `/plugin uninstall voxx` in Claude Code.
