# 行为契约

agent 在本 repo 的默认行为。与 `action-boundary.md`（硬边界）互补：这里是「怎么做才对」。

## 默认工作循环

```
读 doctrine / current-status / 最近 ANATOMY
→ 提出最小改动（先 plan，不急于改）
→ 同步更新 contract / manifest / 实现 / anatomy / ledger
→ 跑 harness validator + 定向测试
→ 写 evidence / memory 更新
→ 仅在需要时请求外部副作用批准
```

## 探索优先只读

复杂任务先进只读/plan 模式，映射「在哪里实现」，返回证据与 plan，不急着改。用 `repo-researcher` subagent 做隔离探索。

## 小步实现，小步验证

- 一次只做 plan 里的一步；改完跑最小相关测试。
- 失败先停下总结失败，再做更大改动，不要在失败上叠失败。
- non-trivial edit 走 `issue -> branch -> worktree -> PR`（见 `repo-editing-guardrails.md`）。

## 输出纪律

- 报告确切命令与输出，不复述「大概通过了」。
- subagent 的长日志写文件（`.claude/agent-reports/`），主线程只接摘要。
- main agent 负责最终 verification；不因为 subagent 说 done 就相信。

## 文档默认语言

- 所有书面文档默认使用中文：报告（含 `.claude/agent-reports/`）、review、`memory/` 状态文件、`ANATOMY.md` 正文、commit message 正文等。
- 例外仅当 human 明确要求使用其他语言时才切换；不要自行假设「英文更专业/更通用」而默认英文。
- 代码、路径、命令、标识符、专有技术术语按其自然形式书写，不受此规则约束——这条规则管的是行文语言，不是代码。

## 研究事实纪律

任何进入 `lab/research/evidence.yaml` / `deliverables/` 的结论，必须能回答：来自哪个 command / commit / run id / config / checkpoint / data split / table-figure，且是否经 fresh verifier。见 `artifact-policy.md`。

## 主动维护，不靠 human 记忆

在自然断点主动：更新 `memory/current-status.md`、维护 session tree、维护 artifact index、提示 session 边界。human 可以偷懒，agent 不能假设 human 记得。
