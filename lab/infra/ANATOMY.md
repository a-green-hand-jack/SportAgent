---
related_files:
  - ../ANATOMY.md
maintenance: |
  Template scaffold. 子目录约定变化时同 commit 更新本文件。
  private/ 内容永不进 Git，也不在本文件引用其具体内容。
---

# lab/infra/ ANATOMY

## What this is

运行环境层。集中管理权限、路径、存储、启动、探针与私密配置，把「代码怎么跑、跑在哪、谁能跑」与实现层解耦。当前为 template scaffold，描述意图结构。

## Composition

Parent: `lab/`（见 `../ANATOMY.md`）
Children:

| 子目录 | 职责 | 文档 |
| --- | --- | --- |
| `permissions/` | 记录 `.claude/settings.json` 与 `.codex/rules` 权限策略的 owner + 理由 + 验证 | README only |
| `paths/` | 路径约定 | README only |
| `storage/` | 存储后端与配额 | README only |
| `launch/` | 可复现启动命令（人类闸门） | README only |
| `probes/` | 环境探针 | README only |
| `private/` | 私密/密钥，永不进 Git | README only |

## Connections（意图）

- `../code/src/` 通过 `paths/`、`storage/` 解析运行时位置，不硬编码。
- `permissions/` 解释根 `.claude/settings.json` / `.codex/rules` 的每条高危能力为何 deny/ask/allow/prompt。
- `launch/` 的命令由 human 执行；产出流向 `../runs/`、`../models/`（bytes gitignore）。

## State

| 路径 | 写入者 | 含义 |
| --- | --- | --- |
| `private/` | human | 密钥/私密配置，永不进 Git |
| `permissions/` | owner | 权限决策的理由与验证记录 |

## Notes

- 高危能力放宽必须留痕：owner、理由、验证方式，三者缺一即为违规。
- 校验：`python scripts/validate-governance.py`。
