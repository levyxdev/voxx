## Agent skills

### Issue tracker

Issues and specs live in GitHub Issues (levyxdev/voxx), worked with `gh`. See `docs/agents/issue-tracker.md`.

### Triage labels

The five default labels: needs-triage, needs-info, ready-for-agent, ready-for-human, wontfix. See `docs/agents/triage-labels.md`.

### Domain docs

Single-context: `GLOSSARY.md` at the root, ADRs in `docs/adr/`. See `docs/agents/domain.md`.

## Branches

`dev` is the trunk: commit straight to it, push to `origin dev`, then close the issue the push resolves; wherever a skill says `main`, read `dev`. `main` moves only at a release. Before releasing, hotfixing, or opening a PR or branch a skill asks for, read `docs/git-workflow.md`.

## Checks

After changing code, run `uv run basedpyright` (zero errors) and `uv run pytest` (all passing). When a change touches an Engine or a real Model, also run the slow tests with `VOXX_TEST_REAL=1 uv run pytest tests/test_real_models.py`; they use the Models installed on this machine. When a change touches packaging (`pyproject.toml`'s build sections, the skill, the plugin), also run `VOXX_TEST_RELEASE=1 uv run pytest tests/test_release.py`.
