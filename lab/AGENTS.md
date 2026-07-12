# lab/ — agent 约束

本层是控制面根。agent 在这里的动作会波及全项目，务必按子层边界行事。

## 允许

- 在 `code/` 下按各子目录规则实现与修改代码。
- 向 `research/` 的 YAML 追加 claim / evidence / ledger 条目（遵守证据分层）。
- 向 `data/`、`artifacts/`、`models/` 追加 **index / manifest / checksum**（不是 bytes）。
- 在 `traces/`、`recipes/`、`evals/`、`reports/` 下按 recipe 政策记录与产出。

## 禁止

- **禁止把大 bytes 提交进 Git**：checkpoint、run 原始输出、原始数据集、wandb 目录均已 gitignore，只登记 index/manifest/summary。
- 禁止改动 `infra/private/`（永不进 Git）。
- 禁止越过人类闸门自行启动训练/评测作业（见 `infra/launch/`）。
- 禁止在交付物或 report 里 overclaim：任何能力/论文级 claim 必须由 `research/evidence.yaml` 支撑，并通过 `research/release-gates.yaml`。

## 必须验证

- 结构改动（移动/改名/拆分文件、改 ownership 或调用关系）需**同 commit** 更新相关 `ANATOMY.md`。
- 治理相关改动后运行：`python scripts/validate-governance.py`。

## 禁止路径

- `lab/infra/private/**`
- 任何被根 `.gitignore` 覆盖的 bytes 路径（`lab/models/**`、`lab/runs/**`、`lab/data/` 下的大文件、checkpoint、wandb）。
