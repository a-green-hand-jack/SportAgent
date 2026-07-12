# lab/runs/ — 运行记录

单次运行的记录与 summary。

- 运行的原始输出 **bytes 不进 Git**（受根 `.gitignore` 覆盖，含 wandb 等）：只保留 summary。
- 结果/轨迹的完整索引见 `../artifacts/`（`result-index.yaml`、`trace-index.yaml`）。
- 实验结论登记到 `../research/experiment-ledger.yaml`。
