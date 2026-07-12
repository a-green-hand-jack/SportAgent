# lab/data/ — 数据索引层

数据集的**索引与校验信息**在这里。要找一个数据集、登记新数据、核对数据完整性，来这层。**大 bytes 不进 Git**（见根 `.gitignore`），这里只留 manifest / checksum / schema / task-set。

## 内容

| 项 | 是什么 |
| --- | --- |
| `dataset-index.yaml` | 数据集总索引（由治理流程维护） |
| `manifests/` | 每个数据集的清单（文件列表、位置、版本） |
| `checksums/` | 校验和，验证数据未被篡改/损坏 |
| `task-sets/` | 评测/实验用的任务集合定义 |
| `schemas/` | 数据结构 schema |

## 常见入口

- 找数据：先看 `dataset-index.yaml`，再到 `manifests/` 定位实际位置。
- 校验完整性：`checksums/`。
- 新增数据集：登记 index + manifest + checksum + schema，**不提交原始 bytes**。
