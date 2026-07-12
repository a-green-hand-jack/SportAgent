---
description: 把一个任务拆成有清晰文件所有权的并行 worker packet
---

先经 `subagent-routing` skill 为每个子任务选 model/effort/tools（见 `.agent/model-routing-policy.md`）。

用 `.agent/templates/parallel-task-packet.md` 产出 packet，必须包含：
- shared objective、global forbidden paths
- 每个 worker 的 task / owns / must-not-touch / verification / report path
- merge order、review 步骤

不派发无边界的 general-purpose worker。隔离先于并行——不满足 `.agent/checklists/pre-parallel.md` 就不并行。
