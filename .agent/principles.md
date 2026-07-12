# 原则（不可协商）

源自 `.reference-docs/claude_code_optimization_spirit_zh.md` §7 的十二条，落到本 repo：

1. **Repo 是可信控制面**，不是代码容器；chat 只是短期意识流。
2. **Context 是昂贵工作记忆**，不是仓库。只保留当前推理需要的最小活动集。
3. **长期状态写文件**，不写在聊天里。fresh session 必须能从 repo 接续。
4. **Human 通过 repo-local brief / review / decision 协作**（`human/`），不靠回忆聊天。
5. **Main agent 做决策，subagents 做隔离任务。** main = PI/tech lead，sub = RA。
6. **并行之前先定义 ownership**，必要时用 worktree。隔离先于并行。
7. **Prompt 表达意图，hooks/permissions 执行硬约束。** 想让某事必然发生就写 hook。
8. **Checkpoint 不是 Git，Git 也不是实验记录。** 三者分工：试错 / 可审计历史 / 实验事实。
9. **Statusline 是仪表盘**，没有仪表盘就别开长途。
10. **高模型 / 高 effort 是子任务预算，不是 agent 身份。** 用任务风险与副作用半径选预算。
11. **Fresh context 是质量工具，session tree 是它的索引。** 新 session 不是失忆，是分支。
12. **Claude Code 会更新**，workflow recipe 要从 human-cc trace 提炼并定期复测。

## 一句话精神

> 把 Claude Code 当作实验仪器：校准它、约束它、记录它、验证它。不要崇拜 agent，要设计 harness。

## 证据分层（研究场景专属）

`log < metric < table < figure < paper claim`。不同层级不能混为一谈；只有可追溯（run id / config / commit / checkpoint / data split / metric source）且经 fresh verifier 复核的结果，才能升级为 paper claim。
