# SportAgent 开源产品底座选择

## Objective

寻找一个成熟、仍在维护的传统运动记录/训练规划开源项目，作为 SportAgent 的产品与数据基础；SportAgent 只在其上增加北极星所需的 AI 约束推理、计划修订和反馈闭环。

## Success criteria

- 找到 8–15 个直接候选，而不是通用 LLM/Agent 基础设施；
- 候选至少覆盖训练计划、运动记录、动作/训练数据模型、用户历史与可扩展 API 中的多数能力；
- 每个候选核对许可证、维护活跃度、主要技术栈、自托管方式、数据导入导出、扩展点、移动/Web 形态、隐私边界和社区健康；
- 对 Top 3 给出“在其上增加 SportAgent AI 闭环”的具体集成形态和两周 spike 方案；
- 给出推荐，但不替 human 做最终选型；明确会导致放弃候选的硬门槛。

## Scope

- **Allowed paths**：只读本仓库与外部一手资料；输出研究结论到 agent tab。
- **Forbidden paths**：不修改代码、issue、branch、远端或依赖；不开始实现。

## Research focus

优先寻找传统产品底座，而不是 AI demo：

- 训练/健身计划与日志：力量训练、动作库、组次重量、RPE/RIR、周期计划；
- 通用运动记录：活动历史、指标、日历、目标、进度图表、设备/格式导入；
- 自托管健康/运动平台：用户数据、API、权限和可扩展后端已经成熟；
- 可合理增加 AI coach/replanner，而不需要 fork 后重写大部分系统。

已知名字可以作为起点但不能限制搜索：wger、FitTrackee、OpenTracks、Workout.cool，以及活跃的 TrainingPeaks/Strong/Hevy 开源替代品。

## Evaluation matrix

| 维度 | 必须回答的问题 |
| --- | --- |
| 产品契合 | 它已解决哪些记录、规划、历史、可视化和用户工作流？ |
| 数据模型 | 是否能表示动作、session、set、load、RPE/RIR、计划版本和反馈？ |
| 扩展性 | 有稳定 API、plugin/event/webhook，还是只能维护重 fork？ |
| 技术与运维 | 栈是否适合当前团队；本地开发、自托管、升级和测试成本如何？ |
| 许可证 | 是否允许修改、分发、SaaS；是否有 copyleft/商标/数据许可约束？ |
| 活跃度 | 最近 release/commit、maintainer 响应、issue/PR 健康如何？ |
| 隐私安全 | 健康数据默认如何保存、导出、删除和隔离？ |
| AI 接入 | SportAgent 的约束编译器、修订决策和解释层应接在哪个边界？ |
| 迁移风险 | 上游漂移、fork 成本、前端耦合、数据锁定和不可测试区域是什么？ |

## Deliverable

1. 一页结论：最值得 spike 的 3 个底座和各自不选条件；
2. 8–15 项全景比较表，所有动态事实附一手链接和检索日期；
3. Top 3 架构与数据流拆解；
4. 每个 Top 3 的两周最小 spike：接入点、演示场景、验收门、预计删除的自研基础设施；
5. 推荐的决策会议议程，以及在信息不足时仍需 human 裁决的问题。

## Stop condition

研究足以支持一次选型讨论和 Top 2 spike 决策；不实施、不把推荐写成既定事实。
