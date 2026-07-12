# lab/artifacts/ — agent 约束

## 允许

- 向 `result-index.yaml`、`model-index.yaml`、`trace-index.yaml`、`table-index.yaml`、`figure-index.yaml` 追加**索引条目**（含外部位置、checksum、来源 run）。

## 禁止

- **禁止提交任何 bytes**：checkpoint、图片、表数据、原始输出一律不进 Git，只登记 index。
- 禁止写入指向不存在产物的悬空索引。

## 必须验证

- 改 index 后：`python scripts/validate-governance.py`。
- 索引条目应能被 `../research/evidence.yaml` 追溯引用。

## 禁止路径

- 不在此目录放 bytes；模型 bytes 见 `../models/`（gitignore），run 输出见 `../runs/`（gitignore）。
