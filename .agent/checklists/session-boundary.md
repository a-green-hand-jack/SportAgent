# Session 边界清单

以下情况不要继续沿同一上下文滚：

```
- 探索结束，准备实现。
- 实现结束，准备 review。
- debug 已有多个失败假设。
- 任务树出现 ≥2 个子任务。
- context 进入 repo 阈值（见 context-memory-policy.md）。
- 需要从普通结果 promote 到 paper claim。
```

操作：

```
Use session-boundary-agent.
Update memory/session-tree.md 和相关 branch status。
Decide: continue / compact / clear / branch / fresh reviewer。
在边界前写下确切的下一个 prompt。
```
