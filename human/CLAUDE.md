# CLAUDE.md — human/ 路由

薄路由。进入 `human/` 时按需读。

## 找任务

- `briefs/active/` — 当前该做什么，以这里的 brief 为准。

## 要 human 拍板

- plan → `reviews/plans/`
- result → `reviews/results/`
- recipe 小 diff → `reviews/recipes/`（见 `.agent/claude-code-recipe-policy.md`）

## 记决策 / 查决策

- `decisions/` — 轻量 ADR；索引在根 `DECISIONS.md`。
- 已接受的示例：`decisions/00000000-adopt-template.md`。

## 零散输入

- `inbox/` — 先落这里，之后分类清空。

## 相关

- `.agent/human-gates.md` — 哪些动作需要 human gate。

## 边界

规则见 `AGENTS.md`。接受/拒绝是 human 的动作，agent 只起草与整理。
