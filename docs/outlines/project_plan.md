# V1 项目计划

## 目标
用户通过问答输入个人信息（身高体重、目标、可用时间、器材、伤病史），系统生成个性化的**训练计划**和**营养方案**。

## 阶段划分

### Phase 1：知识库 (KB)
- [ ] 设计动作库数据结构（Exercise Pydantic 模型）
- [ ] 整理初始动作库数据（80 个核心动作）
- [ ] 设计营养数据结构（FoodItem 模型）
- [ ] 整理常见食物营养数据（500+ 种）
- [ ] 设计规则集结构（TrainingRule 模型）
- [ ] 编写核心训练规则（增肌/减脂/体态改善）

### Phase 2：用户模型 (User)
- [ ] 设计用户画像 Pydantic 模型（UserProfile）
- [ ] 实现信息收集对话流（OnboardingConversation）
- [ ] 实现 BMR/TDEE 计算逻辑

### Phase 3：规划 Agent (Planner)
- [ ] 实现 LLM 客户端封装（支持 Anthropic / OpenAI）
- [ ] 实现 KB 确定性筛选逻辑（动作过滤、营养目标计算）
- [ ] 设计 Prompt 模板（system + user context）
- [ ] 实现计划生成流程
- [ ] 设计输出格式（WeeklyPlan Pydantic 模型）

### Phase 4：CLI 整合
- [ ] 完善交互式 chat 命令
- [ ] 美化 rich 输出（计划展示）

## 成功标准
- 给定用户信息，能在 30 秒内生成一份完整的周训练计划 + 每日营养方案
- 计划符合基本运动科学原则（通过规则集约束验证）
- 覆盖：增肌、减脂、体态改善三个目标
