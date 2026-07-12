# memory/handoffs/ — 交接文档

当一个 session 要把工作交给下一个 session（或另一个 agent / human）时，写一份 handoff。目标是：接手方只读这一份就能继续，不需要回看聊天历史。

## 命名

- 文件名：`<YYYYMMDD>-<slug>.md`（如 `20260708-eval-harness.md`）。
- 结构：使用 `.agent/templates/handoff.md`。
- **长度 < 120 行**。超了说明塞了不该塞的东西（长日志、整段源码）——改成给路径/summary。

## 内容应覆盖

- 目标与当前进度、关键决策与理由。
- 改动的文件、跑过的命令与结论。
- 未解 blocker、下一步、禁改路径。
- 相关产物路径（`lab/artifacts/`、run id 等），不贴内容。

## 与 current-status 的关系

- `current-status.md` 是滚动更新的活文件；handoff 是某个时间点的**冻结快照**。
- 交接后旧 handoff 可按 `gc/` 规则归档。
