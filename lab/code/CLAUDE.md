# lab/code/ — Claude Code 路由

实现层，薄路由。

## 读文件顺序

1. `ANATOMY.md` — 本层组件与子目录。
2. `AGENTS.md` — 允许 / 禁止 / 必须验证。
3. 进入 `src/` 前先读 `src/ANATOMY.md`。

## 关键约束

- 私密/密钥属于 `../infra/private/`，不入代码。
- 提交前跑 `tests/`；结构改动同 commit 更新 anatomy。
