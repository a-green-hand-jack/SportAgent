# human/ — human 与 agent 的协作界面

这是 human 和 agent 在 repo 内**协作的界面**。任务 brief、plan / result / recipe 的评审、轻量决策都发生在这里。

目的很直接：让来自 human 的**可信信息进入 repo，而不是留在聊天窗口里**。聊天记录会丢、会被 compact、fresh session 读不到；写进 `human/` 的东西则成为项目的持久上下文，任何 agent 都能读到并遵守。

## 什么时候来这里

- human 要下任务：写一份 brief 到 `briefs/active/`。
- agent 交出 plan / result / recipe diff，需要 human 拍板：走 `reviews/`。
- 要记录「为什么接受/拒绝某个规则、recipe、架构、实验方向」：写 ADR 到 `decisions/`。
- 收到零散输入（链接、片段、想法）还没归类：先扔 `inbox/`。

## 目录

| 路径 | 内容 |
| --- | --- |
| `briefs/active/` | 进行中的任务 brief |
| `briefs/completed/` | 已完成的 brief（归档） |
| `reviews/plans/` | plan 评审 |
| `reviews/results/` | result 评审 |
| `reviews/recipes/` | recipe diff 评审 |
| `decisions/` | 轻量 ADR（索引在根 `DECISIONS.md`） |
| `inbox/` | 未整理输入的落脚点 |

> plan **正文**不在这里，在根 `plans/<日期>-<slug>.zh.md`（human 直接在文件里批注）；
> `reviews/plans/` 只放 plan 的**评审记录**。二者配套，见 `interactive-plan-writer` agent。

## 原则

human 的输入一旦重要到会影响 agent 行为，就应落到 `human/` 的正式位置，而不是停留在对话里。`inbox/` 是临时缓冲，要定期清空。
