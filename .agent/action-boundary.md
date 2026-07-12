# 动作边界

三档：**禁止 / 需问 / 可做**。这是 doctrine 层的解释；机器强制在 `.claude/settings.json`、`.codex/config.toml` / `.codex/rules/` 与共享 hooks，漂移检查在 `scripts/`。三者必须对齐。

> 设计：把"绝对红线"钉进 hook 地板（不可调，bypass/自主窗口也拦得住），只把"有人在就确认"留在 `ask`（可调）。于是放宽 permission 才安全——致命动作不在可放宽的那层。详见 `autonomous-window.md`。

## 禁止（hook 地板 + deny，bypass 也拦）

- 编辑/删除数据与产物 bytes：`lab/data/**`、`lab/runs/**`、`lab/models/**` 权重、`checkpoints/**`、`wandb/**`、`lab/infra/private/**`、`.env`。
- 递归删除（`rm -r`）受保护数据/产物、`.git`、绝对路径(非 `/tmp`)、`~`、仓库根、`..`；`mv`/`cp` 触碰受保护路径。（缓存/构建/临时目录可删——见"可做"。）
- 提权与远程执行：`sudo`、`curl|sh`、`wget|sh`。
- `pip install`（含 `python -m pip install`）：用 `uv add`。
- push 到 `main`/`master`：除非命令带 `CLAUDE_ALLOW_PUSH_MAIN=1` 或 `CODEX_ALLOW_PUSH_MAIN=1`（human 单次放行）。
- 派发无边界的 `general-purpose` 大 agent。

## 需问（ask，先说明意图与影响，等确认）

- 有损/改历史 git：`git checkout`、`git switch`、`git reset`、`git clean`、`git rebase`、`git merge`、`git branch -d/-D`、`git worktree remove`。
- 依赖变更：`uv add`、`uv sync`、`uv remove`。
- 计算副作用：`kill`、`sbatch`、`runai`、启动/重启训练。
- 协作副作用：`gh pr create`、`gh pr merge`、release、改远端基础设施。
- 促销结果：把普通结果 promote 成 paper claim。

## 可做（allow，read-only 或低风险 —— 不打断）

- 只读 shell：`ls`/`cat`/`head`/`tail`/`find`/`grep`/`rg`/`wc`/`jq`/`stat`/`tree`/`diff` 等。
- 只读 git：`status`/`diff`/`log`/`show`/`branch`(列)/`remote -v`/`rev-parse`/`ls-files`/`blame`/`fetch` 等。
- 低风险 git（可逆）：`git add`、`git commit`、`git stash`、`git push` 到 **topic/实验分支**（非 `main`/`master`）。
- 开发：`pytest`/`ruff`/`mypy`/`pyright`、`uv run *`、`python -c`/`python -m pytest|ruff|mypy`、`mkdir`/`touch`。
- 清理：`rm -rf` 缓存/构建目录（`__pycache__`/`.pytest_cache`/`.ruff_cache`/`.mypy_cache`/`build`/`dist`）。
- 文件编辑：`Edit`/`Write`（受保护路径除外，被 deny + hook 挡）。
- 跑 repo validator：`python scripts/*.py`。

## 副作用半径原则

选择动作时按「错了会怎样」判断：浪费 GPU、污染数据、误导论文、影响导师/合作者可见材料 —— 半径越大越要走 `human-gates.md`。checkpoint / data / remote 至少四层保护：permissions + hook + validator + artifact index。
