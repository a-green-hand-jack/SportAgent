# Session Tree 协议

新 session 不是失忆，而是分支。parent 保留全局目标与任务树，child 只背一个小目标与证据标准。

## 何时分支

一个 session 里出现多个值得独立完成的小任务时，记成树：父节点是当前阶段，子节点是 issue / branch / worktree / 实验 / review / paper section。每个子节点有自己的 allowed/forbidden paths、验证命令、exit condition、handoff。

## clear vs compact vs rewind vs branch

```
/clear    切换无关任务：清当前上下文，session 可 resume。
/compact  继续同一任务但压缩历史。
/rewind   撤回错误方向，或只总结某段历史。
/branch   从父 session 派生子任务，保留父任务树与 child handoff。
```

实践：新研究问题→`/clear`；同任务进下一阶段→checkpoint+`/compact`；多个独立子任务→branch/child session；走错方向→`Esc`/`/rewind`；代码乱→git diff + 显式人类决定 reset。

若当前 surface 不支持 `/branch`，用 `memory/session-tree.md` + 新 session + handoff 文件模拟同样的树。

## 状态文件

- `memory/session-tree.md` — 父目标、当前 phase、children 表、merge 顺序、全局 forbidden、open risks。
- `memory/branches/<slug>.md` — 单分支状态。

由 `session-boundary-agent` 与 `branch-reporter` 维护；human 只需在发现漂移时说「检查 session boundary」或「报告当前 branches」。
