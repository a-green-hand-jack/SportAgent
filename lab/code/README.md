# lab/code/ — 实现层

此目录是未来产品集成、实验与测试的代码控制面。当前有意保持为空实现状态：具体产品形态和开源底座尚未裁决。

## 子目录

| 目录 | 当前用途 |
| --- | --- |
| `src/` | 模板预留源码层；尚无 SportAgent 实现 |
| `configs/` | 未来 spike 与实验配置 |
| `scripts/` | 未来一次性或集成脚本 |
| `tests/` | 未来契约、集成与领域评测测试 |
| `experiments/` | 开源底座 Top 2 的受限 spike 入口 |

## 当前门禁

- 先完成 `human/briefs/active/20260713-open-source-base-selection.md`。
- human 接受底座和首期范围决策前，不创建内部产品框架或引入产品依赖。
- spike 必须围绕具体候选底座，写清接入边界、退出条件和预计替代的自研基础设施。
- 正式代码进入本层时，同 commit 更新 `lab/code/ANATOMY.md` 与相关测试入口。
