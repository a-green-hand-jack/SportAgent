---
name: coding-agent-quota
description: Read local Codex and Claude Code quota/rate-limit snapshots and produce routing evidence for agent work allocation. Use when deciding which coding agent/provider/model to use, balancing Codex vs Claude Code load, checking remaining 5-hour/session and weekly quota, estimating routing capacity before launching subagents, or preparing cross-provider experiments with frozen provider/model policy.
---

> Codex adapter: generated from `.claude/skills/coding-agent-quota/SKILL.md`. Do not edit this copy by hand; run `python scripts/sync-codex-adapters.py`.

# coding-agent-quota

Use this skill before routing meaningful work between Codex and Claude Code when quota, reset time, provider load, or cost-control matters.

## Quick Start

Run the bundled script from the repo root:

```bash
python .claude/skills/coding-agent-quota/scripts/read_agent_quota.py --format table
python .claude/skills/coding-agent-quota/scripts/read_agent_quota.py --format json
python .claude/skills/coding-agent-quota/scripts/read_agent_quota.py --role impl --tier 2 --format json
```

Prefer JSON when another agent or orchestrator will consume the result. Prefer table output for human handoff.

## Evidence Rules

- Treat the script output as a snapshot, not a guarantee. Route high-risk or long-running work only after checking `captured_at` and reset times.
- Prefer provider-specific latest valid snapshots; do not require Codex and Claude to come from the same database row.
- If a provider is `unavailable` or stale, say so and route conservatively instead of inventing percentages.
- Do not read or print credential files. The script uses local usage DB/cache/session logs only.
- For subagent launch decisions, pass `--role` and `--tier` so the output includes `route_recommendation`.
- For formal transfer experiments, freeze provider, model, and policy before launch; do not switch mid-run just because a later quota snapshot changes.

## Routing Heuristic

Use quota as one signal alongside task shape:

- Infrastructure implementation, debugging, and tests: prefer Codex when current-window capacity is healthy.
- Independent safety review and architecture review: use Claude Opus only when the risk justifies the weekly quota burn.
- Routine review, docs, and low-risk checks: prefer cheaper Claude models or the provider with more remaining weekly capacity.
- Cross-provider transfer experiments: use Claude Code when the experiment requires proving transfer across providers.

When current-window remaining capacity is similar, prefer the provider with materially more weekly remaining capacity. When weekly capacity is similar, prefer the provider whose model/tooling best matches the task.

## Source Priority

The script reads:

1. `~/.claude/.search-index/usage.db`, table `api_usage_snapshots`, when present.
2. Codex JSONL session logs under `~/.codex/sessions/` and `~/.codex/archived_sessions/` as a Codex fallback.
3. `~/.paseo/orchestration-preferences.json`, when present, for role-to-provider defaults.

If both sources exist for Codex, prefer the newest valid snapshot by capture time.

## Launch Packet Fields

When routing a child agent, include these fields from JSON output in the packet:

- `providers`: current-window and weekly quota snapshot.
- `usage_velocity`: recent token/message burn proxy from the local usage DB.
- `paseo_preferences`: role defaults, or `missing` if the local file does not exist.
- `route_recommendation`: recommended provider/model/effort plus scoring notes.
