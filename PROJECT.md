# PROJECT

> 研究控制根的顶层描述。派生新项目时**第一件事**就是填写本文件。

## 研究对象（一句话）

SportAgent 是一个以本地确定性知识库约束 LLM 创作的个性化健身、营养与训练执行规划系统。

## 当前 active family

- Planner Agent：周训练与宏观营养规划。
- Cooking Agent：逐日餐食、食谱缩放和购物清单。
- Gym Agent：单次训练执行指导、伤病适配和进阶计划。

## Trunk 与协作模式

采用单 trunk 模式：`issue -> branch off feature/v1 -> fresh worktree -> PR -> owner review -> merge back`。

- 当前 trunk：`feature/v1`
- 产品代码根：`lab/code/imported/SportAgent/`

## Remote / worktree 策略

- 远端：`git@github.com:a-green-hand-jack/SportAgent.git`；默认不推送，push 需 human gate。
- worktree 约定：`Non-trivial edit = fresh worktree`；一个 worktree = 一个 branch purpose = 一个 issue/PR。
- worktree 状态记录：`memory/worktree-status.md` + `memory/branches/<slug>.md`。

## 计算与存储

- GPU / 集群：当前测试与静态规划开发使用本地 CPU；无已登记远端训练作业。
- 大 bytes（data / checkpoint / runs / wandb）不进 Git，只留 index，见 `lab/infra/storage/`。

## 是否包含「内层 release agent」

- [ ] 否：这是普通 ML 研究 repo。忽略 `.agent/release-agent-boundary.md`。
- [x] 是：本 repo 要交付一个 agent 产品。严格区分外层开发 harness 与内层 release agent，见 `.agent/release-agent-boundary.md`。

## 关联文档

- 决策台账：`DECISIONS.md` -> `human/decisions/`
- 结构地图：`ANATOMY.md`
- 当前状态：`memory/current-status.md`
