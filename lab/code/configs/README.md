# lab/code/configs/ — 配置

存放实验与运行的配置文件：超参、数据配置、训练/评估配置。

- 由 `../src/`、`../experiments/`、`../scripts/` 读取。
- 只放配置，不放密钥/私密路径（那些在 `../../infra/private/`）。
- 不在此存放数据或产物 bytes。
