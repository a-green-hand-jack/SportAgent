# memory/branches/ — 分支状态

每个活跃的 branch / worktree 对应一个状态文件 `<slug>.md`，记录该分支「现在到哪了、下一步是什么、有什么风险」。

## 命名

- 文件名：`<slug>.md`，`<slug>` 与 git branch / worktree 名对应（kebab-case）。
- 结构：使用 `.agent/templates/branch-status.md`。

## 谁维护

- `branch-reporter`：在分支上工作时更新该分支的状态文件。
- `session-boundary-agent`：session 边界时确保状态已落盘。

## 与 session-tree 的关系

- `session-tree.md` 的 children 表登记「有哪些分支、合并顺序」（拓扑）。
- 本目录的 `<slug>.md` 记「单个分支内部的详细状态」（内容）。
- 两者应一致：children 表里的每个活跃分支都应有对应的 `<slug>.md`。

## 清理

分支合并或废弃后，其状态文件按 `gc/` 规则归档，不直接删除。
