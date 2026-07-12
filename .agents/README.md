# .agents/

Open agent skills adapter layer for Codex. Codex scans `.agents/skills` from the
current directory up to the repo root, so this directory exposes repo-local
workflows without installing anything globally.

`skills/` is generated from canonical Claude Code files:

- `.claude/skills/*/SKILL.md` -> same-named Codex skills.
- `.claude/commands/*.md` -> `command-*` Codex skills that replace project slash commands.

Regenerate after capability edits:

```bash
python scripts/sync-codex-adapters.py
```
