# current-status.md

> 活状态单一真相源。完成阶段、session 边界或关键验证后更新。

## 当前 objective

把 SportAgent 收敛为只有 `main`/`dev` 的无具体实现基线，并完成传统开源运动记录/训练规划产品底座的选型准备。

## 已接受方向

- 北极星方向保持不变：安全、可执行、会随真实反馈持续调整的个性化运动指导。
- 具体产品形态、首期运动类型和交互方式仍需讨论。
- 优先依托成熟开源产品；SportAgent 聚焦 AI 约束推理、计划修订、反馈闭环和领域评测。
- 旧 Fitness Agent 原型对当前决策没有约束力，已从活动基线移除。

## 当前结构

- Agent-native 控制根：仓库根目录，模板版本 v1.3.0。
- 活动实现：无；`lab/code/` 只保留模板骨架。
- 研究入口：
  - `human/briefs/active/20260713-open-source-base-selection.md`
  - `human/briefs/active/20260713-similar-projects-deep-research.md`
- 历史迁移证据：`lab/docs/audits/template-adoption*`。

## 分支目标

- GitHub 默认分支：`main`。
- 长期分支：仅 `main` 与 `dev`。
- `dev` 从当前 `main` 无实现基线创建；当前二者内容一致。
- 其余本地和远端分支删除。

## Constraints

- 在 human 接受开源底座与首期范围决策前，不开始产品实现、不新增产品依赖。
- 研究优先使用一手资料，许可证、活跃度和扩展边界必须动态核对。
- 不把旧原型的模块划分当成新产品架构。
- 根模板治理文件保持可同步；结构变更同步更新 ANATOMY。

## Active research

现有 Paseo tab `技术侦察员｜基础设施外包地图` 正在筛选 8–15 个传统运动记录/训练规划底座，并为 Top 3 设计 AI 接入边界和两周 spike。

## Stop condition

1. 本地与远端只剩 `main`/`dev`，默认分支为 `main`；
2. 两个分支指向同一个无具体实现 commit；
3. governance、anatomy drift、adapter sync 与 Git 状态验证通过；
4. GitHub #2/#3 反映“形态待讨论、开源底座优先、实现暂停”；
5. 开源底座研究 tab 已启动并保留供后续讨论。
