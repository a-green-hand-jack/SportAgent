# deliverables/ — 对外承诺层

这里放**要给外部世界看的东西**：论文、slides、代码 release。核心纪律只有一条——

> **No overclaim**：任何对外 claim 都不能超过 `lab/research/evidence.yaml` 能支撑的证据。

## 什么时候来这里

- 准备投稿 / 做报告 / 发 release。
- 想知道某个交付物引用了哪些 claim、证据是否齐全：看 `index.md`。
- 修改交付物内容：先确认对应 claim 在 `lab/research/claims.yaml` 有登记、且 `evidence.yaml` 有支撑，且改动走 human gate。

## 目录

| 路径 | 内容 |
| --- | --- |
| `index.md` | 交付物索引（含 claim 支撑与证据齐全度） |
| `paper/` | 论文来源（LaTeX / figure / table）+ writing contract |
| `slides/` | 报告 slides |
| `release/` | 代码 / 模型 / 数据 release |

## 边界

交付物是 repo 中「最不能随便改」的一层。所有改动走 human gate（见 `.agent/human-gates.md`）；LaTeX / figure / table 必须能追溯到 `lab/` 里的产物与 run。详见 `AGENTS.md`。
