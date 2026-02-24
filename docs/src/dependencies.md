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
cli (依赖: planner, utils)
```

## 详细说明

| 模块 | 职责 | 依赖 |
|------|------|------|
| `utils` | 配置、日志、LLM 客户端封装 | 无 |
| `knowledge_base` | 动作库、营养数据、规则集的加载与查询 | utils |
| `user` | 用户画像 Pydantic 模型、信息收集对话流 | utils |
| `planner` | 计划生成 Agent，调用 KB 筛选 + LLM 编排 | knowledge_base, user, utils |
| `cli` | CLI 入口，串联 planner 和用户交互 | planner, utils |
