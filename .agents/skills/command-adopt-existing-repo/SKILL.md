---
name: command-adopt-existing-repo
description: "Codex adapter for Claude slash command /adopt-existing-repo - 分步迁移已有 Git repo，使其收敛成本模板形态并生成 adoption proof"
---

# command-adopt-existing-repo

Codex does not load project `.claude/commands/*.md` files as custom slash commands.
Use this skill when you would have used `/adopt-existing-repo` in Claude Code.

Canonical source: `.claude/commands/adopt-existing-repo.md`. Do not edit this adapter by hand; edit the
Claude command and run `python scripts/sync-codex-adapters.py`.

把 `$ARGUMENTS` 指向的已有 Git repo 迁移成本模板形态。默认使用 conservative policy：
不删除、不覆盖、不移动受保护 bytes；不可判断时停下并写报告。

建议参数格式：

```text
/adopt-existing-repo /path/to/repo --project-name <slug> --test-command "<cmd>"
```

执行：

1. 确认目标是 Git repo，且当前操作发生在迁移分支/worktree 中。
2. 运行：

   ```bash
   python scripts/adopt-existing-repo.py $ARGUMENTS --phase all --policy conservative
   ```

3. 运行：

   ```bash
   python scripts/check-adoption-integrity.py /path/to/repo
   ```

4. 汇报：
   - state dir：`lab/docs/audits/template-adoption/state/`
   - report：`lab/docs/audits/template-adoption-report.md`
   - integrity / governance / original test return code
   - blockers（如有）

不要 push、开 PR、merge 或 release；这些仍走 human gate。
