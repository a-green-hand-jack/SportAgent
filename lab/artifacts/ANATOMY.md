---
related_files:
  - ../ANATOMY.md
  - ../research/ANATOMY.md
maintenance: |
  Template scaffold. index schema/字段变化时同 commit 更新本文件。
  index YAML 由治理流程维护，此处只描述角色与引用关系。
---

# lab/artifacts/ ANATOMY

## What this is

产物索引层。把「产物在哪、是什么、由哪次 run 产生」结构化为一组 index YAML。**只存 index，bytes 在外部存储**。当前为 template scaffold。

## Components（index YAML）

| 文件 | 索引 |
| --- | --- |
| `result-index.yaml` | 结果 |
| `model-index.yaml` | 模型 checkpoint |
| `trace-index.yaml` | 轨迹 |
| `table-index.yaml` | 表 |
| `figure-index.yaml` | 图 |

## Connections（意图）

- 索引条目由 `../runs/`、`../models/` 的产出登记而来（bytes 不进 Git）。
- `../research/evidence.yaml` 引用这些 index 作为证据（table/figure/result 层）。

## State

| 路径 | 写入者 | 含义 |
| --- | --- | --- |
| `*-index.yaml` | agent + human | 产物指针（位置 + checksum + 来源），非 bytes |

## Notes

- 悬空索引（指向不存在产物）应被 validator 拦截。
- 校验：`python scripts/validate-governance.py`。
