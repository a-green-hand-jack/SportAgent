# Claude Code Recipe 政策

Claude Code 会漂移。防漂移不是只写「验证日期 / 版本 / 最小复现」这些元数据，而是把技巧当 repo-local recipe：从真实摩擦中提炼、绑证据、定期复测、会降级会过期。

## 流水线

```
human-cc trace
→ 自动切片
→ workflow-recipe-harvester 提候选 recipe
→ 绑证据 / 适用条件 / 反例 / 复测任务
→ human review（review 对象是小 diff，不是长总结）
→ 写入 memory/current-practices.md
→ 定期复测 / 降级 / 废弃
```

## repo surface

```
lab/traces/human-cc/<date>/<session>/  原始或脱敏 trace
lab/recipes/claude-code/<id>.yaml       recipe
lab/evals/cc-workflow/<id>.yaml         复测任务与判定器
lab/reports/cc-workflow/<date>-*.md     复测报告
memory/current-practices.md             当前采用索引
memory/deprecated-practices.md          失效技巧与原因
human/reviews/recipes/                  human review
```

## recipe 状态机

```
candidate     少量 trace 支持，不能作默认规则。
provisional   有复测任务且连续通过≥2次，可局部采用。
stable        跨任务类别仍有效，写入 current-practices。
deprecated    复测失败 / 产品行为变化 / 被更简单 recipe 取代。
```

## harvester 只提炼有行为证据的结构片段

`stuck→recovery`、`plan drift→correction`、`tool failure→fallback`、`review comment→durable rule`、`context loss→repo recovery`。不总结「Claude Code 很好用」。

## 触发复测

每周一次；CC/模型/权限/hooks/settings/subagent 行为升级后；AGENTS/`.agent`/skills/hooks/validators 变化后；某 recipe 相关任务失败后。每条 recipe 绑 1-3 个小任务（一正例、一边界、一反例）。schema 见 `lab/recipes/claude-code/EXAMPLE.yaml`。
