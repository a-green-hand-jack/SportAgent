# DECISIONS

> 轻量 ADR 索引。为什么接受/拒绝某个规则、recipe、架构或实验方向。

决策正文放在 `human/decisions/<YYYYMMDD>-<slug>.md`，本文件只做索引。

原则：

- 每条决策是一个小文件，不是聊天记忆。可被 fresh session 与 review 读懂。
- 决策若改变 agent 行为，应同时更新对应的 `.agent/` doctrine 或 `.claude/` 能力，并在同一 commit 内。
- 决策若改变研究结论口径，应同步 `lab/research/`。

## 索引

| 日期 | 决策 | 状态 | 文件 |
| --- | --- | --- | --- |
| YYYY-MM-DD | 采用本模板作为项目控制根 | accepted | `human/decisions/00000000-adopt-template.md` |
| 2026-07-09 | 书面文档默认使用中文 | accepted | `human/decisions/20260709-doc-language-default-chinese.md` |
| 2026-07-09 | `lab/docs/` 下 reference / research-narrative 平面与外部 vendor 代码位置 | accepted | `human/decisions/20260709-lab-docs-reference-and-external-vendor-placement.md` |

状态取值：`proposed` · `accepted` · `superseded` · `rejected`。
