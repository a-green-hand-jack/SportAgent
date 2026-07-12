# agent-identity —— agent 命名与身份 doctrine

> 多 agent 并行（尤其 Paseo 多标签页）时，每个 agent 需要一个人类可读、**一眼看出「谁·在做什么·对什么」**的名字，供 human↔agent 与 agent↔agent 交流。本文是命名契约；机制（statusline 显示、自命名、roster、spawn skill）分阶段落地，见 `plans/20260712-agent-identity-and-spawn.zh.md`。

## 名字格式

```
<persona>·<动作字>·<focus>
```

- **persona**：角色人格（下表），给「这是谁/哪类活」。
- **动作字**：单字动词，给显式动作（读名即知在 investigate / build / review …）。
- **focus**：话题短标签（kebab 或短中文），给「对什么」。

例：`师爷·审·窗口感知`＝「师爷（把关者）· 审（审查）· 窗口感知（话题）」。

## persona ↔ 动作 映射

| 做什么 (action) | persona | 动作字 | 覆盖的 agent 家族 | 示例名 |
| --- | --- | --- | --- | --- |
| 调查/侦察 investigate | **斥候** | 查 | explore · repo-researcher · tracer · debugger · document-specialist | `斥候·查·codex额度` |
| 改代码/实现 build | **干将** | 改 | executor · feature-worker · code-simplifier | `干将·改·auth重构` |
| 审查/把关 review | **师爷** | 审 | code-reviewer · critic · verifier · security-reviewer · zh-review-gate | `师爷·审·窗口感知` |
| 规划/统筹/协调 plan | **都督** | 统 | planner · architect · analyst · interactive-plan-writer | `都督·统·发版` |
| 记录/文档 document | **主簿** | 记 | repo-doc-steward · checkpoint-writer · writer · artifact-librarian | `主簿·记·anatomy` |
| 测试 test | **巡检** | 测 | test-engineer · test-runner · qa-tester | `巡检·测·e2e` |
| 实验/数据 experiment | **博士** | 验 | scientist · experiment-orchestrator · experiment-monitor | `博士·验·CFD数据` |
| 设计 design | **画师** | 设 | designer | `画师·设·登录页` |
| git/整合 integrate | **校书** | 并 | git-master（校书郎＝校勘/合并版本，贴合 merge/rebase） | `校书·并·main合流` |

规则：
- **唯一性**：同 persona 多开靠 focus 区分（`师爷·审·窗口感知` vs `师爷·审·codex`）；仍冲突则追加短 id。
- **生命周期**：agent 结束/归档在 roster 标 done，不立即删（留痕）。

## 名字怎么获得 / 怎么读到（解析优先级）

统一由 `.claude/hooks/agent_identity.py` 解析（statusline `🤖` 段调用）：

1. **`AGENT_NAME` 环境变量** —— launcher / human 显式设（最高优先）。
2. **`.agent-identity` 文件**（worktree 根，首行）—— Phase 2 自命名会写这里；也可手动写。
3. 都没有 → 不显示 `🤖` 段（优雅降级）。

> Paseo 集成（用 `PASEO_AGENT_ID` + `paseo whoami`/`rename` 自命名、写回 `.agent-identity`、入 roster）在 Phase 2 落地。statusline 高频渲染，故解析只读 env/文件、不每帧 shell out。

## 框架层 vs 运行时（下游继承边界）

- **框架层（=template，随 `template-sync` 继承，正如 `.agent/`/`.claude/`）**：本 doctrine、`agent_identity.py`、statusline `🤖` 段、（Phase 2/3）自命名/自知 hook、roster 表头/格式、spawn skill。
- **运行时（每 agent/每 project 私有，**不**继承、不 sync）**：某个活 agent 的**名字值**（`.agent-identity` / `AGENT_NAME`，已 gitignore）、`memory/agents-roster.md` 的**内容**（`memory/**` 是 project 层）。
- 理由：命名的**能力**该被每个下游继承；但**谁在跑、叫什么**是各 project 自己的运行时状态，不该混到别的 project。

## runtime-agnostic

身份层不依赖 Paseo：`AGENT_NAME` env + `.agent-identity` 文件 + statusline 在纯 Claude Code / Codex 下同样工作；Paseo（`rename`/`send`/`PASEO_AGENT_ID`）只是可选 adapter。
