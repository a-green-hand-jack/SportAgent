# lab/infra/launch/ — 启动命令

存放**可复现的启动命令**：一条命令能重跑某次训练/评测。

- **启动是人类闸门**：命令由人审阅后执行，agent 不自动运行。
- 命令应可复现：固定配置、数据版本、环境。
- 产出 bytes 不进 Git；index/summary 见 `../../runs/`、`../../models/`、`../../artifacts/`。
