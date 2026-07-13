---
related_files:
  - ../ANATOMY.md
  - src/ANATOMY.md
maintenance: |
  Template scaffold. 子目录结构变化时同 commit 更新本文件与 src/ANATOMY.md。
  真实代码落地前不放 file:line 引用。
---

# lab/code/ ANATOMY

## What this is

实现层。模板预留五个通用子目录；当前没有活动产品实现，等待开源底座选型。

## Composition

Parent: `lab/`（见 `../ANATOMY.md`）
Children:

| 子目录 | 职责 | 独立 anatomy |
| --- | --- | --- |
| `src/` | 未来领域适配与 AI 核心源码；当前为空 | `src/ANATOMY.md` |
| `configs/` | 未来候选底座与实验配置 | README only |
| `scripts/` | 未来集成/数据处理脚本 | README only |
| `tests/` | 未来契约、集成和领域评测 | README only |
| `experiments/` | Top 候选的受限 spike | README only |

## Connections（意图）

- 当前无运行时连接。
- 底座选定后，优先通过稳定 API/plugin/event 边界连接上游，而不是复制完整产品树。
- 运行时的路径/存储由 `../infra/` 提供，不在本层硬编码。

## State

本层不持久化运行产物；产物索引在 `../artifacts/`、`../runs/`、`../models/`。

## Notes

- 具体调用关系与 line-addressed citation 落在 `src/ANATOMY.md`，待底座决策和真实代码补全。
