# Git 流程

两条长期分支：

- `dev`：主干。一个 ticket 一个 ticket 地直接提交到这里，推到 `origin dev`。
- `main`：只放已发布的版本，每个提交都打了 `v<version>` tag。`main` 是 GitHub 默认分支，`npx skills add levyxdev/voxx` 和 `/plugin install voxx` 装的都是它，所以 `main` 上 `scripts/voxx` 钉住的 `voxx@<version>` 必须已经在 PyPI 上。

## 和 skills 的对应

- mattpocock skills 里说的 `main` 指主干，在这个仓库里就是 `dev`：`/code-review` 的 fixed point、`/prototype` 从哪拉分支、PR 的 base（`gh pr create --base dev`）都按 `dev` 算。
- Issue 按 `docs/agents/issue-tracker.md` 用 `gh issue close` 关。提交信息里的 `Closes #n` 要等提交进了默认分支 `main` 才生效，也就是发布的时候。

## 发布

按 [releasing.md](releasing.md) 在 `dev` 上提交 Release commit，发布到 PyPI，再把 `main` 快进（`--ff-only`）到这个提交并打 tag。

快进让 `main` 和 `dev` 停在同一个提交上，发布完不用再把 `main` 合回 `dev`。快进失败说明 `main` 上有 `dev` 没有的提交，通常是热修：先在 `dev` 上 `git merge main`，再发布。

## 热修

只有在 `dev` 上有还没发布的改动、又必须马上修已发布的版本时才走这条：

1. 从 `main` 拉 `hotfix-<version>`，修好，按 releasing.md 改版本号、检查、发布到 PyPI，再把 `main` 快进到这个分支并打 tag。
2. 切回 `dev`，`git merge main`，推 `dev`，删掉热修分支。

`dev` 上没有未发布的改动时，直接在 `dev` 上修，正常发布。
