# memory/ — agent 规则

`memory/` 是活状态层。agent 在这里的职责是**让状态可恢复**，不是堆历史。

## 允许

- 更新 `current-status.md`：每次完成小目标 / session 边界 / compact 前。
- 追加 `handoffs/<YYYYMMDD>-<slug>.md`（用 `.agent/templates/handoff.md`，<120 行）。
- 维护 `branches/<slug>.md`（用 `.agent/templates/branch-status.md`）。
- 更新 `session-tree.md` 的 children 表与合并顺序。
- 在 `phase-dashboard.yaml` / `change-control.yaml` 追加或改状态字段。
- 把过期条目移到 `gc/`。

## 禁止

- 不要把长日志、整篇论文、整份源码粘进任何 memory 文件——只留路径 / run id / summary。
- 不要在 memory 里记实验事实（那属于 `lab/research/` 与 `lab/artifacts/`）。
- 不要把对外 claim 写这里（属于 `deliverables/`）。
- 不要删历史状态而不归档；过期内容进 `gc/`，不是直接删。
- 不要越界改 `session-tree.md` 里 **Global forbidden paths** 列出的路径。

## 必须验证

- 写完 `current-status.md` 后自检：objective / 改动文件 / 命令与结果 / 未解 blocker / 下一步 / 禁改路径 是否齐全——这是 compact 的 preserve 清单。
- `phase-dashboard.yaml` 与 `change-control.yaml` 改完要能被 validator 解析（合法 YAML）。

## 谁维护

`session-boundary-agent`、`branch-reporter` 负责 status/handoff/branch；结构性变更由发起改动的 agent 登记 `change-control.yaml`。
