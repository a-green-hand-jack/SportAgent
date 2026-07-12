# 动作库与解剖学 (Exercise & Anatomy)

**对应文件**：

- `data/raw/exercises.json`: 300+ 训练动作数据。
- `data/raw/anatomy.json`: 肌肉群定义及其训练量准则。

动作库是 PlannerAgent 构建训练计划的材料池。

## 解剖学模型 (`anatomy.json`)

系统将肌肉群定义为有属性的实体，而不仅仅是标签：

- **`is_large_muscle`**: 大肌群（如胸、背、腿）需要更长的恢复时间，通常安排在训练日的首个动作。
- **`recovery_hours`**: 恢复时长范围，用于算法在编排背靠背训练日时避开同一肌群。
- **`weekly_volume`** (初级/中级/高级): 按水平定义的每周建议组数上限。PlannerAgent 需确保总组数在此范围内。
- **`antagonist_groups`**: 对抗肌群关系（如肱二头肌对肱三头肌），用于智能编排超级组或平衡训练。

## 动作数据模型 (`exercises.json`)

每个动作包含：

- `primary_muscles`: 主动肌（主要受力点）。
- `secondary_muscles`: 协同肌（辅助受力点）。
- `equipment`: 要求的器材标识（需与用户 Profile 匹配）。
- `difficulty`: 难度分级（beginner / intermediate / advanced）。
- `movement_pattern`: 动作模式（push / pull / squat / hinge / core / cardio / isolation）。用于保证训练多样性。
- **`contraindications`**: 伤病禁忌标签。若用户有 `wrist_injury`，则所有带此标签的动作（如 `push_up`）将被 KB.get_safe_exercises() 自动过滤。

## 安全与过滤逻辑

PlannerAgent 在生成计划前，会调用 KB 执行以下硬性过滤：

1. **伤病屏蔽**：基于用户 Profile 中的 `contraindications`。
2. **器材匹配**：仅展示用户勾选过的可用器材。若无合适器材，系统具备「Fallback 到自重动作池」的降级逻辑。
3. **难度对齐**：根据用户经验水平（ExperienceLevel）过滤。

## MET 值 (Metabolic Equivalent)

部分动作配有 `met_value`。这用于更精确地估计单次训练消耗的热量。目前该字段在有氧（Cardio）动作中较为完整，抗阻力动作中则由于负重和强度差异较大，系统更多依赖时长和基础代謝进行估算。
