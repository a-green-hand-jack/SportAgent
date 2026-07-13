# PROJECT

## 研究对象

SportAgent 探索一种安全、可执行、能根据真实反馈持续修订计划的个性化 AI 运动教练。

## 当前阶段

**产品底座选择与核心假设收敛。**

- 北极星方向已接受，见 GitHub issue #1。
- 具体产品形态、首期运动类型和 v1 交互方式仍待讨论。
- 旧 Fitness Agent 原型已退出当前基线；仓库暂不包含产品实现。
- 首选路径是在成熟的传统运动记录/训练规划开源项目上增加 SportAgent 的 AI 闭环，而不是从零建设完整应用。

## 当前核心假设

SportAgent 的价值应来自领域层，而不是通用 Agent 数量或平台基础设施：

1. 将用户目标、时间、器材、偏好和安全规则编译为可验证约束；
2. 根据训练记录与主观反馈修订计划，同时保留未受影响约束；
3. 对未知、不安全或证据不足的建议 fail closed；
4. 用领域基准和真实试用证明安全性、可执行性与持续使用价值。

假设会在底座研究、设计讨论和小型 spike 后进一步收窄。

## 分支与协作

- `main`：稳定方向、治理、研究与已接受决策；GitHub 默认分支。
- `dev`：后续集成与实现汇总；从 `main` 创建。
- 不保留其他长期分支；短期 spike 分支完成后应合并或删除。
- 当前 `main` 与 `dev` 指向同一个无具体实现基线。

## 开源底座决策门

在开始产品实现前，至少完成：

- 8–15 个直接候选的许可证、活跃度、产品能力和扩展边界比较；
- Top 3 的数据模型与 AI 接入点拆解；
- Top 2 的小型 spike 计划与退出条件；
- human 对最终底座、fork/插件策略和首期范围的明确决策记录。

研究 brief：`human/briefs/active/20260713-open-source-base-selection.md`。

## 计算与存储

- 当前没有产品运行时、训练任务、GPU 作业或远端数据面。
- 大 bytes 不进 Git，只保留索引，见 `lab/infra/storage/`。

## Agent 产品边界

- 当前尚未选定 release product，因此不实现内层 release agent。
- 选定底座后，再依据 `.agent/release-agent-boundary.md` 明确外层开发 harness 与产品内 AI 能力的边界。

## 关联真源

- 北极星：https://github.com/a-green-hand-jack/SportAgent/issues/1
- v1 路线：https://github.com/a-green-hand-jack/SportAgent/issues/2
- 进度条：https://github.com/a-green-hand-jack/SportAgent/issues/3
- 决策台账：`DECISIONS.md` -> `human/decisions/`
- 结构地图：`ANATOMY.md`
- 当前状态：`memory/current-status.md`
