---
related_files:
  - ../ANATOMY.md
  - src/ANATOMY.md
  - imported/SportAgent/pyproject.toml
maintenance: |
  Template scaffold. 子目录结构变化时同 commit 更新本文件与 src/ANATOMY.md。
  真实代码落地前不放 file:line 引用。
---

# lab/code/ ANATOMY

## What this is

实现层。模板预留五个通用子目录；已迁移的 SportAgent 作为完整产品单元位于 `imported/`。

## Composition

Parent: `lab/`（见 `../ANATOMY.md`）
Children:

| 子目录 | 职责 | 独立 anatomy |
| --- | --- | --- |
| `imported/SportAgent/` | Fitness Agent 产品代码、数据、测试、文档与 uv 元数据 | 原项目文档 |
| `src/` | 模型/数据/训练/评估源码 | `src/ANATOMY.md` |
| `configs/` | 配置文件 | README only |
| `scripts/` | 脚本 | README only |
| `tests/` | 测试 | README only |
| `experiments/` | 实验入口 | README only |

## Connections（意图）

- `imported/SportAgent/tests/` 覆盖 `imported/SportAgent/src/fitness_agent/`。
- `imported/SportAgent/scripts/` 调用同一产品单元的源码与数据。
- 运行时的路径/存储由 `../infra/` 提供，不在本层硬编码。

## State

本层不持久化运行产物；产物索引在 `../artifacts/`、`../runs/`、`../models/`。

## Notes

- 具体调用关系与 line-addressed citation 落在 `src/ANATOMY.md`，待真实代码补全。
