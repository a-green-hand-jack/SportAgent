---
name: command-checkpoint
description: "Codex adapter for Claude slash command /checkpoint - 落盘当前 session 状态到 memory/current-status.md（compact/clear/handoff 前）"
---

# command-checkpoint

Codex does not load project `.claude/commands/*.md` files as custom slash commands.
Use this skill when you would have used `/checkpoint` in Claude Code.

Canonical source: `.claude/commands/checkpoint.md`. Do not edit this adapter by hand; edit the
Claude command and run `python scripts/sync-codex-adapters.py`.

用 `checkpoint-writer` subagent 更新 `memory/current-status.md`。不改源码。

包含：current objective、constraints、files inspected、files modified、decisions made、
commands/tests run、subagent reports、open issues、exact next steps、do-not-forget notes。

然后用 10 行总结：Done / Evidence / Open risks / Next exact action。

若本轮 plan doc、branch status、artifact index 或 experiment ledger 有变化，同一动作里一并更新。
参考 `.agent/checklists/pre-compact.md`。
