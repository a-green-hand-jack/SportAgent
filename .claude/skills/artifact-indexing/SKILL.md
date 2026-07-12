---
name: artifact-indexing
description: 当有新的 dataset/checkpoint/table/figure 等 asset 产生或需要盘点时，用来维护 artifact 索引并出 stale asset report；绝不删或移动 bytes。
---

# artifact-indexing

维护 repo 里所有产出 asset 的索引，让每个 asset 可被检索、可追溯到它的 commit/config/run，并能报告 stale/缺元数据的 asset。**只登记，不搬运字节。**

## 适用边界

适用：新 checkpoint/dataset/table/figure 产生、需要盘点或出 stale report、发现索引与磁盘不一致时。
不适用：需要删除或移动实际文件（禁止；只能出 archive-recommendation 供人类执行）。

## 输入 / 输出 artifact

- 输入：新产出的 asset 文件及其来源（run、config、commit）。
- 输出 / 维护：
  - `lab/artifacts/*.yaml`
  - `lab/models/checkpoint-index.yaml`
  - `lab/data/dataset-index.yaml`
  - `deliverables/index.md`
  - stale asset report（写入 `lab/artifacts/` 下的 report 文件）。

## 需要读取的 ledger

- `.agent/artifact-policy.md`（索引字段、归档规则、命名）。
- 现有各 index YAML，用于 diff 出缺口。

## 允许修改的路径

- `lab/artifacts/*.yaml`
- `lab/models/checkpoint-index.yaml`
- `lab/data/dataset-index.yaml`
- `deliverables/index.md`
- 其余一律只读；**任何 asset 的 bytes 不得删除/移动**。

## 步骤

1. 发现 asset：定位新文件与其来源 run/config/commit。
2. 为每个 asset 记录关键字段（具体字段名以对应 index yaml 的实际 schema 为准，不同资产类型略有差异；以字段最全的 `result-index.yaml` 为例）：`id` / 描述性字段（`summary`，图表/模型对应 `caption`/`name`）/ `storage_path`(或 `source_path`) / `how_to_inspect`(如何检视) / `commit` + `config` + `run_id`(可复现三元组；图表/模型/checkpoint 里对应字段是 `generated_by_run`/`trained_by_run`/`from_run`) / `supports`(依赖/支持哪个 claim，图表里是 `supports_claim`) / `status` / `missing_metadata` / `archive_recommendation`(checkpoint 里是 `archive_after`)。
3. 写入对应 index YAML；在 `deliverables/index.md` 挂上对外可见的交付物。
4. stale 扫描：对照磁盘与索引，标记孤儿文件、缺元数据、过期 asset，产出 stale asset report。
5. 对可归档者只写 `archive-recommendation`，交人类处置，绝不自行移动。

## 验证命令

```
python scripts/validate-governance.py
python scripts/check-anatomy-drift.py
```

## 失败时的 handoff

- 索引与磁盘不一致且无法安全判断：在 report 标 `needs-human` 并按 `.agent/templates/handoff.md` 升级。
- 缺关键元数据（无法回溯 commit/config/run）：记 `missing-metadata`，不猜测填充。
