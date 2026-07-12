---
related_files:
  - ../ANATOMY.md
maintenance: |
  Template scaffold. index/schema 字段或子目录约定变化时同 commit 更新本文件。
  数据 bytes 受根 .gitignore 覆盖，不进 Git，也不在此引用。
---

# lab/data/ ANATOMY

## What this is

数据索引层。把数据集的位置、清单、校验和、任务集与 schema 结构化，让代码与研究事实可追溯地引用数据，而**不把大 bytes 放进 Git**。当前为 template scaffold。

## Composition

Parent: `lab/`（见 `../ANATOMY.md`）
Children:

| 子目录 / 文件 | 职责 |
| --- | --- |
| `dataset-index.yaml` | 数据集总索引 |
| `manifests/` | 每数据集清单 |
| `checksums/` | 校验和 |
| `task-sets/` | 评测/实验任务集 |
| `schemas/` | 数据结构 schema |

## Connections（意图）

- `../code/src/` 的数据模块按 `manifests/` + `schemas/` 加载数据，按 `checksums/` 验证。
- `task-sets/` 供 `../evals/` 使用。
- 实际 bytes 存于外部（根 `.gitignore` 覆盖），仅由 manifest 指向。

## State

| 路径 | 写入者 | 含义 |
| --- | --- | --- |
| `dataset-index.yaml` / `manifests/` / `checksums/` / `schemas/` | agent + human | 数据指针与校验，非 bytes |

## Notes

- manifest ↔ checksum 必须同版本一致，否则 validator 拦截。
- 校验：`python scripts/validate-governance.py`。
