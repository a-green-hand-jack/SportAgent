# 上下文与记忆政策

context 是昂贵工作记忆，磁盘是长期记忆。目标是让 fresh session 永远能从 repo 接续。

## Context 阈值（操作习惯，非官方硬限制）

```
0-40%   正常工作。
40-60%  警惕无关历史；不要粘贴大日志/整篇论文/整份源码。
60-70%  完成当前小目标后 checkpoint + compact。
70%+    不开新方向；先落盘状态，再 compact/clear。
80%+    只做恢复动作：写 current-status、export、compact/clear。
```

`/compact` 在 context 满时可能失败——不要等最后一刻。阈值提醒应来自 statusline + `PreCompact` hook + `session-boundary-agent`，不靠 human 意志力。

## 不要塞进上下文

- 5000 行训练日志 → `tail -n 200` / `grep ERROR` / 结构化 parser。
- 整篇 paper / 整份源码 → 给路径、run id、section 名，让 subagent 读后返回 summary。
- 全部实验历史 → 落到 `lab/research/` 与 `lab/artifacts/` 索引。

## 落盘位置（磁盘才是记忆）

| 内容 | 位置 |
| --- | --- |
| 当前状态 / handoff | `memory/current-status.md` |
| session 分支树 | `memory/session-tree.md` |
| branch/worktree 状态 | `memory/branches/<slug>.md` |
| 当前 plan | `plans/<YYYYMMDD>-<slug>.zh.md` |
| 实验事实 | `lab/research/` + `lab/artifacts/` |
| 采用的 CC 工作流 | `memory/current-practices.md` |

## compact 前清单

见 `.agent/checklists/pre-compact.md`。compact 指令要显式声明 preserve（目标/决策/改动文件/测试命令与结果/未解 blocker/下一步/禁改路径）与 discard（冗长日志/死胡同假设/重复工具输出）。
