# lab/models/ — 模型 checkpoint

模型权重 checkpoint 的落地位置。

- **bytes 不进 Git**（受根 `.gitignore` 覆盖）：checkpoint 存外部存储，Git 内仅保留索引。
- 模型索引见 `../artifacts/model-index.yaml`（位置 + checksum + 来源 run）。
- 训练由人类经 `../infra/launch/` 启动。
