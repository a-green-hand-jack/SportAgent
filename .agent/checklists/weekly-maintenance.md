# 每周维护清单

```
Claude Code:
- claude --version
- /usage 看 24h / 7d subagent-heavy usage
- statusline 是否显示 context/model/branch/worktree

Project memory:
- memory/current-status.md 是否短且最新
- lab/research/evidence.yaml 是否只含已确认结果
- CLAUDE.md 是否过长
- .agent/ / .claude/skills/ 是否有过时流程

Experiments:
- run summaries 是否齐全
- W&B/MLflow run names 是否可读
- stale checkpoints 是否有保留策略

Git/worktrees:
- git worktree list
- stale worktree 是否可归档
- 未 merge 分支是否有状态说明

Safety:
- lab/data / checkpoints / wandb / lab/runs 是否 gitignored 或只留索引
- permissions 是否保护危险路径
- hooks 是否仍然触发（/hooks 或 debug mode）

Recipes:
- 触发本周 recipe 复测（见 claude-code-recipe-policy.md）
```
