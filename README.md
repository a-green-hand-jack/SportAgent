# SportAgent

SportAgent 正在探索一种更可信的 AI 运动教练：它不是只生成一次计划，而是基于真实训练反馈持续修订计划，同时保留目标、时间、器材、偏好和安全约束。

## 北极星

> 让普通训练者无需依赖昂贵的长期私教，也能获得安全、可执行、会随真实反馈持续调整的个性化训练与营养指导，并取得可验证、可持续的身体与行为进步。

长期方向已经确定；具体产品形态、首期运动类型和交互方式仍待研究与讨论。

## 当前状态

- 仓库暂不保留具体产品实现；旧 Fitness Agent 原型已从 `main`/`dev` 基线移除。
- 当前首要决策不是写新框架，而是选择一个成熟的传统运动记录/训练规划开源项目作为底座。
- SportAgent 计划在上游产品能力之上增加 AI 约束推理、计划修订、反馈闭环和领域评测。
- Agent-native 模板、项目治理、研究记录与决策入口继续保留。

在底座选型完成并记录决策之前，不进入产品实现。

## 建设原则

### 依托开源产品

优先复用已有项目提供的用户系统、训练记录、计划管理、动作数据、历史展示、导入导出、移动/Web 交互和部署能力。我们只维护必要的适配层，不重建通用产品基础设施。

候选底座应满足：

- 许可证允许目标使用方式；
- 仍在维护，升级路径可控；
- 有稳定 API、事件或可维护的扩展边界；
- 数据模型能容纳训练 session、动作、组次、负荷和反馈；
- 支持自托管、数据导出和合理的隐私控制；
- 加入 AI 功能不要求长期维护一个几乎完全分叉的产品。

### 保留核心创新

- 健身领域的约束建模与计划编译；
- 反馈驱动的计划修订，并保持未受影响约束；
- fail-closed 的安全边界与人工转介；
- 有来源的领域知识和专家可审查规则；
- 安全性、可执行性、依从性和真实进步的领域评测。

## 分支

- `main`：稳定的方向、治理、研究和已接受决策。
- `dev`：后续 spike、集成与实现的汇总分支。

仓库只保留这两个长期分支。当前二者共享同一个无具体实现基线。

## 项目入口

- [北极星 issue](https://github.com/a-green-hand-jack/SportAgent/issues/1)
- [v1 路线与选型状态](https://github.com/a-green-hand-jack/SportAgent/issues/2)
- [常驻进度条](https://github.com/a-green-hand-jack/SportAgent/issues/3)
- 开源底座研究 brief：`human/briefs/active/20260713-open-source-base-selection.md`
- 相似项目 Deep Research prompt：`human/briefs/active/20260713-similar-projects-deep-research.md`
- 当前状态：`memory/current-status.md`

## 仓库结构

```text
SportAgent/
├── AGENTS.md            # Agent 工作入口与项目约束
├── PROJECT.md           # 项目范围、分支与协作方式
├── human/               # Brief、决策与评审
├── memory/              # 当前状态与长期记忆
├── lab/                 # 研究、选型、实验和未来代码控制面
├── deliverables/        # 对外交付索引
└── scripts/             # Agent-native 治理与验证工具
```

本仓库采用 `a-green-hand-jack/ml-project-repo-agent-native-template` v1.3.0，并通过 `.template.toml` 跟踪上游同步。
