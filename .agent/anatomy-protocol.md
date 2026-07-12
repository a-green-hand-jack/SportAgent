# ANATOMY 协议

`ANATOMY.md` 是给 coding agent 的结构地图，不是 README、不是教程、不是设计长文。它防止 repo 膨胀、结构漂移和 ownership 误判。

## 回答的问题

```
这个目录代表什么概念？哪些文件拥有关键行为？谁调用谁？
哪些状态会持久化？结构变化时哪些地图必须同步更新？
```

## 规则

- 根 `ANATOMY.md` 只做 router：列复杂目录及其子 anatomy，不解释全系统。
- **只有复杂目录**才有自己的 `ANATOMY.md`：多文件协作、跨模块调用、持久状态、生命周期、路由、schema、workflow、权限、或 agent 需独立推理的目录。
- single-file trivial helper、空目录、静态资源、无独立概念边界的 leaf 目录**不要**写 placeholder anatomy。
- 每个结构 claim 尽量引用代码坐标：`path/to/file.py:42` 或 `:42-90`。
- 目标 ~80 行，硬上限 ~120 行。写不短通常是代码边界不清，不是文档该加长。
- **same-commit rule**：移动/改名/拆分/合并/删除文件或函数、改 ownership/调用关系/持久状态 shape/lifecycle/routing/workflow，都算结构改动，必须同 commit 更新相关 anatomy。
  由 `scripts/check-same-commit.py` 机器强制（在「有自己 anatomy 的目录」里 A/D/R 文件却没同变更集更新该 anatomy → 拦）：pre-commit hook（`.githooks/`）+ CI 各查一道。逃生 `SAME_COMMIT_SKIP=1` / `--no-verify`（文档卫生，非安全地板）。
- refactor 前先 grep 被动文件名在所有 `ANATOMY.md`、index YAML、ledger 里的引用。

## 模板

见 `.agent/templates/anatomy.md`。

## Drift checker 的边界

`scripts/check-anatomy-drift.py` 只能挡 missing file / out-of-range line；语义是否仍正确要 agent 打开代码行验证。

## 模板 repo 的特例

本模板里许多目录是**空脚手架**。它们的 `ANATOMY.md` 描述**意图结构**并显式标注「template scaffold」，暂不放指向不存在代码的 `file:line` 引用——等真实代码落地再补 line-addressed citation，避免 citation rot。
