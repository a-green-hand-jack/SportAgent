# current-status.md

> 活状态单一真相源。完成阶段、session 边界或关键验证后更新。

## 当前 objective

完成 SportAgent 对 `ml-project-repo-agent-native-template` v1.3.0 的原地采用，并保持产品行为与
uv 锁定环境可复现。

## 当前结构

- Agent-native 控制根：仓库根目录。
- SportAgent 产品单元：`lab/code/imported/SportAgent/`。
- 迁移状态与 proof：`lab/docs/audits/template-adoption/` 和
  `lab/docs/audits/template-adoption-report.md`。
- 原始冲突留档：`human/imported/adoption-conflicts/`。

## Constraints

- 不改写产品知识库、生成数据、评审材料或原 tracked bytes。
- 不 commit、push、reset、clean，不操作 GitHub issue。
- Python 约束保持 3.12；依赖保持现有 `uv.lock`，不使用系统 pip。

## Baseline

- 原 tracked 文件：106 个，内容 hash 已记录。
- `uv sync --frozen`：CPython 3.12.3，64 个包。
- `uv run --frozen pytest`：471 passed，78% coverage。
- 既有质量债：ruff 123 个 findings；mypy 8 个 errors。

## Migration decisions

- 使用模板官方 `adopt-existing-repo.py` 的 discover/baseline/scaffold/normalize/prove 阶段。
- 采用 tag `v1.3.0`、commit `53cbbee6efcf4e0df92f5ed727f84745210b58b8`。
- 产品保持为一个 imported unit，避免改变 `src/`、`data/`、`tests/` 的内部相对路径和行为。
- `.codex/` 与 `.agents/` 由 canonical `.claude/` 能力生成；静态导航/config 从同一 tag 补齐。

## Stop condition

Integrity、adoption smoke、strict governance、uv sync、471 项产品测试、CLI smoke、diff check
均有 fresh evidence；ruff/mypy 与 baseline 相同且无迁移新增错误。

## Final evidence

- `python scripts/check-adoption-integrity.py /home/user/Projects/SportAgent`：106/106 present。
- `python lab/evals/adoption/run-adoption-smoke.py`：OK。
- `python scripts/validate-governance.py --strict`：0 error / 0 warning。
- `python scripts/sync-codex-adapters.py --check`：0 issue。
- `UV_CACHE_DIR=/tmp/uv-cache uv sync --frozen`：CPython 3.12.3，64 packages installed。
- `UV_CACHE_DIR=/tmp/uv-cache uv lock --check`：65 packages resolved，lock valid。
- `UV_CACHE_DIR=/tmp/uv-cache uv run --frozen pytest`：471 passed，78% coverage。
- `UV_CACHE_DIR=/tmp/uv-cache uv run --frozen fitness-agent version`：`v0.1.0`。
- `git diff --check`：通过。
- Ruff 仍为 baseline 的 123 errors；mypy 仍为 baseline 的 8 errors / 3 files。

迁移已达到 stop condition；剩余工作仅是协调方审阅、Git 记录与 issue #11 tracker 更新。
