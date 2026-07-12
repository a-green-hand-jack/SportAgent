# lab/data/ — Claude Code 路由

数据索引层，薄路由。

## 读文件顺序

1. `ANATOMY.md` — index 与子目录关系。
2. `AGENTS.md` — 允许 / 禁止（重点：bytes 不进 Git）。
3. `README.md` — 内容一览与入口。

## 关键约束

- 只存 manifest / checksum / schema / task-set；大 bytes 由根 `.gitignore` 覆盖，不进 Git。
- manifest 与 checksum 需对应同一数据版本。
- 改动后跑 `python scripts/validate-governance.py`。
