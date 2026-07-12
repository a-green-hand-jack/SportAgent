# 采用 agent-native ML research 模板作为项目控制根

## Context

作为 AI 方向的博士，研究工作越来越多由 coding agent（Claude Code / Codex 等）在 repo 内推进。若关键上下文（当前状态、决策、任务定义、对外 claim 的证据）只存在于聊天窗口，会随 session 结束、context compact 而丢失，导致 fresh session 无法接续、结论无法追溯、对外表述容易 overclaim。

需要一个约定：让**磁盘成为记忆、repo 成为控制根**，human 与 agent 在同一套结构里协作。

## Decision

采用本模板作为项目的控制根，确立三条并列的层：

- `memory/` — 活状态层：当前状态、session 树、phase、handoff、change-control、采用中的 CC recipe。
- `deliverables/` — 对外承诺层：paper / slides / release，遵守 no-overclaim（不超过 `lab/research/evidence.yaml` 的支撑）。
- `human/` — human-agent 协作界面：brief、plan/result/recipe review、轻量 ADR、inbox。

配套 doctrine 位于 `.agent/`（context-memory-policy、human-gates、claude-code-recipe-policy、模板与 checklist 等）。每个重要目录带 README/AGENTS/CLAUDE/ANATOMY 导航四件套。

## Consequences

- 好处：任意 fresh session 可从 repo 接续；决策与证据可追溯；对外 claim 有证据链约束；human 输入固化进 repo 而非留在聊天。
- 代价：需要纪律性地维护状态文件与登记账（status / session-tree / change-control），有一定 overhead。
- 约束：结构/doctrine/能力/契约级变更需登记 `memory/change-control.yaml`；交付物改动走 human gate。

## Status

accepted
