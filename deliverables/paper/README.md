# deliverables/paper/ — 论文

论文来源（LaTeX / figure / table）。这是对外承诺层里要求最严的部分。

## 边界

- 所有实质改动走 **human gate**（见 `.agent/human-gates.md`），并经 `human/reviews/results/` 评审。
- 每张 figure / table / 每个数字都要**可追溯**到 `lab/artifacts/` 的产物或 run id——不允许手填无来源数字。
- 论文里的每条 claim 必须在 `lab/research/claims.yaml` 登记、`lab/research/evidence.yaml` 有支撑。未证明的写进下面 contract 的 "claims not yet proven"，不写进正文结论。

---

## Writing contract（骨架）

> 写作前先填这份极简契约，让 agent 和 human 对「这篇论文在讲什么、能讲什么」达成一致。

### Target venue
（目标会议/期刊 + 截止日 + 页数/格式限制。）

### Paper story
（一段话：核心 narrative，读者读完应记住什么。）

### Non-negotiable claims
（必须站得住的核心主张，每条指向 `claims.yaml` 的 id，且 `evidence.yaml` 有支撑。）

### Claims not yet proven
（想说但**证据尚不足**的主张。默认不写进正文结论，或明确标注为 limitation / future work。）

### Figure & table sources
（每张图表 → 来源产物/run id/生成脚本路径。可追溯是硬要求。）

### Sections to edit
（本轮允许改的章节。）

### Sections not to edit
（本轮禁止改的章节——如已定稿部分、合作者负责部分。）
