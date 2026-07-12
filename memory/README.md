# memory/ — 活状态层

这是 repo 的**工作记忆落盘处**。context 是昂贵的短期记忆，`memory/` 是能让任意 fresh session 接续的长期记忆。

## 什么时候来这里

- session 开始：先读 `current-status.md` 与 `session-tree.md`，恢复当前 objective / phase / 下一步。
- session 结束或 compact 前：更新 `current-status.md`，必要时写 `handoffs/` 与 `branches/`。
- 想知道 phase 进度：看 `phase-dashboard.yaml`。
- 做了结构/doctrine/能力/契约级改动：记到 `change-control.yaml`。
- 想复用某个 Claude Code 工作流：查 `current-practices.md`（失效的看 `deprecated-practices.md`）。

## 目录一览

| 路径 | 内容 |
| --- | --- |
| `current-status.md` | 当前状态活文件（每次 session 结束更新） |
| `session-tree.md` | 父/子 session 分支树与合并顺序 |
| `current-practices.md` | 采用中的 CC recipe 索引 |
| `deprecated-practices.md` | 失效技巧与替代 |
| `phase-dashboard.yaml` | phase 看板 |
| `change-control.yaml` | 变更登记账 |
| `gc/` | 过期状态/handoff 的归档与回收规则 |
| `branches/` | 单分支状态文件 `<slug>.md` |
| `handoffs/` | handoff 文件 `<YYYYMMDD>-<slug>.md` |

## 原则

磁盘才是记忆。不要把 5000 行日志、整篇 paper、整份源码塞进 context——落盘、给路径、让 subagent 读后返回 summary。详见 `.agent/context-memory-policy.md`。
