# Parallel Task Packet 模板

并行前先定义 ownership。main / 人类维护 merge queue，worker 之间不互相 merge。

```markdown
# Parallel Task Packet

## Shared objective
<one sentence>

## Global forbidden paths
- lab/data/**
- lab/runs/**
- lab/models/**
- lab/infra/private/**
- checkpoints/**
- wandb/**

## Worker A
- Task:
- Owns:
- Must not touch:
- Verification:
- Report path: .claude/agent-reports/<task-a>.md

## Worker B
- Task:
- Owns:
- Must not touch:
- Verification:
- Report path: .claude/agent-reports/<task-b>.md

## Merge order
1. Worker A
2. Worker B

## Human / main-agent review
- read reports
- inspect git diff
- run integration test
- update anatomy / ledgers / memory if needed
```
