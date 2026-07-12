# lab/infra/ — agent 约束

## 允许

- 读 `permissions/`、`paths/`、`storage/`、`probes/` 以理解并遵守环境约定。
- 在 `paths/`、`storage/`、`probes/` 增改约定文件（需说明 owner 与理由）。
- 在 `launch/` 起草启动命令**草案**，供人类审阅。

## 禁止

- 禁止读、写、提交 `private/` 的任何内容——**永不进 Git**。
- 禁止自行执行 `launch/` 的启动命令：**启动是人类闸门**。
- 禁止放宽 `.claude/settings.json` 或 `.codex/rules/default.rules` 的 deny/ask/prompt 而不在 `permissions/` 记录 owner + 理由 + 验证。

## 必须验证

- 改动权限/启动约定后：`python scripts/validate-governance.py`。
- 结构改动同 commit 更新 `ANATOMY.md`。

## 禁止路径

- `lab/infra/private/**`（永不进 Git，永不读取外泄）。
