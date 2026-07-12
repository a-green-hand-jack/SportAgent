# 书面文档默认使用中文

## Context

某次 agent session（不同分支）里，agent 写了两份英文报告，而本 repo 其余文档
（`AGENTS.md`、`ANATOMY.md`、`DESIGN.md`、`memory/` 模板等）全部是中文。human 是中文使用者，
希望书面产出与 repo 既有文档语言一致，而不是每次都要靠 review 时口头纠正。需要把这个偏好
固化为可被 fresh session 读到的规则，而不是停留在某一次的口头纠正。

## Decision

书面文档默认使用中文：报告（含 `.claude/agent-reports/`）、review、`memory/` 状态文件、
`ANATOMY.md` 正文、commit message 正文等。仅当 human 明确要求使用其他语言时才切换。

代码、路径、命令、标识符、专有技术术语不受此规则约束，按其自然形式书写（不必翻译）。

固化位置：`.agent/behavior-contract.md`（「文档默认语言」一节）。

## Consequences

- 好处：书面产出与 repo 既有文档语言一致，减少 review 时的语言纠正往返；规则可被任意 fresh
  session 读到，不依赖聊天记忆。
- 代价：几乎没有——代码/命令/标识符不受影响，只是行文语言的默认值。
- 约束：若某次任务 human 明确要求英文（或其他语言）输出，以该次明确要求为准，不与本决策冲突。

## Status

accepted
