# lab/research/ — 研究事实层

项目的**结构化事实真相**在这里：主张、证据、实验台账、回归矩阵、发布闸门。要记录一条结论、核对某个 claim 有没有证据、判断能不能发布，来这层。

## 文件（由治理流程维护的 YAML）

| 文件 | 是什么 |
| --- | --- |
| `claims.yaml` | 能力级 / 论文级主张 |
| `evidence.yaml` | 支撑每条 claim 的证据（分层，见下） |
| `experiment-ledger.yaml` | 实验台账：跑过什么、结论是什么 |
| `regression-matrix.yaml` | 回归矩阵：关键指标是否退化 |
| `release-gates.yaml` | 发布闸门：满足哪些条件才能对外交付 |

## 证据分层

```
log  <  metric  <  table  <  figure  <  paper claim
```

越往右越强。一条 claim 的强度不能超过其最强证据。

## 常见入口

- 写结论前先想：它落在哪一层证据？
- 交付/发文前核对 `release-gates.yaml` 与 `claims.yaml`：**不得 overclaim 超出 `evidence.yaml`**。
