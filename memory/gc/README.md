# memory/gc/ — 记忆垃圾回收

活状态层会不断累积过期的状态快照与旧 handoff。为了让 `current-status.md`、`handoffs/`、`branches/` 保持精简可读，过期内容归档到这里，而不是直接删除。

## 归档什么

- 已被新 handoff 取代的旧 `handoffs/<date>-<slug>.md`。
- 分支合并/废弃后，`branches/<slug>.md` 的历史版本。
- `current-status.md` 中已完成、不再影响未来决策的大段历史（只搬走，摘要留在 status）。

## 规则

- **归档而非删除**：内容移到 `gc/` 对应子路径，保留原文件名与日期前缀。
- **可追溯**：归档时在原位置或 `session-tree.md` 留一行指针，说明去向。
- **不进 context**：归档内容默认不读；只有明确要复盘历史时才由 subagent 读后返回 summary。
- **触发时机**：session-boundary-agent 在 session 结束或 compact 前顺手清理；也可周期性清理。

## 不归档什么

- 实验事实（属 `lab/artifacts/`）、对外 claim（属 `deliverables/`）、正式决策（属 `human/decisions/`）——这些各有归宿，不经 `gc/`。
