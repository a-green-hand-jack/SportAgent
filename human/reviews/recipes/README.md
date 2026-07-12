# human/reviews/recipes/ — recipe 评审

评审对象是 Claude Code **recipe 的小 diff**：一次只改一个小工作流（新增/调整一条 recipe），保持 diff 小、可快速判断。流程与标准见 `.agent/claude-code-recipe-policy.md`。

## 流程

1. agent 把 recipe 变更做成**小 diff**（对应 `lab/recipes/claude-code/<id>.md`）。
2. 在本目录放 review 记录：这条 recipe 解决什么问题、证据/实测、影响范围。
3. human 评审：值不值得采用、有无风险、是否替代已有 recipe。
4. 批准 → 进 `memory/current-practices.md`；淘汰 → 记 `memory/deprecated-practices.md`。

## 为什么要小 diff

recipe 影响 agent 的日常行为，改动要能被快速理解和回滚。大而杂的 recipe 变更应拆分后分别评审。

## review 应包含

- recipe id 与 diff 指针。
- 采用理由与证据（指向实测或 `human/reviews/results/`）。
- 建议 status（trial/adopted）与 expires。
- human 结论与日期。
