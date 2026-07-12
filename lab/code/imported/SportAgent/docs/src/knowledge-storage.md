# Knowledge 存储说明

本项目的"知识"全部以 **静态 JSON 文件** 形式存储在 `data/raw/` 目录下，由 `KnowledgeBase` 类（`src/fitness_agent/knowledge_base/loader.py`）在运行时加载并索引。

> **设计决策**：没有向量数据库，没有运行时学习，没有用户会话记忆。  
> 所有知识在程序启动时一次性加载到内存，查询全部基于 Python 过滤逻辑。

---

## 知识文件一览

| 文件                        | 内容                       | 用途                           |
| --------------------------- | -------------------------- | ------------------------------ |
| `exercises.json`            | 动作库（约 100+ 动作）     | Planner：安全筛选 + 构建动作池 |
| `nutrition.json`            | 食物营养数据库             | Cooking：宏量素精确计算        |
| `recipes.json`              | 食谱模板库                 | Cooking：食谱候选池            |
| `rules.json`                | 训练规则集（按目标和水平） | Planner：注入 prompt           |
| `anatomy.json`              | 肌肉解剖结构 + 训练量目标  | Planner：周训练量验证          |
| `nutrition_principles.json` | 营养原则 + 饮食替代方案    | Cooking：饮食限制处理          |
| `warmup_templates.json`     | 热身模板（按运动类型）     | Planner：热身方案生成          |
| `injury_profiles.json`      | 伤病档案（禁忌动作说明）   | Planner：伤病处理              |

---

## KnowledgeBase 类

```python
# 路径常量
_KB_DIR = data/raw/

class KnowledgeBase:
    # 所有属性使用 @cached_property，首次访问才加载 JSON
    exercises          -> list[Exercise]
    foods              -> list[FoodItem]
    rules              -> ...
    muscle_groups      -> ...
    nutrition_principles -> ...
    warmup_templates   -> ...
    injury_profiles    -> ...
    recipes            -> list[RecipeTemplate]
```

使用 `functools.cached_property` 实现**懒加载**：文件在第一次被访问时才读取，后续访问直接返回缓存值。

### 主要查询方法

#### 动作过滤

```python
# 安全性 + 可用性双重过滤（Planner Step 1 的核心）
kb.get_safe_exercises(
    contraindications: list[ContraindicationTag],  # 用户伤病
    available_equipment: list[Equipment],           # 用户可用器材
) -> list[Exercise]

# 进一步按肌群/动作模式/难度过滤
kb.filter_exercises(exercises, muscle_groups=..., movement_patterns=..., difficulty=...)
```

#### 营养计算（确定性）

```python
# 按 food_id 查询
kb.get_food_by_id(food_id: str) -> FoodItem | None

# 从食材列表精确计算宏量
kb.compute_ingredients_macros(
    ingredients: list[tuple[str, float]]  # (food_id, amount_g)
) -> Macros

# 从食谱模板计算宏量
kb.compute_recipe_macros(recipe: RecipeTemplate) -> Macros
```

#### 饮食限制处理

```python
# 兼容的食谱
kb.get_compatible_recipes(dietary_restrictions: list[str]) -> list[RecipeTemplate]

# 被屏蔽的 food_id 集合（用于校验）
kb.get_banned_food_ids(dietary_restrictions: list[str]) -> set[str]

# 获取所有合法的 food_id 集合
kb.all_food_ids -> set[str]
```

逻辑：在 `nutrition_principles.json` 中查找 `DietarySubstitution` 条目，从其 `banned_food_tags` 字段中找到对应的食材 ID。

#### 训练量目标

```python
# 返回 {muscle_id: (min_sets, max_sets)} 字典
kb.get_volume_targets(level: ExperienceLevel) -> dict[str, tuple[int, int]]
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

RecipeTemplate
  ├─ recipe_id: str
  ├─ meal_type: str             # breakfast / lunch / dinner / snack
  ├─ dietary_flags: list[str]
  └─ ingredients: list[Ingredient]   # food_id + amount_g
```

---

## 用户画像的持久化

**用户画像不在 `data/raw/` 中**，而是保存为独立 JSON 文件（路径由用户或 CLI 指定）：

```python
# user/onboarding.py
def save_profile(profile: UserProfile, path: Path) -> None:
    path.write_text(profile.model_dump_json(indent=2), encoding="utf-8")

def load_profile(path: Path) -> UserProfile:
    data = json.loads(path.read_text(encoding="utf-8"))
    return UserProfile.model_validate(data)
```

用户画像包含基本信息、目标、器材、伤病、饮食限制，以及由 `enrich_profile()` 计算出的 BMR / TDEE / 热量目标 / 蛋白质目标。

### 生成的计划持久化

训练计划（`WeeklyPlan`）和烹饪计划（`WeeklyCookingPlan`）同样以 JSON 形式保存：

```
outputs/
  {name}_training_plan.json     # WeeklyPlan
  {name}_cooking_plan.json      # WeeklyCookingPlan
  {name}_training_plan.md       # Markdown 可读版本
  {name}_cooking_plan.md        # Markdown 可读版本
```

---

## 知识库的局限性

- **静态数据**：食物库、动作库不会自动更新，需手动维护 JSON 文件
- **无向量搜索**：食物查询基于精确 `food_id` 匹配，无语义搜索
- **无版本控制**：JSON 文件没有版本号，格式变更需手动迁移
- **无运行时学习**：Agent 不会基于用户反馈自动更新知识库
