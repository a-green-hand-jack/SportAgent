# CHANGELOG

> 模板框架层的版本历史。判级规则见 `.agent/template-versioning-policy.md`。

## v1.3.0 (MINOR)

- agent spawn skill（Phase 3）：发现 list_agents + 两层交代 + Paseo-tab launcher（出生即命名 --title/--env）+ agent_name_set --register 登记子 agent

## v1.2.0 (MINOR)

- agent 身份/命名 Phase 1+2：statusline 🤖 名字段 + 自命名默认开启（paseo agent update）+ memory/agents-roster 花名册 + 自知 hook
  Closes #20

## v1.1.0 (MINOR)

- 主动上下文调配三块信号 hook（窗口感知 statusline→缓存→hook；Codex 表面对等 UserPromptSubmit/PostCompact）
  Closes #10

