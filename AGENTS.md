## Agent skills

### Issue tracker

Issue 和 spec 都放在 GitHub Issues（levyxdev/voxx），用 `gh` 操作。See `docs/agents/issue-tracker.md`.

### Triage labels

使用五个默认标签：needs-triage、needs-info、ready-for-agent、ready-for-human、wontfix。See `docs/agents/triage-labels.md`.

### Domain docs

Single-context：根目录放 `GLOSSARY.md`，ADR 放 `docs/adr/`。See `docs/agents/domain.md`.

## 检查

改完代码跑 `uv run basedpyright` 和 `uv run pytest`，都要零错误。改动碰到 Engine 或真实模型时，再用 `VOXX_TEST_REAL=1 uv run pytest tests/test_real_models.py` 跑慢测试，它用的是本机已安装的模型。
