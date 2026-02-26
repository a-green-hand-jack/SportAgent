# Knowledge 存储说明

本项目的"知识"全部以 **静态 JSON 文件** 形式存储在 `data/raw/` 目录下，由 `KnowledgeBase` 类（`src/fitness_agent/knowledge_base/loader.py`）在运行时加载并索引。

> **设计决策**：没有向量数据库，没有运行时学习，没有用户会话记忆。  
> 所有知识在程序启动时一次性加载到内存，查询全部基于 Python 过滤逻辑。

---

## 知识文件一览

| 文件                        | 内容                       | 用途                      |
| --------------------------- | -------------------------- | ------------------------- |
| `exercises.json`            | 动作库（约 100+ 动作）     | Planner/GYM：动作池与细节 |
| `nutrition.json`            | 食物营养数据库             | Cooking：宏量素精确计算   |
| `recipes.json`              | 食品模板库                 | Cooking：食谱候选池       |
| `rules.json`                | 训练规则集（按目标和水平） | Planner：注入 prompt      |
| `anatomy.json`              | 肌肉解剖结构 + 训练量目标  | Planner：周训练量验证     |
| `nutrition_principles.json` | 营养原则 + 饮食替代方案    | Cooking：饮食限制处理     |
| `warmup_templates.json`     | 热身模板（按运动类型）     | GYM：热身方案生成         |
| `injury_profiles.json`      | 伤病档案（禁忌动作说明）   | GYM/Planner：安全性处理   |

---

## 权限管控：Knowledge Accessors

在 LangGraph 重构后，Agent 节点不再直接访问全局 `KnowledgeBase`，而是通过 **Knowledge Accessors**（`src/fitness_agent/graph/knowledge/accessors.py`）获取授权后的数据视图。

### 1. 资源授权机制

- 每个节点仅持有 REGISTRY 中授权的 Accessor 实例。
- **PlannerKnowledge**：仅暴露 split_engine、anatomy、exercise 相关的查询接口。
- **CookingKnowledge**：仅暴露 recipe、nutrition、原则相关的查询接口。
- **GYMKnowledge**：暴露 exercise 细节、warmup 模板、伤病档案接口。

### 2. 核心查询逻辑（在 Accessors 中封装）

#### 动作过滤与安全性

```python
# PlannerKnowledge.get_split_templates() -> 获取训练拆分规则
# GYMKnowledge.get_injury_profile() -> 获取伤病对应的处理方案
```

#### 营养计算与校验

```python
# CookingKnowledge.get_ingredient_macros(food_id) -> 获取精确营养数据
# CookingKnowledge.get_all_food_ids() -> 用于校验 LLM 幻觉
```

---

## 数据模型（Pydantic）

知识条目由 `knowledge_base/models.py` 中的 Pydantic 模型描述：

```
Exercise
  ├─ exercise_id: str
  ├─ primary_muscles: list[MuscleGroup]
  ├─ secondary_muscles: list[MuscleGroup]
  ├─ equipment: list[Equipment]
  ├─ contraindications: list[ContraindicationTag]
  └─ difficulty: str

FoodItem
  ├─ food_id: str
  ├─ name_en / name_zh: str
  ├─ dietary_tags: list[str]    # vegetarian, vegan, no_pork …
  └─ per_100g: Macros           # calories / protein / carbs / fat
```

---

## 用户画像与计划持久化

### 用户画像 (profile.json)

用户画像包含基本信息、目标、器材、伤病、以及由 `enrich_profile()` 计算出的 BMR / TDEE / 宏量目标。

### 图运行产物 (outputs/)

LangGraph 运行后的状态节点数据会被提取并保存：

```
outputs/
  {name}_weekly_plan.json     # 训练周计划
  {name}_cooking_plan.json    # 饮食周计划
  {name}_gym_plan.json        # 单课训练指导 (New)
  {name}_training_*.md        # 对应 Markdown 渲染版本
```

---

## 知识库的局限性

- **静态数据**：食物库、动作库不会自动更新，需手动维护 JSON 文件。
- **无向量搜索**：食物查询基于精确 `food_id` 匹配，无语义搜索。
- **权限边界**：节点无法跨域访问知识（如 Planner 无法访问详细食谱），保证了逻辑的解耦合。
