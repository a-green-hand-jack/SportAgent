---
related_files:
  - ../ANATOMY.md
  - settings.json
  - statusline.sh
  - skills/coding-agent-quota/SKILL.md
  - skills/coding-agent-quota/scripts/read_agent_quota.py
  - hooks/pre_tool_guard.py
  - hooks/format_changed_python.py
  - hooks/pre_compact_memory_check.py
  - hooks/subagent_report_index.py
  - hooks/zh_review_advisory.py
maintenance: |
  新增/删除 agent、skill、command、hook 时同 commit 更新本表。
  template scaffold：agents/ 与 skills/ 的清单随 repo 演化增删。
---

# .claude/ ANATOMY

<!-- template:begin -->

## What this is

Claude Code 项目能力层的结构地图：哪些能力存在、谁约束谁。Codex adapters 从本目录生成，
见 `.codex/ANATOMY.md` 与 `.agents/ANATOMY.md`。

## Components

| 路径 | 角色 |
| --- | --- |
| `agents/` | subagent 定义。四层：执行 / 协调 / 维护交互 / 演化。 |
| `skills/` | repo-local workflow，每个 `<name>/SKILL.md`。 |
| `skills/coding-agent-quota/` | 读取 Codex / Claude Code quota snapshot，给 agent 路由提供当前窗口与周额度证据。 |
| `commands/` | slash command 定义。 |
| `hooks/pre_tool_guard.py` | `PreToolUse` 硬约束：拦截危险 Bash 与受保护路径写入。 |
| `hooks/format_changed_python.py` | `PostToolUse` advisory：从 Claude/Codex hook 输入识别变更的 `.py` 文件并尝试 `ruff format`。 |
| `hooks/pre_compact_memory_check.py` | `PreCompact` 提醒：检查 `memory/current-status.md` 新鲜度（advisory）。 |
| `hooks/subagent_report_index.py` | `SubagentStop` 提醒：向 `agent-reports/index.md` 追加时间线（advisory）。 |
| `hooks/zh_review_advisory.py` | `PostToolUse(Edit\|Write)` 提醒：`human/reviews/**`、`human/decisions/**`、`lab/docs/audits/**`、`DECISIONS.md` 命中时做便宜的中日韩字符占比启发检查，疑似忘了用中文时提醒派发 `zh-review-gate`（advisory）。 |
| `statusline.sh` | statusLine 命令：model / dir / git branch / worktree / cost 仪表盘（防御式，可删）。 |
| `settings.json` | 加载权限（allow/ask/deny）、statusLine 与 hook 映射。 |
| `settings.local.json.example` | 自主窗口档模板：临时放宽 permission（git-ignored 的 `settings.local.json`）。见 `.agent/autonomous-window.md`。 |
| `agent-reports/` | subagent 报告落盘处（gitignored，仅留 README/.gitkeep）。 |

## Connections

- `settings.json` 的 hooks 映射调用 `hooks/*.py`；`statusLine` 段调用 `statusline.sh`。
- 权限的「为什么」在 `.agent/action-boundary.md` / `lab/infra/permissions/`；漂移检查在 `scripts/check-agent-harness.py`。
- `skills/adopt-existing-repo/` 与 `commands/adopt-existing-repo.md` 调用 `scripts/adopt-existing-repo.py`，
  用 phase gate 把已有 Git repo 收敛成模板形态。
- `scripts/sync-codex-adapters.py` 读取本目录的 agents/skills/commands，生成 `.codex/agents/*.toml`
  与 `.agents/skills/*/SKILL.md`，使 Codex 可发现同一组 repo-local 能力。

## State

| Path | Written by | Meaning |
| --- | --- | --- |
| `.claude/agent-reports/*.md` | subagents | 隔离任务的长报告 |
| `.claude/agent-reports/index.md` | `subagent_report_index.py` | subagent 结束时间线（gitignored） |

## Notes

- hook 在 worktree/desktop/remote surface 下行为可能不一致，高风险 workflow 仍需 permission + Git + manual review 兜底。

<!-- template:end -->

<!-- 项目自定义区（template:end 之后，sync 不碰）：下游在此追加本项目特定内容；template:begin/end 块内是模板拥有的内容，如需改动请走 template-feedback 上报，勿在此直接改块内。 -->
