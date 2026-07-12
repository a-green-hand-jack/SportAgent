# Release Agent 边界（仅当本 repo 交付 agent 产品时适用）

如果 `PROJECT.md` 勾选了「包含内层 release agent」，必须区分两套东西，不要混成一个长 prompt。普通 ML 研究 repo 可忽略本文件。

## 两层

```
外层 Claude Code development harness
  目的：让 Claude Code 更好地开发这个 repo。
  位置：AGENTS.md · CLAUDE.md · .claude/ · .agent/（本目录多数文件）· scripts/

内层 release agent
  目的：这个 repo 最后要发布/评估/交付的 agent 本身。
  位置：lab/code/src/ · evals/ · traces/ · deliverables/release/ · release-gates
```

## 内层 agent 应有独立契约（与外层分开）

- behavior contract（产品 agent 的行为）
- action boundary（产品 agent 的动作边界）
- context policy（产品 agent 的上下文策略）
- tool-skill interface（产品 agent 的工具接口）
- trace-eval loop（capability evidence chain：claim → trace → eval → verdict）
- human gates（产品 agent 的人类审批点）
- production control plane（上线控制面）

## 分离清单

- 内层 agent 的 anatomy / validator / trace-eval / human gate 与外层**不共用**。
- 「开发时约束 Claude Code 的规则」属于 repo editing harness；「产品 agent 的行为契约」属于 release artifact。
- capability claim 必须有 evidence chain 支撑，进 `lab/research/claims.yaml` + `lab/research/release-gates.yaml`。

> 本模板默认**只提供边界，不预设内层 agent 结构**。真要交付 agent 产品时，另建 repo-local skill/subagent 承载内层脚手架（并在 `lab/research/` 建独立 trace-eval 证据链），不要把内层结构塞进外层 harness。
