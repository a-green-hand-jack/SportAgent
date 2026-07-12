# CLAUDE.md — memory/ 路由

薄路由。进入 `memory/` 时按需读本目录文件，不要通读。

## session 开始先读

1. `current-status.md` — 当前 objective / 改动 / 下一步。
2. `session-tree.md` — 我在哪个 phase、有无子 session、禁改路径。
3. 需要时：`phase-dashboard.yaml`（phase 进度）、相关 `branches/<slug>.md`。

## session 结束 / compact 前

1. 更新 `current-status.md`（活文件，见顶部说明）。
2. 需要交接则写 `handoffs/<YYYYMMDD>-<slug>.md`。
3. 分支状态写 `branches/<slug>.md`。

## 相关 repo-local doctrine

- `.agent/context-memory-policy.md` — 落盘位置与 context 阈值。
- `.agent/checklists/pre-compact.md` — compact 前清单。
- `.agent/templates/handoff.md`、`.agent/templates/branch-status.md` — 模板。
- `.agent/claude-code-recipe-policy.md` — recipe 采用/失效流程（配合 `current-practices.md`）。

## 边界

规则见本目录 `AGENTS.md`。不要在 memory 记实验事实或对外 claim。
