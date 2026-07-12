# lab/research/ — agent 约束

## 允许

- 向 `claims.yaml`、`evidence.yaml`、`experiment-ledger.yaml`、`regression-matrix.yaml` 追加条目。
- 把 claim 与其支撑 evidence 关联起来。

## 禁止

- **禁止 overclaim**：任何 claim 的强度不得超过 `evidence.yaml` 里最强证据（`log < metric < table < figure < paper claim`）。
- 禁止在无对应 evidence 时写入 paper 级 claim。
- 禁止绕过 `release-gates.yaml` 声明「可发布 / 可交付」。

## 必须验证

- 每次改 YAML 后：`python scripts/validate-governance.py`（校验证据链、gate、schema 一致性）。
- 新增 claim 必须能追溯到具体 evidence 条目。

## 禁止路径

- 不在此存放数据/产物 bytes（它们的 index 在 `../data/`、`../artifacts/`）。
