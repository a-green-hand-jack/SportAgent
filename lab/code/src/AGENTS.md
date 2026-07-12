# lab/code/src/ — agent 约束

## 允许

- 新建与重构模型 / 数据 / 训练 / 评估模块。
- 通过 `../../data/` 的 manifest/schema 访问数据，通过 `../../infra/paths/` 解析路径。

## 禁止

- 禁止硬编码绝对路径、密钥或私密配置（用 `../../infra/`）。
- 禁止在源码目录写入或提交数据 bytes、checkpoint。
- 禁止自行发起训练/评测作业（人类闸门在 `../../infra/launch/`）。

## 必须验证

- 新增或改动模块必须同 commit 在 `ANATOMY.md` 补上 line-addressed citation（`file.py:line`）。
- 对应测试放 `../tests/` 并通过。
- 治理改动后：`python scripts/validate-governance.py`。

## 禁止路径

- 不引用 `../../infra/private/`。
