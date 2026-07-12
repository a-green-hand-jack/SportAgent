# Session Tree

## Parent objective

将 SportAgent 原地迁移到 agent-native template v1.3.0，并验证产品与 uv 环境。

## Current phase

单 owner 迁移与验证；未派生子 session。

## Children

| id | purpose | branch/worktree | status |
| --- | --- | --- | --- |
| sportagent-template-adoption | 官方 phased adoption、冲突 reconcile、uv 与验证 | `feature/v1` 当前共享 worktree | complete |

## Merge / review order

1. 审核模板框架与 `.template.toml`。
2. 审核 imported SportAgent unit 和冲突留档。
3. 阅读 migration report 与验证证据后，由协调方决定后续 Git/GitHub 动作。

## Global forbidden paths

- `lab/data/**`、`lab/runs/**`、`lab/models/**` bytes
- `checkpoints/**`、`wandb/**`、`lab/infra/private/**`、`.env`

## Open risks

- 产品 ruff 与 mypy 在迁移前已有失败基线；迁移不扩大这部分产品代码质量债。
