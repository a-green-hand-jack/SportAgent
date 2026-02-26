本项目使用 **LangGraph** 重构了 Agent 架构，将传统的类封装改为 **StateGraph 节点 + 工具 + 资源库** 的组合模式。核心逻辑遵循：**K&T Registry 资源管控 + 声明式节点流 + 确定性工具链**。

---

## 核心架构：K&T Registry

为了保证 Agent 的安全性与可控性，项目引入了 **K&T (Knowledge & Tool) Registry** 设计模式（见 `src/fitness_agent/graph/registry.py`）。

### 1. 资源授权矩阵

每个 Agent 节点在运行时只能访问 REGISTRY 中明确定义的 **Knowledge 域** 和 **Tool 函数**。

- **知识访问器 (Knowledge Accessors)**：如 `PlannerKnowledge`，它是对全局 `KnowledgeBase` 的子集封装，只暴露该 Agent 授权查询的接口。
- **原子工具 (Tools)**：如 `volume_checker`，是纯函数式的业务逻辑单元，方便独立测试。

### 2. 无状态节点流

每个 Agent 现在是一个独立的 `node` 函数，接收 `FitnessAgentState` 并返回更新后的状态。这种设计天然支持分支路由、循环重试和中间状态持久化。

---

## Planner 节点 (plan_node)

**文件**：`src/fitness_agent/graph/agents/planner.py`

负责生成周训练计划。

### 授权资源

- **Knowledge**: `rules`, `anatomy`, `exercises`
- **Tools**: `split_engine` (动作池筛选), `volume_checker` (容量验证)

### 执行流程

1. **KB 筛选**：调用 `split_engine` 过滤伤病禁忌并根据器材筛选安全动作池。
2. **LLM 生成**：注入用户画像、规则和动作池，生成 `WeeklyPlan` JSON。
3. **闭环验证**：
   - 调用 `volume_checker` 计算各肌群每周组数是否在安全区间内（Based on `anatomy.json`）。
   - 验证单次训练时长和伤病安全性。
4. **重试机制**：若验证失败，将错误信息通过对话追加给 LLM 进行自我修正（最多重试 2 次）。

---

## Cooking 节点 (cook_node)

**文件**：`src/fitness_agent/graph/agents/cooking.py`

负责生成 7 天饮食计划。

### 授权资源
- **Knowledge**: `recipes`, `nutrition`, `nutrition_principles`
- **Tools**: `deterministic_scaler` (精准热量缩放), `grocery_gen` (购物清单生成)

### 创新机制：增量式逐日生成 (Incremental Generation)
为了彻底解决长文本生成导致的 JSON 截断和逻辑混乱，`cook_node` 采用了 **逐日滚动生成** 模式：
1. 循环 7 天，每次调用 LLM 只生成一天的计划。
2. 将已生成的历史天数作为 Context 传给 LLM（通过 `already_generated_json`）。
3. 这种模式极大提高了 LLM 维持食谱多样性和热量连贯性的能力。

### 核心执行链
1. **逐日生成**：遍历周一至周日，每次调用 LLM 生成单日 `DayMealPlan`。
2. **确定性修正**：由 `deterministic_scaler` 工具根据 `nutrition.json` 的数据，自动等比例缩放食材量，并补全蛋白质缺口。
3. **购物清单**：`grocery_gen` 工具在生成完整 7 天计划后，自动去重并按品类汇总清单。

---

## GYM 节点 (gym_node)

**文件**：`src/fitness_agent/graph/agents/gym.py`

负责为 individual 训练课提供深度指导（Training Session Guidance）。

### 授权资源
- **Knowledge**: `exercises`, `warmup_templates`, `injury_profiles`
- **Tools**: `training_card_exporter` (训练卡生成器), `rpe_engine` (重量推荐引擎)

### 执行流程
1. **热身匹配**：基于计划中的动作模式，自动匹配最合适的热身模板，并结合用户伤病档案（`injury_profiles`）动态修改热身步骤。
2. **RPE 计算**：调用 `rpe_engine` 工具，根据动作类型、用户的相对强度（Intensity Level）推荐每个动作的重量（重量参考 Onboarding 阶段的自评）。
3. **卡片生成**：生成结构化的单课训练卡，包含：热身方案、动作明细（组数、次数、RPE、建议重量、休息时间）、伤病提醒、以及针对性的动作提示。

---

## 基础设施变更

### 1. LangGraph 状态管理
所有数据交换通过 `FitnessAgentState`（TypedDict）进行。节点间的依赖（如 `cook_node` 依赖 `weekly_plan`）通过图形拓扑强制保证。

### 2. Prompt 多元化
- **Planner**: `planner/prompt.py`
- **Cooking**: `cooking/prompt.py`
- **GYM**: `gym/prompt.py`

每个节点拥有独立的 System Prompt 角色定义和构建函数，解耦了各阶段的输出要求。
