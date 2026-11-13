# Voices and Default Voices live only under `$VOXX_HOME`

`--voices-dir` let a project keep its Cloned Voices and Designed Voices in its own folder, so they could travel with it and be committed. But every later `voices` and `narrate` in that project had to pass the same folder again, and an agent in a new session had no way to know a project had one: a Voice stored there was as good as lost. Default Voices made it worse, since a default would name a Voice that one voices dir has and another lacks. So `--voices-dir` is gone: every Cloned Voice and Designed Voice is under `$VOXX_HOME/voices`, and the Default Voices are under `$VOXX_HOME` too, one place on the machine that every agent and project finds without being told.

## Considered options

- **Keep `--voices-dir`, with a Default Voice per voices dir.** Rejected: it keeps the default beside the Voices it names, but leaves the folder itself for the agent to remember.
- **Keep `--voices-dir`, with the Default Voices under `$VOXX_HOME`.** Rejected: a default could name a Voice the voices dir in use does not have.

## Consequences

- A Voice no longer travels with a project; copying `$VOXX_HOME/voices/<name>/` to another machine does.
