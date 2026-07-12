# lab/artifacts/ — Claude Code 路由

产物索引层，薄路由。

## 读文件顺序

1. `ANATOMY.md` — 各 index 的角色与引用关系。
2. `AGENTS.md` — 允许 / 禁止（重点：只存 index，不存 bytes）。
3. `README.md` — index 一览。

## 关键约束

- 只登记 index，bytes 永不进 Git。
- index 供 `../research/evidence.yaml` 追溯。
- 改动后跑 `python scripts/validate-governance.py`。
