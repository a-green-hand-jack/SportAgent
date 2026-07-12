# Session 协议

一次标准 session 的生命周期。不要把 session hygiene 交给 human 记忆。

## 1. 开始：定义目标、停止条件、状态文件

每个 session 开头写清楚（模板见 `.agent/templates/session-brief.md`）：

```
Objective:        这个 session 要精确完成什么？
Success criteria: 什么可观察证据证明成功？
Scope:            Allowed paths / Forbidden paths
Context budget:   >60% 先 checkpoint
Verification:     命令 / metric / run id / 期望输出
State files:      current-status / session-tree / plan doc / branch
```

好目标可收敛（「验证 Fig.3 latent interpolation 是否与 paper 一致」）；坏目标发散（「帮我看看这个项目」）。

## 2. 交互式中文 plan doc

非几分钟小任务，先让 `interactive-plan-writer` 写 `plans/<YYYYMMDD>-<slug>.zh.md`（模板见 `.agent/templates/plan-doc.zh.md`）。human 在文件里批注 → Claude 读 diff → 收敛 plan → 必要时小 commit。plan doc 是当前 session 的锚点。

## 3. 探索（read-only first）→ 4. 计划（先拆边界）→ 5. 实现（小步）→ 6. 验证（fresh evidence）

- 探索用只读模式 / `repo-researcher`，返回证据与 plan，不改。
- 计划必含：任务拆分、每任务文件所有权、冲突风险、验证命令、回滚方式。不接受「我会改相关文件」。
- 实现只做一步，跑最小测试；non-trivial 走 worktree/PR。
- 验证输出：changed files / commands run / test result / remaining risks / evidence paths（实验再加 commit/config/run id/checkpoint/split/metric source）。

## 7. 阶段边界（Claude 主动提醒）

探索→实现、实现→review、debug 多次失败、任务树 >2 子任务、context 到阈值、结果→paper claim：用 `session-boundary-agent`，更新 session-tree，决定 continue/compact/clear/branch/fresh reviewer，并写下一个确切 prompt。

## 8. 结束：写状态，不靠记忆

用 `checkpoint-writer` 更新 `memory/current-status.md`，10 行总结 Done / Evidence / Open risks / Next exact action。plan doc、branch status、artifact index、ledger 若有变化，同一结束动作里更新。
