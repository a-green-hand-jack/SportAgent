---
name: worktree-pr-flow
description: 当要落地一处代码改动时，用来走 issue→branch→worktree→实现→更新anatomy/ledger→测试+validator→PR→review→merge→归档的标准流程；push/PR/merge 走 human gate。
---

> Codex adapter: generated from `.claude/skills/worktree-pr-flow/SKILL.md`. Do not edit this copy by hand; run `python scripts/sync-codex-adapters.py`.

# worktree-pr-flow

把一次改动放进受控流程：从 issue 到归档，每一步留证据。默认在 fresh worktree 里实现，隔离工作区。push/PR/merge 是外部副作用，走 human gate。

## 适用边界

适用：任何需要进入版本历史的代码/结构改动。
不适用：纯本地探索、尚未通过 plan 的 scope（先走 interactive-plan-doc）。

## 输入 / 输出 artifact

- 输入：已锁定 scope 的 plan doc / issue。
- 输出：feature branch、fresh worktree、更新的 anatomy/ledger、PR（含 evidence + risks）、归档记录。

## 需要读取的 ledger

- `.agent/repo-editing-guardrails.md`（门禁流程）。
- `.agent/human-gates.md`（push/PR/merge 审批）。
- `.agent/anatomy-protocol.md`（同 commit 更新地图）。

## 允许修改的路径

- worktree 内的目标源码
- 受影响的 `ANATOMY.md` / index / ledger
- push/PR/merge 前不越过 human gate。

## 步骤

1. issue：先有一个可追溯的 issue/plan。
2. branch on correct base：按模式选 base——
   - 单 trunk（pairwise-diffusion 式）：`git worktree add ../wt-<slug> -b <slug> <trunk>`。
   - branch-local mainline（DOLoop 式）：base 为 `mainline/<domain>`，如 `git worktree add ../wt-<slug> -b <domain>/<slug> mainline/<domain>`。
3. fresh worktree：在隔离 worktree 内实现，避免污染主工作区。cwd 不保证跨 Bash 调用稳定持久，每次写操作前先跑 `pwd` + `git rev-parse --show-toplevel` 核对确实在分配的 worktree 里，不要只在任务开头 `cd` 一次就假设之后都对。
4. 实现 + 同 commit 更新 anatomy/ledger（见 anatomy-drift-control）。
5. 定向测试 + validator：只跑相关测试，跑 validator。
6. PR：写清 evidence（跑了什么、结果）与 risks；**human gate**。
7. review → merge（human gate）→ 归档：更新索引，清理 worktree（`git worktree remove ../wt-<slug>`）。

## 验证命令

```
python scripts/validate-governance.py
python scripts/check-anatomy-drift.py
```

## 失败时的 handoff

- 测试/validator 红：不 push，在 branch 修；无法定位则按 `.agent/templates/handoff.md` 升级。
- base 选择存疑（哪种 mainline 模式）：停下问人类，不擅自选 base。
