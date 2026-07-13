# AGENTS

<!-- template:begin -->

> 所有编码/研究 agent 的 repo 级入口与硬规则。Claude Code 见 `CLAUDE.md`（薄路由指向此处）。

## 进入 repo 先读

1. 本文件 `AGENTS.md`
2. `.agent/AGENTS.md`（doctrine 索引）
3. `memory/current-status.md`（当前状态与 handoff）
4. 结构探索前先读 root `ANATOMY.md`，再读目标目录的 `ANATOMY.md`

## 心智模型

- **Repo 是控制面，chat 是短期意识流。** 长期状态写文件，不写在聊天里。
- **Main agent = PI / tech lead**：定目标、边界、决策、整合、验收。**Subagent = RA**：有限范围的读/写/测/查/监控/总结。
- **隔离先于并行**：并行前先定义 ownership（owned paths / forbidden paths / merge target）。
- **新鲜上下文是质量工具**：探索→plan→实现→review 之间该切 session 就切；用 `memory/session-tree.md` 记树。

## 硬边界（详见 `.agent/action-boundary.md`）

除非 human 明确要求，禁止：

- 编辑或删除 `lab/data/**`、`lab/runs/**`、`lab/models/**` bytes、`checkpoints/**`、`wandb/**`、`lab/infra/private/**`、`.env`。
- 启动、kill、restart 长训练或远端作业。
- 开 PR / merge / release / 改远端基础设施。
- 未经理由地新增依赖。

`git push` 到 topic/实验分支是 `allow`（agent 可做）；push 到 `main`/`master` 由 hook 拦，需 human 显式放行 `CLAUDE_ALLOW_PUSH_MAIN=1` 或 `CODEX_ALLOW_PUSH_MAIN=1`。其余外部副作用一律走 human gate，见 `.agent/human-gates.md` 与 `.agent/autonomous-window.md`。

## 能力是 repo-local 的

项目相关的 agent / skill / command / hook canonical 源放在 `.claude/`，Codex adapters 放在 `.codex/` 与 `.agents/`，不装到 user 全局。行为契约放 `.agent/`，结构地图放 `ANATOMY.md`，门禁放 `scripts/`。

## 验证纪律

- 优先跑 repo validator：`python scripts/validate-governance.py`。
- 只跑与改动相关的定向测试；报告**确切命令与输出**。
- 不给出无 run id / config / commit / artifact path / metric source 的实验结论。
- 结构改动（移动/改名/拆分/合并/改 ownership/状态 shape）必须**同 commit** 更新相关 `ANATOMY.md` 与 ledger。

## 完整 doctrine

- 行为契约：`.agent/behavior-contract.md`
- 动作边界：`.agent/action-boundary.md`
- 上下文/记忆：`.agent/context-memory-policy.md`
- session 协议：`.agent/session-protocol.md` · `.agent/session-tree-protocol.md`
- anatomy 协议：`.agent/anatomy-protocol.md`
- 模型/effort 路由：`.agent/model-routing-policy.md`
- 工具/skill 接口：`.agent/tool-skill-interface.md`
- human gates：`.agent/human-gates.md`

<!-- template:end -->

<!-- 项目自定义区（template:end 之后，sync 不碰）：下游在此追加本项目特定内容；template:begin/end 块内是模板拥有的内容，如需改动请走 template-feedback 上报，勿在此直接改块内。 -->

## SportAgent 项目约定

- 当前没有产品实现；`lab/code/` 仅保留模板骨架，旧 Fitness Agent 原型不属于活动代码。
- 北极星已确定，但产品形态、首期范围和开源底座尚未裁决。底座决策落入 `human/decisions/` 前，不开始产品实现或新增产品依赖。
- 优先选择成熟的传统运动记录/训练规划开源项目，再以薄适配层增加 SportAgent 的 AI 约束推理、计划修订和反馈闭环。
- 根 `scripts/` 属于模板治理；当前只运行治理与研究相关验证。
- `lab/docs/audits/template-adoption*` 与 `human/imported/adoption-conflicts/` 是历史迁移证据，不是当前产品入口。
- 长期分支只保留 `main` 与 `dev`；稳定决策进 `main`，后续 spike/集成先进入 `dev`。
