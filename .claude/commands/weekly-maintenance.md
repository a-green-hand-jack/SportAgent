---
description: 走一遍每周维护清单：跑治理门禁 + 检查 memory/worktree/artifact/hook 状态
---

按 `.agent/checklists/weekly-maintenance.md` 执行每周维护，并把结果汇总成一份简短报告。
只读 + 报告为主；任何写动作（归档、删索引、降级 recipe）都先提议、等 human 确认。

## 步骤

1. **治理门禁**：跑 `python scripts/validate-governance.py`，报告确切输出。有 error/warning 就列出。
2. **Claude Code**：提醒 human 手动确认 `claude --version` 与 `/usage`（agent 无法代跑）；确认 statusline 是否显示 model/dir/branch。
3. **Project memory**：`memory/current-status.md` 是否短且最新；`lab/research/evidence.yaml` 是否只含已确认结果；`CLAUDE.md` 是否超 80–120 行；`.agent/` / `.claude/skills/` 有无过时流程。
4. **Experiments / artifacts**：用 `artifact-librarian` 生成 stale asset 报告（active 但无 claim/deliverable 关联、superseded 仍标 active、source run 缺失的 table/figure）。只出归档提案，不删。
5. **Git / worktrees**：`git worktree list`；用 `branch-reporter` 汇总 active branch/worktree 的功能分野与 merge target；标出 stale worktree 与未 merge 分支。
6. **Safety**：确认 `lab/data` / `checkpoints` / `wandb` / `lab/runs` 仍被 gitignore 或只留索引；permissions 是否保护危险路径；hooks 是否仍触发（提示 human 用 `/hooks` 或 debug mode 验证）。
7. **Recipes**：按 `.agent/claude-code-recipe-policy.md` 触发本周 recipe 复测；到期未复测的降级或移入 `memory/deprecated-practices.md`。

## 输出

一份 ≤20 行报告：门禁结果 / 需 human 手动确认项 / 待归档提案 / stale 分支 / 到期 recipe / 建议的下一步。不执行不可逆动作。
