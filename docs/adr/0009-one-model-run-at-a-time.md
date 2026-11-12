# One Model run at a time per `$VOXX_HOME`

Agents liked to start several `narrate` or `voice design` runs at once to finish sooner, and on a Mac with little memory that made it hot, short of memory, or crash. A worker returns its Models' memory when it exits (ADR 0002), but several workers share one GPU, so running them side by side gains little, and once their Models no longer fit in memory the machine swaps and every run slows down. On an M4 with 16 GB, two runs of a six-Line Narration side by side took 25.2 s against 30.2 s one after the other with `qwen3-tts-0.6b-customvoice` (16% faster, 6.5 GB at peak against 5.2 GB); with `voxcpm2`, about 6.9 GB each, one after the other took 78.2 s, while side by side neither had read five of its six Lines after four minutes. So every command that starts a worker takes an exclusive lock under `$VOXX_HOME` first and holds it until the worker exits: a second run waits, with no timeout, and reports on stderr which command holds the lock and its PID. The operating system releases the lock when its holder dies, so a crash never leaves it held.

## Considered options

- **Let the skill tell the agent to size the concurrency from the machine's memory.** Rejected: an agent only governs its own runs, not another session's or another project's, and voxx registers no peak memory per Model to size it from.
- **Allow more than one run on a machine with more memory.** Rejected for now: memory only keeps parallel runs from slowing down, it does not make them faster; a setting such as `VOXX_MAX_WORKERS` can be added if a machine ever shows a real gain.
- **Fail at once when the lock is held.** Rejected: the agent would only retry later, queueing by hand, and could take the refusal for a failure.
- **One lock per machine.** Rejected: `$VOXX_HOME` is where the Models live and normally there is one; a lock under it also lets the tests, each with its own temporary `$VOXX_HOME`, run in parallel against the fake Engine.

## Consequences

- `doctor` does not report memory: nothing needs it.
- Two runs with different `$VOXX_HOME`s on one Mac still run side by side.
- The lock belongs to the voxx command, not its worker: if the command is killed outright, its worker may hold its Model a moment longer, until it notices its stdin closed, while the next run starts.
