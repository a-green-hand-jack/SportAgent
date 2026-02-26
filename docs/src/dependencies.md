# 模块依赖关系

```
utils (无依赖)
  ↑
knowledge_base (依赖: utils)
  ↑
user (依赖: utils, knowledge_base)
  ↑
gym ————┐
  ↑     │ (依赖: utils, user, knowledge_base)
planner ┘
  ↑
graph (依赖: knowledge_base, user, planner, cooking, gym, utils)
  ↑
cli (依赖: graph, user, utils)
```

## 详细说明

| 模块             | 职责                                                                            | 依赖                                               |
| ---------------- | ------------------------------------------------------------------------------- | -------------------------------------------------- |
| `utils`          | 配置、日志、LLM 客户端封装（多 Provider）                                       | 无                                                 |
| `knowledge_base` | 动作库、营养数据、食谱库、规则集的加载与查询                                    | utils                                              |
| `user`           | 用户画像 Pydantic 模型、信息收集对话流、BMR/TDEE 计算                           | utils, knowledge_base                              |
| `planner`        | 训练计划 Pydantic 模型与专有 Prompt 定义                                        | knowledge_base, user, utils                        |
| `cooking`        | 饮食计划 Pydantic 模型与专有 Prompt 定义                                        | knowledge_base, user, planner.models, utils        |
| `gym`            | 单课训练计划模型、强度计算逻辑 (RPE) 与专有 Prompt 定义                         | knowledge_base, user, utils                        |
| `graph`          | **LangGraph 核心**：节点定义 (plan/cook/gym)、Registry 权限管控、工具集 (Tools) | knowledge_base, user, planner, cooking, gym, utils |
| `cli`            | CLI 入口（Typer），负责初始化 Graph 并执行 `invoke`                             | graph, user, utils                                 |

## 延伸阅读

- [agent-implementation.md](agent-implementation.md)：基于 LangGraph 的节点实现与 Registry 模式
- [knowledge-storage.md](knowledge-storage.md)：知识库 JSON 文件结构与 KnowledgeAccessors 接口
- [information-flow.md](information-flow.md)：基于 StateGraph 的 Agent 编排流水线
