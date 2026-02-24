# Claude Code Instructions — fitness-agent

## 项目概览

AI 驱动的个性化健身规划系统。V1 目标：用户通过问答提供个人信息，LLM 结合结构化知识库（动作库 + 营养数据 + 规则集）生成个性化的训练计划和营养方案。

### 核心架构原则
- **知识库负责确定性逻辑**：热量计算、动作安全过滤、规则约束
- **LLM 负责创造性编排**：计划组合、个性化表达、自然语言输出
- 两者职责分明，不要让 LLM 做应该确定性完成的事

## 模块结构

```
src/fitness_agent/
├── knowledge_base/   # 知识库：动作库、营养数据、训练规则
├── planner/          # 规划 Agent：用户建模、计划生成、LLM 交互
├── user/             # 用户模型：画像、信息收集对话流
├── utils/            # 工具：日志、配置、LLM 客户端封装
└── cli.py            # CLI 入口
```

对应文档在 `docs/src/` 下。

## 开发规范

1. **每个 src 模块必须有对应 tests**，路径镜像：`src/fitness_agent/X/Y.py` → `tests/X/test_Y.py`
2. **测试数据隔离**：测试专用 `tests/data/` 和 `tests/outputs/`，不共享主项目目录
3. **绝对导入**：包已 editable 安装，始终用 `from fitness_agent.X import Y`
4. **类型注解**：所有公共函数加类型注解
5. **Pydantic 数据模型**：所有结构化数据（用户画像、动作、计划）用 Pydantic BaseModel

## 环境管理

- 始终用 `uv run` 执行脚本
- 添加依赖用 `uv add <package>`
- 运行测试：`uv run pytest`

## 新增功能流程

1. 在 `docs/dev/features/` 创建功能文档
2. 在 `src/fitness_agent/` 实现
3. 在 `tests/` 编写测试
4. 更新 `docs/src/` 对应模块文档

## 知识库数据位置

- 动作库：`data/raw/exercises.json`
- 营养数据：`data/raw/nutrition.json`
- 训练规则：`data/raw/rules.json`
- 处理后的数据：`data/processed/`
