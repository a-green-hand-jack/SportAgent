# .agents/ — Claude Code 入口

薄路由：这里是 Codex skill adapter layer。

- Claude Code canonical workflows live in `.claude/skills/` and `.claude/commands/`.
- Do not hand-edit generated `skills/*/SKILL.md`.
- After changing canonical workflows, run `python scripts/sync-codex-adapters.py`.
