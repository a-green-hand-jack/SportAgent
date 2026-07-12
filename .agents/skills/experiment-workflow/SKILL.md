---
name: experiment-workflow
description: 当要跑一个实验或复现一篇 paper 时，用来写 experiment card、登记 ledger、准备（但不擅自运行）launch 命令、只读监控、写 run summary 并把达标结果收进 evidence。
---

> Codex adapter: generated from `.claude/skills/experiment-workflow/SKILL.md`. Do not edit this copy by hand; run `python scripts/sync-codex-adapters.py`.

# experiment-workflow

实验的全生命周期：先立卡登记，再准备 launch 命令交人类运行，用只读监控看 bounded 状态，跑完写 run summary，达到证据门槛才进 evidence / 论文。paper 复现同样适用。

## 适用边界

适用：训练/评测实验、消融、paper reproduction。
不适用：无需计算的分析；擅自启动长任务（launch 是 human gate）。

## 输入 / 输出 artifact

- 输入：实验假设 / 待复现的 claim。
- 输出：
  - experiment card（`.agent/templates/experiment-card.md`）
  - `lab/research/experiment-ledger.yaml` 登记条目
  - run summary（`.agent/templates/run-summary.md`）
  - 达标后进 `evidence/` 或论文素材。

## 需要读取的 ledger

- `lab/research/experiment-ledger.yaml`（现有实验、避免重复）。
- `.agent/human-gates.md`（launch 审批点）。
- `.agent/artifact-policy.md`（产出如何登记，衔接 artifact-indexing）。

## 允许修改的路径

- `lab/research/experiment-ledger.yaml`
- experiment card / run summary 文件
- `evidence/`（仅达标后）
- **不得擅自执行 launch 命令。**

## 步骤

1. 写 experiment card：假设、变量、成功判据、预算。
2. 登记 `lab/research/experiment-ledger.yaml`。
3. 三层目标（对 paper 复现同样适用）：读懂 claim → 找到对应实现 → 跑最小 smoke 验证链路。
4. 准备 launch 命令但不运行；交人类（human gate）启动。
5. 只读监控：用 experiment-monitor 观察 bounded 状态，不改运行中的 job。
6. 跑完写 run summary（`.agent/templates/run-summary.md`）；产出物交 artifact-indexing 登记。
7. 达到证据门槛才收进 `evidence/` 或论文；未达标只记结论不夸大。

## 验证命令

```
python scripts/validate-governance.py
```

## 失败时的 handoff

- 实验失败/结果异常：在 run summary 如实记录，按 `.agent/templates/handoff.md` 升级。
- smoke 都跑不通（复现受阻）：停在第三层，记录卡点，不伪造结果。
