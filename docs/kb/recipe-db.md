# 食谱库 (Recipe Database)

**对应文件**：`data/raw/recipes.json`

食谱库提供了一套高质量的、经过营养验证的任务模板。CookingAgent 的职责是基于这些模板进行变体生成和克数缩放。

## 食谱结构

```json
{
  "id": "recipe_id",
  "name_zh": "食谱名称",
  "meal_type": "breakfast|lunch|dinner|snack|pre_workout|post_workout",
  "tags": ["high_protein", "quick", "batch_friendly"],
  "ingredients": [
    { "food_id": "food_id_ref", "amount_g": 150, "note": "加工说明" }
  ],
  "steps_zh": ["步骤1", "步骤2"],
  "substitution_groups": {
    "vegan": {
      "milk": {
        "replacement_id": "soy_milk",
        "amount_g": 200,
        "note": "替换说明"
      }
    }
  },
  "scaling_notes": "缩放指导原则"
}
```

## 核心设计点

### 1. 餐食类型 (`meal_type`)

食谱被硬性分配到不同的进餐时段。这确保了 Agent 不会在早餐推荐「宫保鸡丁」，也不会在训练后推荐「低蛋白沙拉」。

- **`pre_workout`**: 低脂、中等碳水，易消化。
- **`post_workout`**: 高蛋白、高碳水，促进合成。
- **`snack`**: 低热量，高蛋白。

### 2. 动态替代 (`substitution_groups`)

这是本项目的一个「小巧思」。Agent 如果发现用户有特殊的饮食限制（如 `vegan`），它会查询该食谱的 `substitution_groups`。

- 如果定义了替代方案，直接应用。
- 如果没有定义，由 LLM 根据 [营养原理](./principles-and-rules.md) 自行寻找食材库中的替代品。

### 3. 可批量性 (`batch_friendly`)

标记哪些菜品可以一次做 3-5 天的量（Meal Prep）。这在 `shopping_list` 生成和生成 `cooking_tips_zh` 时是非常重要的参考坐标。

### 4. 营养锚点 (`per_serving_macros`)

此字段仅作为 LLM 的参考初值。CookingAgent 生成后，会立即执行 `_overwrite_macros_deterministic` 来覆盖这一数值。

## 扩展建议

当添加新食谱时：

1. **配比优先**：食材克数只是基准，重点是比例要合理。
2. **加工说明**：在 `ingredients.note` 中注明具体处理方法（如「切丁」、「去皮重量」），这会显著提高生成的 Markdown 文档的实用性。
