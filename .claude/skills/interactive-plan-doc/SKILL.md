---
name: interactive-plan-doc
description: 当一个阶段需要在动手前与人类对齐 scope 时，用来写中文 plan doc、收人类批注、收敛并做 plan revision commit（human gate）。
---

# interactive-plan-doc

把一个阶段的意图写成中文 plan doc，让人类批注，读 diff 收敛，直到 scope/forbidden/verification 清楚后才允许开始实现。

## 适用边界

适用：阶段启动、需要与人类对齐目标与边界、任务足够大值得先规划时。
不适用：微小机械改动；scope 已在既有 plan doc 中锁定且未变。

## 输入 / 输出 artifact

- 输入：阶段目标、上游指令、相关 anatomy/ledger。
- 输出：`plans/<YYYYMMDD>-<slug>.zh.md`，模板见 `.agent/templates/plan-doc.zh.md`。

## 需要读取的 ledger

- `.agent/human-gates.md`（plan revision 的审批点）。
- `.agent/repo-editing-guardrails.md`（改 repo 的门禁流程）。
- 相关 `ANATOMY.md` 与 index YAML（了解现状）。

## 允许修改的路径

- `plans/<YYYYMMDD>-<slug>.zh.md`
- 其余一律只读，直到 plan 通过 human gate。

## 步骤

1. 起草：用 `.agent/templates/plan-doc.zh.md` 写出目标、scope、forbidden、验收/verification、风险。
2. 交人类批注：明确请求 review，不要抢跑实现。
3. 读 diff：把人类批注逐条读进来，识别被改动的意图。
4. 收敛：更新 plan，直到 scope / forbidden / verification 三者都明确无歧义。
5. plan revision commit：作为 human gate，经人类确认后提交定稿。
6. 只有定稿后，才移交实现（可转 worktree-pr-flow / experiment-workflow）。

## 验证命令

```
python scripts/validate-governance.py
```

## 失败时的 handoff

- 人类批注相互冲突或 scope 无法收敛：记录未决项，按 `.agent/templates/handoff.md` 升级给人类澄清。
- 若在未通过 human gate 前已被要求实现：拒绝，回到步骤 2。
