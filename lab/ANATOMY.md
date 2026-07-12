---
related_files:
  - code/ANATOMY.md
  - infra/ANATOMY.md
  - research/ANATOMY.md
  - artifacts/ANATOMY.md
  - data/ANATOMY.md
maintenance: |
  Template scaffold. 本层为 router。子目录结构变化时同 commit 更新对应 anatomy。
  暂不放指向不存在代码的 file:line 引用，真实代码落地再补 line-addressed citation。
---

# lab/ ANATOMY（router）

## What this is

研究控制面根。本文件只做 **router**：指向各复杂子目录的独立 anatomy，不解释全系统。当前为 template scaffold，多数子目录为空脚手架，描述的是**意图结构**。

## 子目录 router

| 子目录 | 概念 | 独立 anatomy |
| --- | --- | --- |
| `code/` | 实现层（src/configs/scripts/tests/experiments） | `code/ANATOMY.md` |
| `infra/` | 运行环境层（permissions/paths/storage/launch/probes/private） | `infra/ANATOMY.md` |
| `research/` | 研究事实层（claims/evidence/ledger/gates） | `research/ANATOMY.md` |
| `artifacts/` | 产物索引层（result/model/trace/table/figure index） | `artifacts/ANATOMY.md` |
| `data/` | 数据索引层（dataset-index + manifests/checksums/task-sets/schemas） | `data/ANATOMY.md` |

## 只有 README 的 leaf 层

`models/`、`runs/`、`traces/human-cc/`、`recipes/claude-code/`、`evals/cc-workflow/`、
`evals/adoption/`、`reports/cc-workflow/`、`docs/{reference,research-narrative,audits}/`
为 leaf/scaffold，只有 `README.md` 或单脚本 smoke，无独立 anatomy（`docs/` 三个子目录的用途见
`human/decisions/20260709-lab-docs-reference-and-external-vendor-placement.md`；`reference/`、
`research-narrative/` 目前无真实内容，暂未物理创建，仅 `audits/` 已落地）。

## State（意图）

| 路径 | 写入者 | 含义 |
| --- | --- | --- |
| `models/`、`runs/` | 训练/运行流程 | bytes 已 gitignore，Git 内仅 index/summary |
| `data/` 大文件 | 数据流程 | bytes 不进 Git，仅 manifest/checksum/schema |
| `research/*.yaml` | agent + human | 结构化研究事实，validate-governance 校验 |

## Notes

- Router 层不承载业务逻辑；跨层调用关系落在各子 anatomy。
- 结构漂移检查：`scripts/check-anatomy-drift.py`；治理校验：`python scripts/validate-governance.py`。
