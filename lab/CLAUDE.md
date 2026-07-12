# lab/ — Claude Code 路由

本目录是研究控制面根，薄路由。

## 读文件顺序

1. `ANATOMY.md` — 本层结构地图与各子目录 router。
2. `AGENTS.md` — 允许 / 禁止 / 必须验证 / 禁止路径。
3. `README.md` — 子层一览与常见入口。
4. 进入目标子目录后，先读该目录的 `CLAUDE.md` / `ANATOMY.md`。

## 关键约束（细节见 AGENTS.md）

- 大 bytes 不进 Git，只登记 index/manifest/summary。
- `infra/private/` 永不进 Git；启动作业是人类闸门。
- 交付不得超出 `research/evidence.yaml` 的证据。
- 治理改动后跑 `python scripts/validate-governance.py`。
