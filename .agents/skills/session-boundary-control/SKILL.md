---
name: session-boundary-control
description: 在阶段切换、context 占用过高、或任务树分叉时，决定 continue/compact/clear/branch/fresh-reviewer 并维护 session 树。
---

> Codex adapter: generated from `.claude/skills/session-boundary-control/SKILL.md`. Do not edit this copy by hand; run `python scripts/sync-codex-adapters.py`.

# session-boundary-control

在 session 生命周期的关键点上做一个显式决策：继续、compact、清空、开分支、还是换一个 fresh reviewer；并把这个决策记进 session 树。

## 适用边界

适用：阶段切换（plan→实现→review）、context 占用逼近预算、任务出现分叉、需要独立视角 review 时。
不适用：任务线性推进且 context 充裕（继续即可，无需仪式）；纯外部副作用（走 human gate）。

## 输入 / 输出 artifact

- 输入：当前 context 占用、所处阶段、任务树形态。
- 输出：更新后的 `memory/session-tree.md`；必要时新增/更新 `memory/branches/<slug>.md`。

## 需要读取的 ledger

- `.agent/session-tree-protocol.md`（分支树语义与命名）。
- `.agent/session-protocol.md`（session 生命周期）。
- `.agent/checklists/session-boundary.md`（边界判定清单）。
- `.agent/context-memory-policy.md`（context 预算与落盘规则）。
- 现有 `memory/session-tree.md`。

## 允许修改的路径

- `memory/session-tree.md`
- `memory/branches/<slug>.md`
- 其余一律只读。

## 步骤

1. 对照 `.agent/checklists/session-boundary.md` 判断当前处于哪种边界。
2. 选动作：continue（同线继续）/ compact（压缩上下文，先按 policy 落盘）/ clear（清空重开）/ branch（分叉出 `<slug>`）/ fresh reviewer（换独立 session 审）。
3. 落盘：compact/clear 前把必要状态写入 memory，避免信息丢失。
4. 更新 `memory/session-tree.md`：记节点、父子关系、动作与理由。
5. branch 时创建 `memory/branches/<slug>.md`，登记该分支的目标与状态。

## 验证命令

```
python scripts/validate-governance.py
```

## 失败时的 handoff

- 若边界判断需要人类拍板（例如是否放弃一条分支）：在 `memory/session-tree.md` 标 `needs-human`，并按 `.agent/templates/handoff.md` 写 handoff。
- compact/clear 前若落盘不完整，禁止执行该动作，先补齐 memory。
