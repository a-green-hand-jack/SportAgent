# human/reviews/plans/ — plan 评审

agent 在执行前把 plan 交到这里，由 human 评审并批准/驳回。目的是在**动手前**对齐方向，避免昂贵的错误执行。

## 流程

1. agent 依据 `human/briefs/active/` 的 brief 起草 plan（通常 plan 正文在 `plans/<YYYYMMDD>-<slug>.zh.md`）。
2. 在本目录放一条 review 记录，指向该 plan，并给出关键取舍与风险。
3. human 批准 / 要求修改 / 驳回。
4. 结果重要时固化为 ADR（`human/decisions/`）。

## review 应包含

- 指向被评审 plan 的路径。
- plan 的核心取舍、假设、影响的路径。
- 是否触及 forbidden paths 或需要额外 gate。
- human 结论与日期。

agent 只起草，批准是 human 的动作。gate 契约见 `.agent/human-gates.md`。
