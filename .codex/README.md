# .codex/

Codex project adapter layer. Keep durable repo behavior canonical in `AGENTS.md`,
`.agent/`, and `.claude/`; this directory makes the same capability surface
discoverable by Codex.

| Path | Purpose |
| --- | --- |
| `config.toml` | Project-scoped Codex config: subagent limits and lifecycle hooks. |
| `rules/default.rules` | Codex execpolicy prompts/forbids for high-risk shell commands. |
| `agents/*.toml` | Generated Codex custom-agent adapters from `.claude/agents/*.md`. |

After editing `.claude/agents/`, `.claude/skills/`, or `.claude/commands/`, run:

```bash
python scripts/sync-codex-adapters.py
python scripts/validate-governance.py
```
