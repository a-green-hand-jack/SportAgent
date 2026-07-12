# ANATOMY — deliverables/ 结构图

模板骨架（template scaffold）。描述**预期结构**与证据流，非已存在代码；文件按名引用，不含 `file:line`。

## 组件

```
deliverables/
├── index.md      交付物索引（claim 支撑 + 证据齐全度 + 状态）
├── paper/        论文来源：LaTeX / figure / table + writing contract
├── slides/       报告 slides
└── release/      代码 / 模型 / 数据 release
```

## 证据流（no-overclaim 链）

```
lab/artifacts/            (真实产物：figure/table/metric/run)
      │  被引用
lab/research/evidence.yaml   (证据登记：哪条证据支撑什么)
      │  支撑
lab/research/claims.yaml     (claim 登记：项目主张)
      │  被交付物引用
deliverables/<paper|slides|release>   (对外表述)
      │  索引
deliverables/index.md        (谁引用了哪些 claim、证据齐全否)
```

任一环缺失 → 该 claim 视为 **not yet proven**，不得对外写死。

## 持久状态归属

- **索引/状态**：`index.md`（随交付物进展更新）。
- **来源**：`paper/`、`slides/`、`release/` 内容，须可追溯回 `lab/`。
- **契约**：`paper/README.md` 内的 writing contract 骨架。

## 边界

- 所有实质改动经 human gate（`.agent/human-gates.md`）与 `human/reviews/results/`。
- 实验事实/探索在 `lab/`，不在此。
- 对外表述之外的内部状态在 `memory/`，不在此。
