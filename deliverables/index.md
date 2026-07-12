# deliverables/index.md — 交付物索引

所有对外交付物的单一索引。**No overclaim**：每一个对外 claim 都必须在 `lab/research/evidence.yaml` 有支撑；下表的「evidence 齐全」列用来强制这一点。

| id | 类型 | 路径 | 支撑 claim | 状态 | evidence 齐全 |
| --- | --- | --- | --- | --- | --- |
| _(示例)_ | paper | `deliverables/paper/` | `claims.yaml#c1` | draft | 否 |

## 列说明

- **类型**：`paper` / `slides` / `release`。
- **路径**：交付物在 repo 内的位置。
- **支撑 claim**：指向 `lab/research/claims.yaml` 中的 claim id（可多个）。
- **状态**：`draft` / `submitted` / `published`。
- **evidence 齐全**：该交付物引用的每条 claim 是否都在 `lab/research/evidence.yaml` 有证据。**只要有一条 claim 缺证据，就填「否」，且该 claim 在交付物中必须标为 not yet proven 或移除。**

## 纪律

- 交付物不得引入 `evidence.yaml` 之外的结论。
- 提升状态（draft → submitted → published）前，evidence 齐全列必须为「是」，且经 human gate（见 `.agent/human-gates.md`）。
