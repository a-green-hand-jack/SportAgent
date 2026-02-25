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

### `generate_cooking_plan(weekly_plan, profile)` 流程

```
Step 1 ── 食谱兼容性过滤
          ├─ get_compatible_recipes(dietary_restrictions)
          └─ get_banned_food_ids(dietary_restrictions)

Step 2 ── 分批 LLM 生成（避免超出 token 上限）
          Batch A: 第 1-4 天
          Batch B: 第 5-7 天

          每批 (_generate_batch):
            for attempt in range(max_retries + 1):
              response = client.chat(batch_prompt, max_tokens=8192)
              days = _parse_batch_response(response)
              _overwrite_macros_deterministic(days)  # 用 KB 数据覆盖 LLM 报告的宏量
              dietary_warnings = _validate_dietary_compliance(days, banned_food_ids)
              calorie_warnings = _validate_calorie_compliance(days, calorie_target)
              if warnings: 追加纠错 message → 重试
              else: break

Step 3 ── 汇总
          合并 14 天 → 7 天计划
          _aggregate_shopping_list()   # 去重聚合购物清单
          返回 WeeklyCookingPlan
```

### 宏量素覆写（`_overwrite_macros_deterministic`）

LLM 报告的营养数值**不可信**，Agent 在每次生成后自动覆写：

1. 遍历每道菜的 `ingredient food_ids × amount_g`
2. 从 `nutrition.json` 查出精确数值
3. 覆写 `per_serving_macros`
4. 重算 `day_total_macros`

### 食谱多样性校验（`_validate_diversity`）

- 同一 `recipe_id` 出现 > 50% 的餐次 → 警告
- 蛋白质来源 < 3 种食材 ID → 警告
- 这些警告**不触发重试**，仅记录日志

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

### 支持的提供商

| Provider    | 实现类               | 默认模型           | 备注                       |
| ----------- | -------------------- | ------------------ | -------------------------- |
| `anthropic` | `AnthropicClient`    | `claude-haiku-4-6` | system prompt 作为独立字段 |
| `openai`    | `OpenAICompatClient` | `gpt-4o-mini`      |                            |
| `deepseek`  | `OpenAICompatClient` | `deepseek-chat`    | max_tokens 上限 8192       |
| `qwen`      | `OpenAICompatClient` | `qwen-plus`        |                            |
| `gemini`    | `GeminiClient`       | `gemini-2.0-flash` |                            |

Provider 和模型通过 `.env` 的 `LLM_PROVIDER` / `LLM_MODEL` 配置；也可通过 CLI `--provider` / `--model` 参数临时覆盖。

---

## Prompt 文件

| Agent   | System Prompt                       | User Message 构建函数  |
| ------- | ----------------------------------- | ---------------------- |
| Planner | `planner/prompt.py::PLANNER_SYSTEM` | `build_user_message()` |
| Cooking | `cooking/prompt.py` 中的常量        | `build_batch_prompt()` |

Prompt 包含：用户画像摘要、训练/营养规则（from KB）、动作/食谱候选池（from KB）、输出 JSON schema 示例。
