# 模块依赖关系

```
utils (无依赖)
  ↑
knowledge_base (依赖: utils)
  ↑
user (依赖: utils)
  ↑
planner (依赖: knowledge_base, user, utils)
  ↑
cooking (依赖: knowledge_base, user, planner.models, utils)
  ↑
cli (依赖: planner, cooking, utils)
```

## 详细说明

| 模块             | 职责                                                   | 依赖                                        |
| ---------------- | ------------------------------------------------------ | ------------------------------------------- |
| `utils`          | 配置、日志、LLM 客户端封装（多 Provider）              | 无                                          |
| `knowledge_base` | 动作库、营养数据、食谱库、规则集的加载与查询           | utils                                       |
| `user`           | 用户画像 Pydantic 模型、信息收集对话流、BMR/TDEE 计算  | utils                                       |
| `planner`        | 训练计划生成 Agent，调用 KB 筛选 + LLM 编排 + 验证重试 | knowledge_base, user, utils                 |
| `cooking`        | 饮食计划生成 Agent，分批 LLM 生成 + 确定性宏量覆写     | knowledge_base, user, planner.models, utils |
| `cli`            | CLI 入口（Typer），串联问卷 → planner → cooking → 展示 | planner, cooking, utils                     |

## 延伸阅读

- [agent-implementation.md](agent-implementation.md)：PlannerAgent 与 CookingAgent 的实现细节
- [knowledge-storage.md](knowledge-storage.md)：知识库 JSON 文件结构与 KnowledgeBase 查询接口
- [information-flow.md](information-flow.md)：用户与系统交互的完整信息流
