# .agent/ — repo-local doctrine 索引

> 「这个 repo 如何允许 agent 工作」的版本化规则。所有 agent 在 `AGENTS.md` 之后读这里。

doctrine 是分文件的，每个文件一个关注点，短而稳定、可 review、可被 validator 引用。

## 读取顺序

1. `principles.md` — 不可协商的心智模型（12 条）。
2. `behavior-contract.md` — agent 的默认行为契约。
3. `action-boundary.md` — 硬边界：不能做 / 要问 / 可做。
4. `human-gates.md` — 外部副作用的人类审批点。
5. `context-memory-policy.md` — 上下文预算与落盘规则。
6. `session-protocol.md` + `session-tree-protocol.md` — session 生命周期与分支树。
7. `anatomy-protocol.md` — 结构地图与防漂移。
8. `model-routing-policy.md` — subagent 的 model/effort 预算路由。
9. `tool-skill-interface.md` — 何时用 shell / skill / subagent / MCP。
10. `repo-editing-guardrails.md` — 改 repo 的门禁流程。
11. `artifact-policy.md` — dataset/checkpoint/table/figure 索引与归档。
12. `claude-code-recipe-policy.md` — 从 human-cc trace 提炼可复测 recipe。
13. `repo-documentation-topology.md` — 导航四件套的分工与放置规则。
14. `release-agent-boundary.md` — 仅当本 repo 交付 agent 产品时适用。
15. `autonomous-window.md` — human 授权无人值守窗口的协议：放宽 permission、保留 hook 地板。
16. `template-stress-test-policy.md` — 模板自身机制漂移的防线：变更幅度 → 测试深度分级，
    多 case 登记账定位。
17. `template-versioning-policy.md` — 模板版本(semver)判级契约 + 上下游反馈同步四站闭环
    （下游上报 issue → 上游发版 → sync 追平）。

## 模板与清单

- `.agent/templates/` — launch packet、experiment card、run summary、plan doc、branch status、handoff。
- `.agent/checklists/` — compact 前、并行前、session 边界、每周维护。

## 与其他平面的关系

- doctrine 说「为什么这样限制」；`.claude/settings.json` / `.codex/config.toml` / `.codex/rules/` 让工具加载权限与 hooks；`scripts/` 验证没漂移。三者必须一致。
