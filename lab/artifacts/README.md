# lab/artifacts/ — 产物索引层

所有产物的**索引**在这里：结果、模型、轨迹、表、图。这层**只存 index，不存 bytes**——真实文件在外部存储，Git 里只留可追溯的指针。

## 文件（index YAML，由治理流程维护）

| 文件 | 索引什么 |
| --- | --- |
| `result-index.yaml` | 实验结果 |
| `model-index.yaml` | 模型 checkpoint |
| `trace-index.yaml` | 运行/会话轨迹 |
| `table-index.yaml` | 表格产物 |
| `figure-index.yaml` | 图产物 |

## 常见入口

- 要引用某个结果/图/表，先在对应 index 找到条目与其外部位置。
- `../research/evidence.yaml` 会引用这些 index 作为证据。
- **bytes 不进 Git**：checkpoint、图片、原始输出都在外部存储，这里只有 index。
