# lab/infra/ — Claude Code 路由

运行环境层，薄路由。

## 读文件顺序

1. `ANATOMY.md` — 子目录与职责。
2. `AGENTS.md` — 允许 / 禁止 / 禁止路径。
3. 需要时读 `permissions/`（权限理由）、`paths/`、`launch/`。

## 关键约束

- `private/` 永不进 Git，永不读取外泄。
- 启动是人类闸门：`launch/` 命令由人执行，不自动跑。
- 放宽权限须在 `permissions/` 留 owner + 理由 + 验证。
