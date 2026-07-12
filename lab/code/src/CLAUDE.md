# lab/code/src/ — Claude Code 路由

源码层，薄路由。当前为空脚手架。

## 读文件顺序

1. `ANATOMY.md` — 意图结构（模块落地后含 line-addressed citation）。
2. `AGENTS.md` — 允许 / 禁止 / 必须验证。
3. `README.md` — 各模块意图。

## 关键约束

- 路径/私密走 `../../infra/`，数据走 `../../data/` 索引。
- 新增模块同 commit 补 `ANATOMY.md` 的 `file.py:line` 引用。
