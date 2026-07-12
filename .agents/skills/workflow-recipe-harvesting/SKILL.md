---
name: workflow-recipe-harvesting
description: 当要从 human-cc 会话 trace 提炼可复用的 Claude Code 工作流 recipe 时，用来产出 recipe、绑复测任务与报告，并维护 practices 索引。
---

> Codex adapter: generated from `.claude/skills/workflow-recipe-harvesting/SKILL.md`. Do not edit this copy by hand; run `python scripts/sync-codex-adapters.py`.

# workflow-recipe-harvesting

从人类使用 Claude Code 的 trace 里提炼候选 recipe，给每条绑上小复测任务与过期时间，跑复测出报告，并按状态维护 practices 索引。

## 适用边界

适用：`lab/traces/human-cc/` 下有新会话、需要沉淀/复测/淘汰某条工作流做法时。
不适用：一次性技巧、无法复测的经验（不进 recipe）。

## 输入 / 输出 artifact

- 输入：`lab/traces/human-cc/<date>/<session>/`。
- 输出：
  - recipe：`lab/recipes/claude-code/<id>.yaml`
  - 复测任务：`lab/evals/cc-workflow/<id>.yaml`（每条绑 1-3 小任务）
  - 报告：`lab/reports/cc-workflow/`
  - 索引：`memory/current-practices.md` / `memory/deprecated-practices.md`

## 需要读取的 ledger

- `.agent/claude-code-recipe-policy.md`（状态机、绑测规则、过期规则）。
- 现有 `memory/current-practices.md` / `memory/deprecated-practices.md`。

## 允许修改的路径

- `lab/recipes/claude-code/<id>.yaml`
- `lab/evals/cc-workflow/<id>.yaml`
- `lab/reports/cc-workflow/`
- `memory/current-practices.md` / `memory/deprecated-practices.md`
- **不修改原始 trace。**

## 步骤

1. 读 trace：识别重复出现、可复用的工作流模式作为候选 recipe。
2. 写 recipe（`lab/recipes/claude-code/<id>.yaml`），初始状态 `candidate`。
3. 绑复测：在 `lab/evals/cc-workflow/<id>.yaml` 写 1-3 个小任务（正例 / 边界 / 反例），并设过期时间。
4. 跑复测，报告落 `lab/reports/cc-workflow/`。
5. 按结果推进状态：candidate → provisional → stable；失效则 deprecated。
6. 更新索引：stable/provisional 进 `current-practices.md`，deprecated 进 `deprecated-practices.md`。

## 验证命令

```
python scripts/validate-governance.py
```

## 失败时的 handoff

- 复测不稳定/无法自动判定：保持 `provisional`，按 `.agent/templates/handoff.md` 请人类裁定。
- recipe 过期无人复测：标 `deprecated` 并移入 `deprecated-practices.md`，不留悬空 stable。
