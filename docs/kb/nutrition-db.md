# 食材库 (Nutrition Database)

**对应文件**：`data/raw/nutrition.json`

食材库是 CookingAgent 进行营养核算和饮食限制过滤的基石。

## 数据模型

每个食材条目（Food Item）包含：

- `id`: 唯一标识符（如 `chicken_breast`）
- `name_zh`: 中文展示名称
- `category`: 分类（见下表）
- `serving_size_g`: 标准份量（默认为 100g）
- `calories`: 每份热量 (kcal)
- `protein_g`: 蛋白质 (g)
- `carbs_g`: 碳水化合物 (g)
- `fat_g`: 脂肪 (g)
- `dietary_tags`: 标签数组，用于自动匹配用户限制（如 `vegan`, `gluten`）

## 食材分类 (Categories)

| 分类 ID     | 示例食材               | 说明                            |
| :---------- | :--------------------- | :------------------------------ |
| `grain`     | 大米, 燕麦, 红薯, 土豆 | 主要碳水来源                    |
| `meat`      | 牛里脊, 猪里脊, 羊腿肉 | 畜肉类蛋白质和脂肪来源          |
| `poultry`   | 鸡胸肉, 火鸡胸肉       | 禽肉类优质蛋白质来源            |
| `seafood`   | 三文鱼, 金枪鱼, 虾     | 鱼虾类蛋白质及脂肪酸来源        |
| `egg_dairy` | 鸡蛋, 牛奶, 希腊酸奶   | 蛋奶类蛋白质                    |
| `legume`    | 豆腐, 毛豆, 豆浆       | 豆类及植物蛋白来源              |
| `vegetable` | 西蓝花, 菠菜, 番茄     | 纤维素和微量元素来源            |
| `fruit`     | 香蕉, 蓝莓, 苹果       | 天然糖分和维生素来源            |
| `oil_fat`   | 橄榄油, 花生油, 坚果   | 纯油脂及健康脂肪来源            |
| `condiment` | 酱油, 醋, 蜂蜜         | 调味品（包含部分糖分/钠摄入量） |

## 饮食标签体系 (Dietary Tags)

系统通过标签执行自动禁忌过滤：

- **`plant` / `animal_product`**：区分动植物来源。
- **`vegan` / `vegetarian`**：严格/普通素食。
- **`dairy` / `egg`**：用于乳糖不耐受或蛋类过敏。
- **`gluten`**：用于麸质过敏过滤。
- **`high_protein`**：辅助 Agent 识别高蛋白源（如蛋白质强化步骤）。

## 维护原则

1. **数值来源**：数据应尽量参考 USDA 或中国食物成分表。
2. **加工状态**：食材通常指「生重」或「标准可食用部分」，除非条目明确注明（如 `pasta` 记录的是煮熟后的数值）。
3. **ID 规范**：使用 `snake_case`，如 `sweet_potato`。
