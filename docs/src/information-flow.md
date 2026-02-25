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
[PlannerAgent.generate_plan(profile)]
   │
   ├─ KB 过滤：动作安全池
   ├─ build_user_message() → prompt
   ├─ LLM call #1 (system + user)
   ├─ validate → 若有问题追加 correction message
   ├─ LLM call #2（可选，最多 max_retries 次）
   └─ → WeeklyPlan（JSON）
   │
   ├──► 保存 JSON + Markdown 到 outputs/
   ├──► Rich 终端渲染显示
   │
   └── [--cook 标志 或 cook 子命令？]
           yes ↓
   ▼
[CookingAgent.generate_cooking_plan(weekly_plan, profile)]
   │
   ├─ KB 过滤：食谱兼容性
   ├─ Batch A prompt (Day 1-4) → LLM → 验证 → 重试
   ├─ Batch B prompt (Day 5-7) → LLM → 验证 → 重试
   ├─ 宏量素覆写（确定性计算）
   └─ → WeeklyCookingPlan（JSON）
   │
   └──► 保存 JSON + Markdown → Rich 终端渲染
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

## 阶段三：PlannerAgent 内部信息流

```
UserProfile
    │
    ├─► KB.get_safe_exercises(injuries, equipment)
    │       → exercise_pool: list[Exercise]（最多 60 个）
    │
    ├─► build_user_message(profile, kb, exercise_pool)
    │       → user_message: str（包含用户画像摘要 + 规则 + 动作池）
    │
    └─► LLM 多轮对话
            messages = [
              Message(role="user", content=user_message),
              # 若验证失败，追加：
              Message(role="assistant", content=上轮LLM回复),
              Message(role="user", content=correction_message),
              # 最多 max_retries 轮
            ]
            system = PLANNER_SYSTEM

            LLMResponse.content (JSON string)
                │
            _parse_response()
                │
            WeeklyPlan (Pydantic)
                │
            validate (volume / duration / injury)
                │
            若通过 → 返回
            若失败 → 追加 correction → 重试
```

**LLM 看到的信息**：

- System prompt：教练角色定义、JSON 输出格式
- User message：用户名/年龄/目标/水平/器材/伤病/训练安排/热量目标 + 动作池 + 训练规则

**LLM 输出的信息**：

- 纯 JSON 字符串（`WeeklyPlan` schema）

---

## 阶段四：CookingAgent 内部信息流

```
WeeklyPlan + UserProfile
    │
    ├─► KB.get_compatible_recipes(dietary_restrictions)
    │       → compatible_recipes: list[RecipeTemplate]
    │
    ├─► KB.get_banned_food_ids(dietary_restrictions)
    │       → banned_food_ids: set[str]
    │
    └─► Batch A (Day 1-4)
    │       messages = [Message(role="user", content=batch_prompt)]
    │       batch_prompt 包含：
    │         - 用户热量/蛋白质目标
    │         - 训练日 vs 休息日安排
    │         - 饮食限制
    │         - 食谱候选池（cuisine + ingredients）
    │         - 输出 JSON schema
    │       LLM → JSON string
    │       _parse_batch_response() → list[DayMealPlan]
    │       _overwrite_macros_deterministic()   ← 覆写宏量素
    │       validate dietary + calorie
    │       （若失败追加 correction → 重试一次）
    │
    └─► Batch B (Day 5-7)  同上

合并 → WeeklyCookingPlan → _aggregate_shopping_list()
```

---

## 数据在各层之间的传递

```
JSON 文件 (data/raw/)
    ↓ 启动时加载（cached_property）
KnowledgeBase（内存对象）
    ↓ 传入
Agent.__init__(client, kb)
    ↓ 每次调用
generate_plan(profile) / generate_cooking_plan(plan, profile)
    ↓
构建 prompt str → 发给 LLM API
    ↓ 返回
JSON str → Pydantic 模型验证
    ↓
WeeklyPlan / WeeklyCookingPlan
    ↓
CLI 渲染（Rich）+ 保存（JSON + Markdown）
    ↓
用户看到的终端输出 + outputs/ 目录下的文件
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

| 组件            | 状态                   | 说明                                    |
| --------------- | ---------------------- | --------------------------------------- |
| `KnowledgeBase` | **有状态**（内存缓存） | 启动后常驻，不同请求共享同一实例        |
| `PlannerAgent`  | **无状态**             | 每次 `generate_plan()` 独立，不保留历史 |
| `CookingAgent`  | **无状态**             | 同上                                    |
| `UserProfile`   | **文件持久化**         | 以 JSON 保存在用户指定路径              |
| 训练/烹饪计划   | **文件持久化**         | 以 JSON + Markdown 保存在 outputs/      |
| LLM 对话历史    | **请求内临时**         | 仅在 retry 循环内追加，请求结束后丢弃   |
