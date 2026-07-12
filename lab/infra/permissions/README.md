# lab/infra/permissions/ — 权限理由

解释根 `.claude/settings.json` 与 `.codex/rules/default.rules` 的 deny / ask / allow / prompt 列表**为什么这样设**。

每条高危能力应记录：

- **owner**：谁负责这条决策。
- **理由**：为什么 deny / ask / allow。
- **验证**：如何确认约束仍生效。

放宽任何高危权限而不在此留痕（owner + 理由 + 验证），即为违规。改动后跑 `python scripts/validate-governance.py`。
