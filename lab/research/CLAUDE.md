# lab/research/ — Claude Code 路由

研究事实层，薄路由。

## 读文件顺序

1. `ANATOMY.md` — 各 YAML 的角色与证据链。
2. `AGENTS.md` — 允许 / 禁止（重点：不得 overclaim）。
3. `README.md` — 证据分层与入口。

## 关键约束

- 证据分层：`log < metric < table < figure < paper claim`；claim 强度 ≤ 最强证据。
- 交付看 `release-gates.yaml` + `claims.yaml`，不超出 `evidence.yaml`。
- 改 YAML 后跑 `python scripts/validate-governance.py`。
