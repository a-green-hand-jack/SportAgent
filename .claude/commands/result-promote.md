---
description: 把一个实验结果升级为 evidence / paper claim（走证据门槛 + fresh verifier）
argument-hint: <run-id>
---

评估把 $ARGUMENTS 的结果 promote 进 `lab/research/evidence.yaml` / `lab/artifacts/result-index.yaml` / 论文。

先检查证据门槛（见 `.agent/artifact-policy.md`）：run 可定位、config 可复现、metric 来源清楚、
与 baseline 比较清楚、caveat 写明。

promote 是 human gate（见 `.agent/human-gates.md`）：用 tier 4 fresh verifier 复核后，
附 run id / config / commit / checkpoint / data split / metric source，再请求人工批准。
不要在有旧训练日志的当前上下文里直接下 claim。

证据门槛与 evidence 写入的完整流程见 `experiment-workflow` skill；本 command 只是它的 promote 入口。
