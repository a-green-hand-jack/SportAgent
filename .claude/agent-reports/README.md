# .claude/agent-reports/

subagent 把长报告写到这里（`<task>.md`），主线程只接摘要——避免大段日志污染主上下文。

- `feature-worker` 写 changed files / tests / risks / merge notes。
- 其他 subagent 按需落报告。
- `index.md` 由 `.claude/hooks/subagent_report_index.py` 在 SubagentStop 时自动追加时间线。
- 这些是**过程产物**，非研究事实；研究事实进 `lab/research/` 与 `lab/artifacts/`。

## Git 边界

报告与 `index.md` **不进 Git**（见 `.gitignore`）；只跟踪本 `README.md` 与 `.gitkeep`。
需长期保留的结论提炼进 `memory/current-status.md` 或对应 ledger。
