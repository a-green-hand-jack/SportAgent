# Agent 与用户交互的信息流

## 完整流程概览

```
用户终端
   │
   ▼
[CLI] fitness-agent plan
   │  (typer + Rich)
   │
   ├──► [加载已有 profile？]
   │         yes → load_profile(path)
   │         no  ↓
   │
   ▼
[Onboarding Q&A]  user/onboarding.py
    │  终端问答 → UserProfile（Pydantic）
    │  + enrich_profile() → BMR/TDEE/热量目标
    │  + parse_injuries_with_llm()（可选 LLM 调用）
    │
    ▼
[LangGraph 编排流 (StateGraph)]
    │
    ▼ (START)
[plan_node] — 生成周训练计划
    │  ├─ 调用 split_engine (KB 过滤)
    │  ├─ LLM 生成 WeeklyPlan
    │  ├─ 调用 volume_checker (容量校验)
    │  └─ 对话式重试 (max_retries=2)
    │
    ▼ (Conditional Edge)
[cook_node] — 生成周饮食计划 (should_cook 为 True 时)
    │  ├─ 增量逐日生成 (7 次调用，历史 JSON 注入)
    │  ├─ 调用 deterministic_scaler (热量/蛋白修正)
    │  └─ 调用 grocery_gen (购物清单聚合)
    │
    ▼ (Conditional Edge)
[gym_node] — 生成单课训练卡 (should_gym 为 True 时)
    │  ├─ 热身/拉伸模板自动匹配
    │  ├─ 调用 rpe_engine (重量推荐)
    │  └─ 调用 training_card_exporter (KB 数据注入)
    │
    ▼ (END)
```

---

## 阶段一：CLI 入口

**文件**：`src/fitness_agent/cli.py`（Typer app）

```bash
fitness-agent plan [--provider anthropic] [--model claude-opus-4-6]
                   [--profile path/to/profile.json]
                   [--output path/to/output.json]
                   [--cook]
```

CLI 做的事：

1. 解析命令行参数
2. 构建 `LLMClient`（通过 `build_client_from_config()` 或 `--provider/--model` 覆盖）
3. 加载 `KnowledgeBase`
4. 决定走"新用户问卷"还是"加载已有 profile"

---

## 阶段二：Onboarding 问卷

**文件**：`src/fitness_agent/user/onboarding.py`

```
终端输入 ──► _ask() / _ask_choice() / _ask_float() / _ask_int()
                │
                ▼
        [顺序收集以下信息]
        1. 姓名、年龄、性别、身高、体重
        2. 训练目标（GoalType 枚举）
        3. 训练经验水平（ExperienceLevel 枚举）
        4. 日常活动水平
        5. 每周训练天数 + 每次时长
        6. 力量水平自评
        7. 偏好训练时间
        8. 可用器材（多选，Equipment 枚举）
        9. 伤病描述（自由文本 → LLM 解析 → ContraindicationTag）
        10. 饮食限制（逗号分隔字符串）
                │
                ▼
        UserProfile（Pydantic）
                │
        enrich_profile()  ← user/calculator.py
          Mifflin-St Jeor 公式算 BMR
          × 活动系数算 TDEE
          ± 目标热量缺口/盈余
          计算蛋白质目标
                │
                ▼
        UserProfile (enriched)
        save_profile(profile, path)  →  profile.json（可选持久化）
```

### 伤病信息的 LLM 解析

当用户输入自由文本伤病描述时（如"手腕疼、膝盖不好"），会触发一次额外的 LLM 调用：

```python
# utils/text_parser.py
parse_injuries_with_llm(raw_text, llm_client)
    → list[ContraindicationTag]
```

解析结果会展示给用户确认，用户可选择接受或清除。

---

## 阶段三：plan_node 内部信息流

```
FitnessAgentState (user_profile)
    │
    ├─► split_engine(profile, kb)
    │       → exercise_pool: list[Exercise]（最多 60 个）
    │
    ├─► build_user_message(profile, kb, exercise_pool)
    │       → user_message: str
    │
    └─► LLM 多轮对话 (plan_nodeRetry)
            messages = [Message(role="user", content=user_message)]
            LLM → JSON string

            [校验项 - 触发对话式重试]
            ├─ volume_checker()         # 容量校验 (from anatomy.json)
            ├─ _validate_duration()     # 时长校验
            └─ _validate_injuries()     # 伤病再确认

            若失败 → 追加 correction message → 重试 (max 2)

    写入 state["weekly_plan"]
```

**LLM 看到的信息**：

- System prompt：教练角色定义、JSON 输出格式
- User message：用户名/年龄/目标/水平/器材/伤病/训练安排/热量目标 + 动作池 + 训练规则

**LLM 输出的信息**：

- 纯 JSON 字符串（`WeeklyPlan` schema）

---

## 阶段四：cook_node 内部信息流

```
FitnessAgentState (user_profile + weekly_plan)
    │
    ├─► CookingKnowledge.get_recipes()
    │       → compatible_recipes: list[RecipeTemplate]
    │
    └─► 增量逐日生成循环 (Incremental Loop)
        for day in [周一 … 周日]:
            already_generated_json = json.dumps(history)
            LLM call → DayMealPlan

            [重试型校验 - 针对当天]
            ├─ _validate_food_ids()           # 食材 ID 幻觉
            └─ _validate_dietary_compliance() # 忌口违规

            若失败 → 追加 correction → 局部重试

    [确定性后处理工具链 - 一次性处理 7 天]
    ├─ deterministic_scaler()
    │    ├─ _overwrite_macros_deterministic() # 覆写宏量素（查 KB）
    │    ├─ _scale_day_to_calorie_target()    # 自动热量缩放
    │    └─ _boost_protein_for_day()          # 针对性强化蛋白
    └─ grocery_gen()                          # 跨天聚合购物清单

    写入 state["cooking_plan"]
```

---

## 阶段五：gym_node 内部信息流

```
FitnessAgentState (user_profile + weekly_plan)
    │
    ├─► GYMKnowledge.get_warmup_template()
    │       → 基于动作模式自动匹配热身序列
    │
    ├─► LLM 生成单课计划 (GymSessionPlan)
    │
    └─► training_card_exporter() (确定性注入)
            ├─ 注入动作细节 (cues, muscles, videos)
            ├─ 注入热身/拉伸序列 (带伤病调整)
            └─ 注入伤病适配提示 (injury_adaptations)

    写入 state["gym_plan"]
```

---

## 数据在各层之间的传递

```
KnowledgeBase (Raw JSON)
    ↓
KnowledgeAccessors (Scoped View)
    ↓
Graph State (FitnessAgentState)
    ↓
Agent Nodes (Logic & LLM)
    ↓
Deterministic Tools (Calculations)
    ↓
Graph State (Results)
    ↓
CLI (Rich Rendering)
```

---

## IO 注入设计（可测试性）

`run_onboarding()` 接受 `ask_fn` 和 `print_fn` 参数，默认为 `input` 和 `print`，在 CLI 中被替换为 Rich Console 的输入/输出方法。

这使得 onboarding 模块可以在测试中不依赖真实终端：

```python
# 测试示例
answers = iter(["Alice", "25", "1", "165", "60", ...])
profile = run_onboarding(
    ask_fn=lambda _: next(answers),
    print_fn=lambda *a, **kw: None,
)
```

---

## 无状态 vs 有状态

| 组件            | 状态                       | 说明                                    |
| --------------- | -------------------------- | --------------------------------------- |
| `KnowledgeBase` | **有状态**（内存缓存）     | 启动后常驻，跨节点共享                  |
| `graph`         | **无状态/短轮询**          | 每次 invoke 一个新图，由 LangGraph 管理 |
| `Agent Nodes`   | **无状态**                 | 纯函数节点，不保留私有历史              |
| `UserProfile`   | **持久化 JSON**            | 用户关键特征，作为图的初始输入          |
| `WeeklyPlan`等  | **持久化 JSON / Markdown** | 图运行完成后的最终产物                  |
| `LLM 历史`      | **状态感知**               | 在 cook_node 循环中通过 state 显式传递  |
