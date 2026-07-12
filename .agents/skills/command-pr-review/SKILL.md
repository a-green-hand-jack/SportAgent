---
name: command-pr-review
description: "Codex adapter for Claude slash command /pr-review - 以 fresh reviewer 审查当前 diff（correctness/回归/测试/复现/数据安全）"
---

# command-pr-review

Codex does not load project `.claude/commands/*.md` files as custom slash commands.
Use this skill when you would have used `/pr-review` in Claude Code.

Canonical source: `.claude/commands/pr-review.md`. Do not edit this adapter by hand; edit the
Claude command and run `python scripts/sync-codex-adapters.py`.

以 fresh reviewer 审查当前 diff。聚焦：
- correctness、regressions、missing tests
- research reproducibility
- data/checkpoint safety
- anatomy impact（结构改动是否同 commit 更新了 ANATOMY / ledger）

不要先写总结。按 severity 列出 findings，附文件引用与建议修复。
最后跑 `python scripts/validate-governance.py` 报告结果。
