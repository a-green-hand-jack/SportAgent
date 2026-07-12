---
related_files:
  - ../ANATOMY.md
  - ../.claude/ANATOMY.md
  - ../.codex/ANATOMY.md
  - ../scripts/sync-codex-adapters.py
maintenance: |
  Codex skills adapter layer. 修改生成规则、skills 路由或 command adapter 形态时同步本文件。
---

# .agents/ ANATOMY

## What this is

Codex 读取的 repo-local skills 层。它不是 canonical workflow 源；canonical 源在 `.claude/skills/`
与 `.claude/commands/`，本目录由生成器同步。

## Components

| 路径 | 角色 |
| --- | --- |
| `skills/<name>/SKILL.md` | 从 `.claude/skills/<name>/SKILL.md` 生成的 Codex skill。 |
| `skills/command-<name>/SKILL.md` | 从 `.claude/commands/<name>.md` 生成的 Codex command adapter skill。 |

## Connections

- Codex 可显式用 `$<skill-name>` 调用这些 skills；enabled skills 也会出现在 slash command list。
- `scripts/sync-codex-adapters.py --check` 校验本目录与 `.claude/` canonical 源一致。

## Notes

- 不手写 adapter 内容，避免 Claude/Codex 能力漂移。
