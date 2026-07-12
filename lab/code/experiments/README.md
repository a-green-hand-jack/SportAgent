# lab/code/experiments/ — 实验入口

每个实验的入口与专属代码。调用 `../src/` 的模块、读取 `../configs/`。

- 实验产出的 bytes（checkpoint、输出）不进 Git；其索引/summary 见 `../../runs/`、`../../models/`、`../../artifacts/`。
- 实验结论登记到 `../../research/experiment-ledger.yaml`。
- 实际启动由人类经 `../../infra/launch/` 执行。
