# .claude/ — Claude Code 入口

<!-- template:begin -->

薄路由。

- 需要隔离/并行/限工具 → 看 `agents/`（先经 `.agent/model-routing-policy.md` 选 tier）。
- 反复出现的流程 → 看 `skills/`。
- 权限与 lifecycle 约束 → `settings.json` + `hooks/`。
- subagent 长报告写 `agent-reports/`，主线程只接摘要。

不要用 user 全局能力承载本项目行为。

<!-- template:end -->

<!-- 项目自定义区（template:end 之后，sync 不碰）：下游在此追加本项目特定内容；template:begin/end 块内是模板拥有的内容，如需改动请走 template-feedback 上报，勿在此直接改块内。 -->
