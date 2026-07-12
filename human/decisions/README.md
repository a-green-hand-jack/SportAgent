# human/decisions/ — 轻量 ADR

记录**为什么**接受/拒绝某个规则、recipe、架构选择或实验方向。ADR（Architecture Decision Record）是轻量的：一页说清 context / decision / consequences / status 即可，目的是让未来的 agent 和 human 不必重推同一场讨论。

## 命名

- `<YYYYMMDD>-<slug>.md`（示例 ADR 用占位日期 `00000000`）。
- 根目录 `DECISIONS.md` 维护索引；新增 ADR 时在那里登记一行。

## 结构

```
# <标题>
## Context     背景：面对什么问题、有哪些选项。
## Decision    决定：选了什么、要点。
## Consequences 后果：好处、代价、后续影响与约束。
## Status       proposed | accepted | rejected | superseded
```

## 规则

- agent 可起草 ADR（status: `proposed`）；`accepted` / `rejected` 由 **human** 置。
- 已 `accepted` 的 ADR 不删改；被取代时新开一条并把旧的标 `superseded`。
- 示例：`00000000-adopt-template.md`（采用本模板作为项目控制根）。
