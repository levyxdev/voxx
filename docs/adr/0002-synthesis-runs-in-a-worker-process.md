# Synthesis runs in a separate worker process

The CLI does not load Models in its own process. It starts a worker process, talks to it with JSON-RPC over stdio, and the worker exits once a Narration is read. So when mlx runs out of GPU memory or crashes, only the worker dies, and the CLI can still return a structured error to the agent; the several GB a Model holds are returned when the worker exits; and the CLI never imports mlx, so commands like `voxx models` and `voxx schema` return at once. PyTorch-based Engines or a resident mode added later keep the same protocol.

## Considered options

- **One process with lazy imports.** Rejected: the least code, but on a crash the agent gets no JSON error, and the protocol would still have to be added later.
- **A separate venv per Engine.** Deferred: needed only when two Engines require different versions of one dependency (for example, the official CosyVoice and Qwen3-TTS packages each pin a conflicting `transformers`). In v0.1 every Model runs through mlx-audio, and the worker is `python -m voxx.worker` in the same package.
