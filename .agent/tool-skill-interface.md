# 工具 / Skill / Subagent / MCP 接口

选择「用什么」的默认梯度：能便宜就便宜，能隔离就隔离。

## 梯度

```
1. 直接 shell / grep / rg / glob   —— tier 0，最省 context
2. repo-local skill (.claude/skills/ canonical；.agents/skills/ for Codex) —— 反复出现的流程，按需加载
3. subagent (.claude/agents/ canonical；.codex/agents/ for Codex)      —— 需要隔离上下文 / 限制工具 / 并行
4. MCP / connector / CLI           —— 外部系统访问
```

## 何时开 skill 而不是塞进 prompt

流程会反复出现、有明确输入输出 artifact、要读特定 ledger、有验证命令、有失败 handoff —— 做成 skill，避免每个 session 都把它塞进基础 context。

## 何时开 subagent

需要保护主会话 context、限制工具、复用专用配置、或并行探索。**不**适合：无边界大任务、需要完整主线程历史（除非显式 fork）、多 agent 同时编辑同一模块、高风险外部操作。

## MCP 原则

- 能用 CLI 解决的通常比 MCP 更省 context。
- MCP 适合结构化接口、权限清楚、重复调用频繁的系统。
- 高权限 MCP（读 secrets / 改数据库 / 发邮件 / 改 issue 状态）必须谨慎，走 human gate。

## 能力必须 repo-local + 有索引

新能力先登记 contract / manifest，再写实现；没有索引的能力不算正式 surface。canonical 定义放 `.claude/`，
Codex adapters 由 `scripts/sync-codex-adapters.py` 生成到 `.codex/` / `.agents/`，验证进 `scripts/`。
