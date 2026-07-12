# deliverables/release/ — 代码 / 模型 / 数据 release

对外发布的代码、模型权重、数据集及其说明（README / model card / 复现说明）。

## 边界

- release 是公开且难以撤回的承诺，所有实质改动走 **human gate**（见 `.agent/human-gates.md`）。
- **可追溯**：发布的产物要指回 `lab/artifacts/` 的具体产物与 run id；复现说明要能让外部按 `lab/` 的流程重现。
- **No overclaim**：README / model card 里对性能、能力、适用范围的描述不能超过 `lab/research/evidence.yaml` 的支撑；已知局限如实写出。

## 建议

- 发布前核对 `deliverables/index.md`：对应 claim 的 evidence 齐全列须为「是」。
- 许可证、数据来源、伦理/安全说明属于 release 的一部分，缺失应在 human review 中挡下。
