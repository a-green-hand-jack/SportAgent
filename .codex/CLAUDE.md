# .codex/ — Claude Code 入口

薄路由：这里是 Codex 适配层。Claude Code 的 canonical 能力仍在 `.claude/`。

- 改 custom agent 行为：改 `.claude/agents/*.md`，再跑 `python scripts/sync-codex-adapters.py`。
- 改 Codex hooks/rules：看 `config.toml`、`rules/default.rules`，同步 `.agent/action-boundary.md` 与 `lab/infra/permissions/`。
- 不要手改生成的 `agents/*.toml`。
