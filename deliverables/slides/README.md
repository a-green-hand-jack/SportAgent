# deliverables/slides/ — 报告 slides

对外报告用的 slides（talk / poster / 组会对外版）。

## 边界

- 实质改动走 **human gate**（见 `.agent/human-gates.md`），必要时经 `human/reviews/results/`。
- **No overclaim**：slides 上的每个结论、每个数字都不能超过 `lab/research/evidence.yaml` 的支撑；口头报告尤其容易夸大，写进 slides 前先核对 `claims.yaml`。
- **可追溯**：图表 / 数字来源要记录（指向 `lab/artifacts/` 的产物或 run id），便于回答提问与复现。

## 建议

- slides 通常是 paper claim 的子集或简化，不应引入 paper 里没有、也没证据的新主张。
- 若某数字仍在变动，标注日期/run id，避免展示过期结果。
