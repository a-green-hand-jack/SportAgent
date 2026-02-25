# Agent 实现文档

本项目中共有两个核心 Agent：`PlannerAgent`（训练计划生成器）和 `CookingAgent`（饮食计划生成器）。两者的架构模式相同：**确定性 KB 过滤 + LLM 创意生成 + 规则校验重试**。

---

## 总体设计哲学

Agent 的职责被刻意一分为二：

| 层              | 谁来做                     | 例子                         |
| --------------- | -------------------------- | ---------------------------- |
| **规则/安全层** | KnowledgeBase（纯 Python） | 过滤受伤禁忌动作、计算宏量素 |
| **创意/排列层** | LLM                        | 给出一周训练编排、食谱搭配   |

这样 Agent 既保证安全合规，又保留 LLM 个性化灵活度。

---

## PlannerAgent

**文件**：`src/fitness_agent/planner/agent.py`

### 初始化参数

```python
PlannerAgent(
    client: BaseLLMClient,       # LLM 客户端
    kb: KnowledgeBase,           # 知识库
    max_exercises_in_pool: int = 60,  # 发给 LLM 的最大动作数（控制 prompt 长度）
    max_retries: int = 2,        # 验证失败后最多重试次数
)
```

### `generate_plan(profile)` 流程

```
Step 1 ── 确定性 KB 过滤
          ├─ 排除伤病禁忌动作 (get_safe_exercises)
          ├─ 排除用户无法使用的器材
          └─ 若结果为空 → fallback 到纯徒手动作

Step 2 ── 构建 Prompt
          ├─ PLANNER_SYSTEM （系统提示，定义教练角色与 JSON 格式）
          └─ build_user_message()：
               用户画像 + 训练规则 + 动作池 + 营养信息

Step 3 ── LLM 调用（generate → validate → retry 循环）
          for attempt in range(max_retries + 1):
            response = client.chat(messages, system, max_tokens=8192)
            plan = _parse_response(response)   # 解析 JSON → WeeklyPlan
            ├─ 验证周训练量 (_validate_volume)
            ├─ 验证每日时长 (_validate_duration)
            └─ 验证伤病安全 (_validate_injuries)
            if all_warnings: 追加纠错 message → 重试
            else: break

Step 4 ── 收尾
          若重试后仍有警告 → 把警告写入 coach_notes（不崩溃）
          返回 WeeklyPlan
```

### 验证机制

| 验证项       | 方法                                 | 触发重试         |
| ------------ | ------------------------------------ | ---------------- |
| 周训练量     | `_validate_volume`                   | 是               |
| 单次训练时长 | `_validate_duration`（+15 分钟容差） | 是               |
| 伤病安全     | `_validate_injuries`                 | 是               |
| 训练日数量   | 直接比较（非阻塞）                   | 否（仅 warning） |

重试时，Agent 把上一轮的助理回复和纠错指令追加到 `messages` 列表，形成多轮对话，LLM 可以看到自己的错误并修正。

### 无状态设计

> `PlannerAgent` 是 **stateless** 的——每次调用 `generate_plan()` 都是全新的对话。没有跨请求的会话历史。

---

## CookingAgent

**文件**：`src/fitness_agent/cooking/agent.py`

### 初始化参数

```python
CookingAgent(
    client: BaseLLMClient,
    kb: KnowledgeBase,
    max_retries: int = 1,
    calorie_tolerance_pct: float = 10.0,  # 热量校验的容差百分比
)
```

### 设计哲学

CookingAgent 采用**「LLM 管创意，系统管精度」**的分工哲学：

- LLM 负责食材搭配、烹饪步骤、菜品多样性等创意决策
- 系统通过确定性后处理流水线保证热量/蛋白质的数值精度
- 这样 LLM 的幻觉只影响食材创意，不影响关键数值约束

> **关键约束常量**（类级别定义，集中管理）
>
> | 常量                             | 值          | 含义                        |
> | -------------------------------- | ----------- | --------------------------- |
> | `TRAINING_DAY_MULTIPLIER`        | 1.07        | 训练日热量 +7%              |
> | `REST_DAY_MULTIPLIER`            | 0.96        | 休息日热量 -4%              |
> | `MAX_SCALE_FACTOR`               | 2.0         | 食材最大等比缩放倍数        |
> | `MIN_SCALE_FACTOR`               | 0.5         | 食材最小等比缩放倍数        |
> | `PROTEIN_COMPLIANCE_PCT`         | 90.0        | 每日蛋白质合规下限（%目标） |
> | `PROTEIN_RICH_THRESHOLD`         | 15.0 g/100g | 判断「高蛋白食材」的阈值    |
> | `POST_WORKOUT_MIN_PROTEIN_G`     | 35.0 g      | 训练后餐最低蛋白质要求      |
> | `PROTEIN_BOOST_BUFFER_G`         | 5.0 g       | 蛋白强化的安全缓冲量        |
> | `MAX_UNKNOWN_FOOD_IDS_PER_BATCH` | 2           | 容忍的最大食材 ID 幻觉数    |
>
> `MEAL_CALORIE_HARD_CAPS` 为 snack（400）和 pre_workout（400）设置了硬性上限，超出后强制向下缩放。

---

### `generate_cooking_plan(weekly_plan, profile)` 主流程

```
Step 1 ── 食谱兼容性过滤
          ├─ get_compatible_recipes(dietary_restrictions)  →  compatible_recipes
          └─ get_banned_food_ids(dietary_restrictions)     →  banned_food_ids

Step 2 ── 增量逐日 LLM 生成（7次调用，每次生成1天）
          for day_label in [周一 … 周日]:
            already_json = json.dumps([d.model_dump() for d in all_days])  # 历史上下文
            day = _generate_day(day_label, already_generated_json=already_json)
            all_days.append(day)

Step 3 ── 确定性后处理流水线（全 7 天）
          a. _overwrite_macros_deterministic()   # 用 KB 数据覆盖 LLM 报告的宏量
          b. _boost_protein_for_day()            # 蛋白质缺口补足（+5g 缓冲）
          c. _scale_day_to_calorie_target()      # 等比缩放食材量，精确达到热量目标
          d. _clamp_meal_calories()              # 超上限餐食（snack/pre_workout）向下强制缩放
          e. _round_ingredient_amounts()         # 克数取整（≥10g: 整10g; <10g: 整5g）
          f. _overwrite_macros_deterministic()   # 二次宏量覆写（反映取整后的精确值）

Step 4 ── 最终警告型验证（仅记录，不再重试）
          ├─ _validate_calorie_compliance()      # 热量偏差
          ├─ _validate_protein_compliance()      # 蛋白质不足
          ├─ _validate_post_workout_protein()    # 训练后餐蛋白
          ├─ _validate_diversity()               # 跨天食谱多样性
          ├─ _validate_intraday_diversity()      # 日内蛋白质食材重复
          ├─ _validate_meal_structure()          # 训练日/休息日餐型结构
          └─ _validate_meal_calorie_ranges()     # 单餐热量范围

          → 将剩余警告追加至 plan.cooking_tips_zh（不崩溃）

Step 5 ── 收尾
          _compute_day_calorie_target() → 计算最终 calorie_deviation_pct
          _aggregate_shopping_list()   → 跨 7 天去重汇总购物清单
          返回 WeeklyCookingPlan
```

---

### 增量逐日生成策略（核心架构决策）

这是 CookingAgent 最重要的架构设计，与旧版的「分批生成（2+2+3天）」有根本区别。

**动机**：旧版批量生成无法有效避免菜品重复，且任何批量内的 LLM 幻觉会影响整批。

**核心思路**：每次只让 LLM 生成 **1 天**，但把所有已生成的天作为历史 JSON 注入到下一次调用的 Prompt 中。

```
周一 LLM call:  [无历史] ──→ DayMealPlan(周一)
                                  ↓ json.dumps
周二 LLM call:  [历史: 周一] ──→ DayMealPlan(周二)
                                  ↓ json.dumps（周一 + 周二）
周三 LLM call:  [历史: 周一, 周二] ──→ DayMealPlan(周三)
                                  ↓ ...
...
周日 LLM call:  [历史: 周一~周六] ──→ DayMealPlan(周日)
```

**优势**：

| 维度            | 旧批量策略                | 新增量策略                    |
| --------------- | ------------------------- | ----------------------------- |
| LLM 感知历史    | ❌ 批内无法看到已生成内容 | ✅ 每天都能看到完整历史       |
| 输出 token 需求 | 多（一次生成 2-3 天）     | 少（单天 ≈ 1500-2000 tokens） |
| 幻觉影响范围    | 一旦失败整批受影响        | 仅影响当天，单独重试          |
| 适配 provider   | 需要判断 token 上限选批次 | 统一策略，无需适配            |
| 菜品多样性控制  | 依赖 Prompt 指令          | LLM 能直接看到已用菜品        |

**实现关键细节（`_generate_day`）**：

```python
# max_tokens 设置为 4096（单天 ≈ 1500-2000 tokens，4096 足够宽裕）
response = self.client.chat(messages, system=COOKING_SYSTEM, max_tokens=4096)

# 重试循环内同样注入历史——历史 JSON 只在首次调用注入（通过 user_message），
# 重试时只追加 assistant 回复 + 纠错 user 消息，保持多轮对话结构
messages.append(Message(role="assistant", content=response.content))
messages.append(Message(role="user", content=correction))
```

---

### 确定性后处理流水线详解

#### a. 宏量素覆写 (`_overwrite_macros_deterministic`)

**完全忽略** LLM 自报的营养数值，通过 `food_id × amount_g × nutrition.json` 重算：

```python
computed = kb.compute_ingredients_macros([(ing.food_id, ing.amount_g) for ing in recipe.ingredients])
recipe.per_serving_macros = MacroBreakdown(calories=computed["calories"], ...)
```

此方法在流水线中被调用 **两次**（Step a 和 Step f），确保每次修改食材量后数值都保持一致。

#### b. 蛋白质强化 (`_boost_protein_for_day`)

触发条件：`day.protein_g < daily_protein_target`（注意：比 PROTEIN_COMPLIANCE_PCT 更严格，一旦不足即触发）。
目标值：`daily_protein_target + PROTEIN_BOOST_BUFFER_G`（+5g 缓冲，吸收后续取整的损耗）。

按贡献比例分配额外克数到高蛋白食材（protein ≥ 15g/100g），而不是均匀分配：

```python
share = contribution / total_existing_protein  # 按当前贡献比例
extra_amount_g = (gap * share) / protein_per_g
```

#### c. 热量自动缩放 (`_scale_day_to_calorie_target`)

在保持食材配比的前提下，对全天所有食材做**等比例缩放**：

```python
raw_factor = target_cal / actual_cal
# 限制在 [0.5, 2.0] 内，防止出现过小或过大的份量
factor = max(MIN_SCALE_FACTOR, min(MAX_SCALE_FACTOR, raw_factor))
```

训练日 target = `base × 1.07`，休息日 target = `base × 0.96`。

#### d. 餐型硬上限夹紧 (`_clamp_meal_calories`)

热量缩放后可能导致 snack / pre_workout 超过上限（400 kcal）。此步骤对超限的餐独立做向下缩放，不影响其他餐：

```python
cap = MEAL_CALORIE_HARD_CAPS.get(recipe.meal_type)  # snack=400, pre_workout=400
if actual_cal > cap:
    factor = cap / actual_cal  # 仅缩小该餐食材
```

> 注意：此步骤后**不**立即调用 `_overwrite_macros_deterministic`，由调用者统一在 Step f 中处理。

#### e. 克数取整 (`_round_ingredient_amounts`)

```
≥ 10g  →  取整到最近的 10g
<  10g  →  取整到最近的 5g (最小 5g)
```

目的：让用户拿着购物清单时数字更直观（不出现「147.3g 鸡胸肉」这样的尴尬用量）。

---

### 两类验证的分工

| 类型                 | 时机                             | 触发效果                             | 属于哪类违规                             |
| -------------------- | -------------------------------- | ------------------------------------ | ---------------------------------------- |
| **重试型**（对话式） | 单天生成后（`_generate_day` 内） | 追加 assistant + correction 消息重试 | 食材 ID 幻觉（>2个），饮食忌口违规       |
| **警告型**（后验）   | 全部 7 天生成并后处理后          | 追加到 `cooking_tips_zh`，不中断     | 热量偏差、蛋白质不足、多样性、餐型结构等 |

重试型验证的容忍度设计值得注意：

- `MAX_UNKNOWN_FOOD_IDS_PER_BATCH = 2`：允许最多 2 个幻觉 food_id（通常是 LLM 拼写错误，不严重），超过 2 个才重试

---

### Prompt 设计（`cooking/prompt.py`）

`build_cooking_user_message()` 按以下顺序构建 9 个段落：

| #   | 段落                           | 内容                                            |
| --- | ------------------------------ | ----------------------------------------------- |
| 1   | 用户概况                       | 体重、目标、饮食限制、热量/蛋白质/碳水/脂肪目标 |
| 2   | 训练日程                       | 哪几天训练（含训练重点）、哪几天休息            |
| 3   | 训练日 vs 休息日营养目标       | 分别给出热量/碳水/脂肪目标（含计算好的数值）    |
| 4   | 食谱参考库                     | KB 筛选后的兼容食谱（经饮食限制过滤）           |
| 5   | 食材数据库（紧凑格式）         | nutrition.json 所有食材的 ID、名称、营养表      |
| 6   | 饮食替换规则                   | 仅有饮食限制时注入（如无乳糖替代方案）          |
| 7   | PlanAgent 餐食参考             | Planner 给出的餐食建议（仅参考，非强制）        |
| 8   | **已生成历史（多样性上下文）** | 所有已生成天的 DayMealPlan JSON（增量策略核心） |
| 9   | 当天任务指令                   | 明确今天是训练日/休息日、热量目标、约束清单     |

**关键设计**：段落 8 只在 `already_generated_json is not None`（即生成第 2 天起）时注入，避免第 1 天（周一）的 Prompt 过长。系统提示（`COOKING_SYSTEM`）也规定了菜品每周最多出现 **2 次**的多样性约束，与 Prompt 段落 8 形成双重约束。

**训练日判断的健壮处理**：PlannerAgent 输出的 `day_label` 可能是「周一 (Day 1)」格式，CookingAgent 在 Prompt 构建时会做前缀匹配（`d.day_label.startswith(wl)`），统一规范化为「周一」，避免训练日识别错误。

---

## LLM 客户端抽象层

**文件**：`src/fitness_agent/utils/llm_client.py`

所有 Agent 通过统一接口 `BaseLLMClient` 与 LLM 通信：

```python
class BaseLLMClient(ABC):
    def chat(
        self,
        messages: list[Message],
        *,
        system: str = "",
        max_tokens: int = 4096,
        temperature: float = 0.7,
    ) -> LLMResponse: ...
```

### 支持的提供商与 Token 管控

Agent 通过 `_MAX_TOKENS_CAP` 注册表感知不同 Provider 的输出上限，从而自动切换单步/分步生成策略。

| Provider    | 实现类               | 默认模型            | 备注                                   |
| ----------- | -------------------- | ------------------- | -------------------------------------- |
| `anthropic` | `AnthropicClient`    | `claude-haiku-4-6`  |                                        |
| `openai`    | `OpenAICompatClient` | `gpt-4o-mini`       |                                        |
| `deepseek`  | `OpenAICompatClient` | `deepseek-reasoner` | 默认使用 R1 模型，输出上限高，单批处理 |
| `qwen`      | `OpenAICompatClient` | `qwen-turbo`        |                                        |
| `gemini`    | `GeminiClient`       | `gemini-2.0-flash`  |                                        |

Provider 和模型通过 `.env` 的 `LLM_PROVIDER` / `LLM_MODEL` 配置；也可通过 CLI `--provider` / `--model` 参数临时覆盖。

---

## Prompt 文件

| Agent   | System Prompt                       | User Message 构建函数          |
| ------- | ----------------------------------- | ------------------------------ |
| Planner | `planner/prompt.py::PLANNER_SYSTEM` | `build_user_message()`         |
| Cooking | `cooking/prompt.py::COOKING_SYSTEM` | `build_cooking_user_message()` |

Planner Prompt 包含：用户画像摘要、训练规则（from KB）、动作候选池（from KB）、输出 JSON schema 示例。

Cooking Prompt（每天一次调用）包含：用户画像摘要、训练日程、营养目标（训练日 vs 休息日）、食谱参考库（from KB）、食材数据库（from KB）、饮食替换规则、PlanAgent 餐食建议、**已生成天历史 JSON**（增量策略核心）、当天任务指令（含热量目标、当天类型）。
