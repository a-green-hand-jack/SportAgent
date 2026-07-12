# deliverables/ — agent 规则

对外承诺层。agent 在这里的默认姿态是**谨慎**：交付物代表项目对外部的正式声明。

## 硬规则

- **No overclaim**：写入任何对外 claim 前，必须确认它在 `lab/research/claims.yaml` 登记、且 `lab/research/evidence.yaml` 有对应证据。没有证据的话不写，或标为 "not yet proven"。
- **human gate**：对 `paper/`、`slides/`、`release/` 内容的实质改动必须走 human gate（见 `.agent/human-gates.md`），并经 `human/reviews/results/` 评审。
- **可追溯**：每张 figure / table / 数字都要能指回 `lab/artifacts/` 的产物或 run id。不允许手填无来源的数字。

## 允许

- 更新 `index.md` 的状态与证据齐全度字段。
- 在 writing contract 骨架里补充 target venue / story / claims 等（内容，非绕过 gate）。
- 生成 / 更新可追溯的 figure、table（来源记录在案）。

## 禁止

- 不要引入 `evidence.yaml` 之外的结论。
- 不要在无 human 批准下改动已 submitted / published 的交付物。
- 不要把实验探索过程写进交付物（那属 `lab/`）。

## 必须验证

- 改动后核对 `index.md`：受影响交付物的 claim 支撑与 evidence 齐全度是否仍成立。
- 如涉及结构/契约变更，登记 `memory/change-control.yaml`。
