# 营养原理与训练规则 (Principles & Rules)

**对应文件**：

- `data/raw/nutrition_principles.json`: 进餐时机、宏量素比例及限制替代逻辑。
- `data/raw/rules.json`: 训练量、频率、分化方式及进阶逻辑。

这些文件构成了系统「逻辑大脑」的参数层。

## 营养原理 (`nutrition_principles.json`)

此文件定义了生理学层面的指导原则：

### 1. 进餐时机 (Meal Timing)

定义了 `pre_workout`（赛前/练前）、`post_workout`（练后）和 `pre_sleep`（睡前）的营养关注点及原因。例如：

- **练后窗口**：60分钟内，强调高 GI 碳水以补充糖原，配合 20-40g 蛋白质。
- **禁忌**：练前避开高纤维和高脂肪，防止肠胃不适。

### 2. 训练日 vs. 休息日 (Cycle Strategy)

系统根据当天是否有训练自动调整热量目标：

- **训练日**：碳水上调 15-20%，支持能量供应。
- **休息日**：碳水下调 10-15%，脂肪略微上调以维持激素水平。

### 3. 饮食限制替代 (Dietary Substitutions)

记录了针对 `lactose_intolerant`、`vegetarian`、`vegan`、`gluten_free` 的具体操作。

- **banned_food_tags**: 强制屏蔽的食材标签。
- **must_supplement**: 针对限制饮食建议的补剂（如 Vegan 必须补充 B12）。

---

## 训练规则 (`rules.json`)

此文件采用约束引擎（Constraint Engine）的思路，定义了不同场景下的参数：

### 1. 容量与频率 (Volume & Frequency)

- **容量 (rule*vol*\***)\*\*: 规定了不同水平（初/中/高级）每周每肌群的组数上下限。
- **天数 (rule*freq*\***)\*\*: 限制新手每周训练不超过 4 天，确保身体恢复。

### 2. 强度与目标 (Intensity)

根据目标（减脂、增肌、重组）定义：

- **RM 范围**：增肌建议 6-12RM，减脂建议 8-15RM。
- **RPE 建议**：即主观疲劳感知度。

### 3. 分化结构 (Structure)

定义了基于经验水平的分化逻辑：

- **新手**：全身分化 (Full Body)。
- **中级**：上下肢分化 (Upper-Lower)。
- **高级**：推拉腿分化 (PPL)。

## 维护建议

这些规则是 SportAgent 区别于通用 LLM 的关键——它们提供了**领域专家的约束**。当需要调整系统生成的「激进程度」时，应优先修改这些参数，而非强制修改 Prompt。
