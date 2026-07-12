# lab/data/ — agent 约束

## 允许

- 向 `dataset-index.yaml` 追加数据集条目。
- 在 `manifests/`、`checksums/`、`task-sets/`、`schemas/` 增改清单、校验和、任务集、schema。

## 禁止

- **禁止提交原始数据 bytes**：大文件由根 `.gitignore` 覆盖，Git 里只留 manifest/checksum/schema。
- 禁止写指向不存在数据的 manifest，或与实际不符的 checksum。

## 必须验证

- 改动后：`python scripts/validate-governance.py`（校验 index / manifest / checksum / schema 一致性）。
- manifest 与 checksum 必须匹配同一数据版本。

## 禁止路径

- 不在此目录放大 bytes；受 `.gitignore` 覆盖的数据文件不得强制提交。
