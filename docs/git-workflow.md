# Git workflow

Two long-lived branches:

- `dev`: the trunk. Commit to it directly, one ticket at a time, and push to `origin dev`.
- `main`: released versions only; every commit on it carries a `v<version>` tag. `main` is the GitHub default branch, and `npx skills add levyxdev/voxx` and `/plugin install voxx` both install from it, so the `voxx@<version>` that `scripts/voxx` pins on `main` must already be on PyPI.

## Mapping to the skills

- Where the mattpocock skills say `main` they mean the trunk, which here is `dev`: `/code-review`'s fixed point, the branch `/prototype` branches from, and a PR's base (`gh pr create --base dev`) all count from `dev`.
- Close issues with `gh issue close`, as `docs/agents/issue-tracker.md` says. A `Closes #n` in a commit message takes effect only once the commit reaches the default branch `main`, that is, at the release.

## Releasing

Follow [releasing.md](releasing.md): commit the release on `dev`, publish it to PyPI, then fast-forward (`--ff-only`) `main` to that commit and tag it.

Fast-forwarding leaves `main` and `dev` on the same commit, so nothing needs merging back into `dev` after a release. If the fast-forward fails, `main` has a commit `dev` lacks, usually a hotfix: run `git merge main` on `dev` first, then release.

## Hotfixes

Take this path only when `dev` holds unreleased changes and a released version needs fixing now:

1. Branch `hotfix-<version>` from `main`, fix it, then set the version, check and publish to PyPI as releasing.md says, and fast-forward `main` to the branch and tag it.
2. Switch back to `dev`, `git merge main`, push `dev`, and delete the hotfix branch.

When `dev` holds no unreleased changes, fix on `dev` and release as usual.
