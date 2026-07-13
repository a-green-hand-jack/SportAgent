# Claude Code 入口

<!-- template:begin -->

> 薄路由。真正的 doctrine 在 `AGENTS.md` 与 `.agent/`，不要在这里堆第二套规则。

## 先读

1. `AGENTS.md`
2. `.agent/AGENTS.md`
3. `memory/current-status.md`（若存在）
4. 结构探索前读 root `ANATOMY.md`

## 项目能力是 repo-local

- `.claude/agents/` — 项目专属 subagents
- `.claude/skills/` — 项目专属 workflows
- `.claude/commands/` — 项目专属 slash commands
- `.claude/hooks/` + `.claude/settings.json` — lifecycle 约束与权限
- `.codex/` + `.agents/` — 从 `.claude/` 生成的 Codex adapters（改 canonical 后跑 `python scripts/sync-codex-adapters.py`）

除非 human 明确要求，不要用 user 全局的 agents/skills/hooks 承载本项目行为。

## 安全（硬边界，详见 `.agent/action-boundary.md`）

- 不编辑/删除 `lab/data/`、`lab/runs/`、`lab/models/` bytes、checkpoints、wandb、远端产物、`lab/infra/private/`，除非明确要求。
- 不启动/kill/restart 长训练或远端作业。
- 不开 PR / merge / release / 改远端基础设施，除非拿到 human 批准。`git push`：topic/实验分支 `allow`，`main`/`master` 需 `CLAUDE_ALLOW_PUSH_MAIN=1` / `CODEX_ALLOW_PUSH_MAIN=1` 显式放行。
- 不无理由新增依赖。

## 验证

- 优先跑 repo validator：`python scripts/validate-governance.py`（或 `check-agent-harness.py` / `check-anatomy-drift.py`）。
- 只跑定向测试；报告确切命令与输出。
- 不声称实验结果，除非有 run id、config、commit、artifact path、metric source。

## Python

- 优先用 `uv`（`uv run` / `uv add` / `uv sync`）。

<!-- template:end -->

<!-- 项目自定义区（template:end 之后，sync 不碰）：下游在此追加本项目特定内容；template:begin/end 块内是模板拥有的内容，如需改动请走 template-feedback 上报，勿在此直接改块内。 -->

## SportAgent 路由

当前没有产品实现。先读 `PROJECT.md`、`memory/current-status.md` 与
`human/briefs/active/20260713-open-source-base-selection.md`；在 human 接受开源底座决策前，
只做研究、设计和小型选型计划，不创建新的产品框架。仓库根 `scripts/` 当前仅用于治理验证。
