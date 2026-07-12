---
description: 只读监控一个长实验（不 kill/restart/改 config）
argument-hint: <run-id 或 log 路径>
---

用 `experiment-monitor` subagent 监控 $ARGUMENTS。

只读：
- log 最后 200 行
- run dir 的 status 文件
- wandb/mlflow 最新 metrics（若有）

只报异常：crash / NaN / OOM / stall / missing checkpoint / config mismatch。
报告 status、latest metrics、checkpoint freshness、是否需要介入。不修改任何东西。
遵循 `.agent/action-boundary.md`。
