# lab/ — 研究控制面

这里是整个 ML 研究项目的**控制面根**。所有实现、运行环境、研究事实、数据与产物索引都挂在这一层。日常「我该去哪」先看这里。

## 子层一览

| 目录 | 是什么 | 何时来 |
| --- | --- | --- |
| `code/` | 实现层：源码 / 配置 / 脚本 / 测试 / 实验入口 | 改模型、写训练/评估代码 |
| `infra/` | 运行环境层：权限 / 路径 / 存储 / 启动 / 探针 / 私密 | 配置机器、跑作业前的准备 |
| `research/` | 研究事实层：claims / evidence / ledger / gates | 记录一条结论、核对证据链 |
| `data/` | 数据索引层：manifest / checksum / schema / task-set | 找数据集、登记新数据 |
| `artifacts/` | 产物索引层：result / model / trace / table / figure 的 index | 定位某次产物、引用结果 |
| `models/` | 模型 checkpoint 索引（bytes 不进 Git） | 找某个训练权重 |
| `runs/` | 单次运行的 summary（bytes 不进 Git） | 回看一次实验跑了什么 |
| `traces/` | 人机协作轨迹（Claude Code 会话记录） | 复盘一次 agent 会话 |
| `recipes/` | 可复用的 Claude Code 工作流配方 | 复用一套已验证的做法 |
| `evals/` | 工作流 / 能力评测 | 评估一个 workflow 是否达标 |
| `reports/` | 面向人的阶段报告 | 汇报、对外交付前 |

## 常见入口

- 想看**结构地图**：`ANATOMY.md`（本层 router，指向各子目录 anatomy）。
- 想知道 **agent 能改什么**：`AGENTS.md`。
- Claude Code 读文件顺序：`CLAUDE.md`。
- 大 bytes（checkpoint、run 输出、原始数据、wandb）**一律不进 Git**，Git 里只留 manifest / index / summary。
- 任何治理相关改动后跑：`python scripts/validate-governance.py`。
- 迁移已有 repo 的 smoke eval 在 `lab/evals/adoption/run-adoption-smoke.py`。
