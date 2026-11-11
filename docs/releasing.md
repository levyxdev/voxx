# Releasing

The `voxx` package on PyPI and the skill in `skills/voxx/` are released together from one tag: the skill's launcher runs `uvx voxx@<version>`, so the package of that version must be on PyPI before anyone installs the skill from the tag.

## 1. Set the version

Set the same version in all three places, then run `uv lock`:

- `version` in `pyproject.toml`
- `uvx voxx@<version>` in `skills/voxx/scripts/voxx`
- `version` in `.claude-plugin/plugin.json`

`tests/test_release.py` fails until they agree.

## 2. Check

```sh
uv run basedpyright
uv run pytest
VOXX_TEST_REAL=1 uv run pytest tests/test_real_models.py
VOXX_TEST_RELEASE=1 uv run pytest tests/test_release.py
```

`VOXX_TEST_RELEASE=1` also builds the wheel and the sdist and checks what they ship; the default `uv run pytest` skips that.

## 3. Build

```sh
rm -rf dist
uv build
```

This writes `dist/voxx-<version>.tar.gz` (the sdist) and `dist/voxx-<version>-py3-none-any.whl` (the wheel), and uploads nothing. Try the wheel the way the skill will run it, outside the source tree:

```sh
uvx --from ./dist/voxx-<version>-py3-none-any.whl voxx doctor
```

## 4. Publish

These steps are the maintainer's, by hand; nothing in the repository runs them. Upload before `main` moves: `main` is what `npx skills add` installs, so its launcher must never pin a version PyPI lacks ([git workflow](git-workflow.md)).

1. Commit the release on `dev` (or the hotfix branch) and push it.
2. Upload: `uv publish dist/*`, with a PyPI token for the `voxx` project in `UV_PUBLISH_TOKEN`.
3. Check that `uvx voxx@<version> doctor` runs from PyPI.
4. Fast-forward `main` to the release commit, tag it, and push both:

   ```sh
   git switch main
   git merge --ff-only dev
   git tag v<version>
   git push origin main v<version>
   git switch dev
   ```

5. Create a GitHub release from the tag.

