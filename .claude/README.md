# .claude/

<!-- template:begin -->

Claude Code 项目能力层，也是 Codex adapter 的 canonical source。项目专属能力放这里，**不装到 user 全局**。

| 目录 | 内容 |
| --- | --- |
| `agents/` | repo-local subagents（执行/协调/维护/演化四层） |
| `skills/` | repo-local workflows（按需加载） |
| `commands/` | 项目 slash commands |
| `hooks/` | 生命周期约束（可执行脚本） |
| `rules/` | 附加 rule 片段 |
| `settings.json` | Claude Code 加载的权限与 hook 配置 |
| `agent-reports/` | subagent 写长报告的地方（主线程只接摘要） |

能力必须有 manifest / owner / verification，见 `.agent/tool-skill-interface.md`。为什么这样限制在 `.agent/`；验证在 `scripts/`。

Codex 读取的 `.codex/agents` 与 `.agents/skills` 由本目录生成；改完 agents / skills / commands 后运行
`python scripts/sync-codex-adapters.py`。

<!-- template:end -->

<!-- 项目自定义区（template:end 之后，sync 不碰）：下游在此追加本项目特定内容；template:begin/end 块内是模板拥有的内容，如需改动请走 template-feedback 上报，勿在此直接改块内。 -->
