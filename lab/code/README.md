# lab/code/ — 实现层

一切**可执行代码**都在这里：源码、配置、脚本、测试、实验入口。想改模型、写训练/评估逻辑、加一个实验，就来这层。

## 子目录

| 目录 | 是什么 |
| --- | --- |
| `imported/SportAgent/` | SportAgent 产品单元：源码、数据、测试、文档与 uv 环境 |
| `src/` | 模板预留的通用源码层；当前 SportAgent 不使用 |
| `configs/` | 配置文件（超参、数据、运行配置） |
| `scripts/` | 一次性 / 运维 / 数据处理脚本 |
| `tests/` | 单元与集成测试 |
| `experiments/` | 实验入口与实验专属代码 |

## 常见入口

- SportAgent 核心逻辑在 `imported/SportAgent/src/fitness_agent/`。
- 产品依赖与测试从 `imported/SportAgent/` 运行，使用其 `pyproject.toml` 与 `uv.lock`。
- 新实验从 `experiments/` 起步，配置放 `configs/`。
- 提交前跑 `tests/`。
