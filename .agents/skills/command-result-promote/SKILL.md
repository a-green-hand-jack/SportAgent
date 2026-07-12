---
name: command-result-promote
description: "Codex adapter for Claude slash command /result-promote - 把一个实验结果升级为 evidence / paper claim（走证据门槛 + fresh verifier）"
---

# command-result-promote

Codex does not load project `.claude/commands/*.md` files as custom slash commands.
Use this skill when you would have used `/result-promote` in Claude Code.

Canonical source: `.claude/commands/result-promote.md`. Do not edit this adapter by hand; edit the
Claude command and run `python scripts/sync-codex-adapters.py`.

评估把 $ARGUMENTS 的结果 promote 进 `lab/research/evidence.yaml` / `lab/artifacts/result-index.yaml` / 论文。

先检查证据门槛（见 `.agent/artifact-policy.md`）：run 可定位、config 可复现、metric 来源清楚、
与 baseline 比较清楚、caveat 写明。

promote 是 human gate（见 `.agent/human-gates.md`）：用 tier 4 fresh verifier 复核后，
附 run id / config / commit / checkpoint / data split / metric source，再请求人工批准。
不要在有旧训练日志的当前上下文里直接下 claim。

证据门槛与 evidence 写入的完整流程见 `experiment-workflow` skill；本 command 只是它的 promote 入口。
