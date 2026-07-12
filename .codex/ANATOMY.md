---
related_files:
  - ../ANATOMY.md
  - ../.claude/ANATOMY.md
  - ../.agents/ANATOMY.md
  - ../scripts/sync-codex-adapters.py
maintenance: |
  Codex project adapter layer. 修改 Codex 配置/规则/agent 适配时，同 commit 更新本文件、
  根 ANATOMY 与 scripts/ANATOMY（若生成器或 validator 变化）。
---

# .codex/ ANATOMY

## What this is

Codex 可发现的项目配置与 custom-agent 适配层。canonical 行为仍在 `.agent/` 与 `.claude/`；
本目录负责把它们映射成 Codex 当前读取的格式。

## Components

| 路径 | 角色 |
| --- | --- |
| `config.toml` | Codex project config：subagent 并发/深度限制与 lifecycle hooks。 |
| `rules/default.rules` | Codex execpolicy：高风险 shell 命令的 allow/prompt/forbidden 前缀规则。 |
| `agents/*.toml` | 由 `scripts/sync-codex-adapters.py` 从 `.claude/agents/*.md` 生成的 custom-agent 适配。 |

## Connections

- `config.toml` 的 hooks 调用 `.claude/hooks/*.py`，让 Claude Code 与 Codex 共用同一地板脚本。
- `agents/*.toml` 不手写；生成器同步 name/description/instructions，并把 Claude tool list 转成
  Codex agent 的行为边界说明。
- `.agents/skills/` 承载 Codex skills；与本目录共同组成 Codex capability adapter surface。

## Notes

- Codex project config 只在用户信任本 repo 的 `.codex/` layer 后加载。
- provider/auth/telemetry 等机器本地设置不得写进 project `.codex/config.toml`。
