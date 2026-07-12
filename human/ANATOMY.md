# ANATOMY — human/ 结构图

模板骨架（template scaffold）。描述**预期结构**与协作流，非已存在代码；文件按名引用，不含 `file:line`。

## 组件

```
human/
├── briefs/
│   ├── active/       进行中的任务 brief
│   └── completed/    已完成 brief（归档）
├── reviews/
│   ├── plans/        plan 评审
│   ├── results/      result 评审
│   └── recipes/      recipe 小 diff 评审
├── decisions/        轻量 ADR（+ 采用模板的示例 ADR）
└── inbox/            未整理输入
```

## 协作流

```
human 写 brief → briefs/active/
      │
agent 读 brief → 起草 plan → reviews/plans/  ─(human 批准)─┐
      │                                                     │
agent 执行 → 结果 → reviews/results/  ─(human 批准)──────────┤
      │                                                     │
agent 提 recipe 小 diff → reviews/recipes/ ─(human 批准)─────┤
      │                                                     ▼
重要判断固化为 ADR → decisions/ ──(human 置 accepted)──→ 根 DECISIONS.md 索引
      │
brief 完成 → briefs/completed/

零散输入 → inbox/ → 定期分类到以上正式位置
```

## 权威与状态

- **权威源**：`briefs/`、`decisions/`（accepted）——以 human 为准，agent 遵守。
- **待决**：`reviews/`、`decisions/`（proposed）——等待 human 动作。
- **缓冲**：`inbox/`——临时，定期清空。

## 边界

- 接受/拒绝、批准/驳回是 human 动作，agent 只起草与整理。
- gate 契约见 `.agent/human-gates.md`；recipe review 见 `.agent/claude-code-recipe-policy.md`。
