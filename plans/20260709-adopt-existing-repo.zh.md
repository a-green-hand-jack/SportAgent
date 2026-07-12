# adopt-existing-repo 迁移能力计划

> 目标：新增一个可分步、可验证、尽量无人值守的迁移能力，把一个已经存在的 repo
> 收敛成 `ml-project-repo-agent-native-template` 的完整形态，而不是只叠加少量文件。

## 当前目标

在 `worktree-adopt-existing-repo` 分支实现一个 template-converger：

- 输入：一个已有 Git repo 路径。
- 输出：该 repo 在迁移分支/worktree 中逐步变成 template 形态。
- 约束：每一步都有可运行检查，证明没有破坏原 repo 的文件、测试和重要产物。
- 交互：默认不需要 human 逐项参与；遇到无法安全判断的问题时，工具应停下并写明报告，而不是猜。

## 非目标

- 不在第一版自动删除任何原 repo 文件。
- 不编辑或搬动大 bytes：数据、run 产物、模型、checkpoint、`wandb/`、`.env` 只登记或保留原位。
- 不自动 push、开 PR、merge、release。
- 不自动修复所有语言/框架的构建系统；只做保守的路径移动、入口更新和验证报告。
- 不把 ELF case 写死为实现依赖；ELF 只作为真实 replay/stress case。

## Branch / worktree

- base branch：`main`
- implementation branch：`worktree-adopt-existing-repo`
- worktree path：`.claude/worktrees/adopt-existing-repo`

## Linked issue / PR

- 暂无 GitHub issue / PR。
- 本 plan doc 是当前 feature 的可追踪锚点。

## Allowed paths

第一版预计修改：

- `.claude/skills/adopt-existing-repo/SKILL.md`
- `.claude/commands/adopt-existing-repo.md`
- `scripts/adopt-existing-repo.py`
- `scripts/check-adoption-integrity.py`
- `tests/` 或 `lab/evals/` 下的 synthetic existing repo fixtures / tests
- `plans/20260709-adopt-existing-repo.zh.md`
- `README.md`
- `DESIGN.md`
- `ANATOMY.md`
- `scripts/ANATOMY.md`
- `.claude/ANATOMY.md`
- `memory/current-status.md`
- `memory/session-tree.md`

如实现中新增测试目录或 adoption ledger，需要同步更新对应 `ANATOMY.md`。

## Forbidden paths

- 禁止编辑或删除 `lab/data/**`、`lab/runs/**`、`lab/models/**` bytes、`checkpoints/**`、`wandb/**`、`lab/infra/private/**`、`.env`。
- 禁止改远端基础设施、push 到 `main/master`、开 PR、merge、release。
- 禁止在目标 existing repo 中直接原地破坏性迁移；工具默认应创建迁移分支/worktree或 dry-run 报告。

## 任务树

- [x] Phase 0：锁定 contract 与 plan
- [x] Phase 1：实现 discover/baseline 数据模型
- [x] Phase 2：实现 scaffold，把 template control plane 安全写入目标 repo
- [x] Phase 3：实现 normalize，把已有 repo 收敛到 template layout
- [x] Phase 4：实现 prove，跑原生测试、template validator、manifest integrity
- [x] Phase 5：加入 synthetic fixtures 与回归测试
- [x] Phase 6：文档、ANATOMY、DESIGN、README 同步
- [x] Phase 7：用 ELF branch 或另一个真实 repo 做 replay/stress smoke

## Human 批注区

（human 可在这里直接改 plan；agent 读取 diff 后收敛。）

## 当前决策

- 功能形态叫 `adopt-existing-repo`，但内部心智模型是 template-converger。
- 默认策略是 conservative：不删除、不覆盖、不可判断即停下并报告。
- 支持分 phase 执行，也支持 `--all --policy conservative` 无人值守模式。
- 每一步都写 machine-readable state，便于中断后 resume。
- 自动化优先级：保护原 repo > 完整收敛 > 美观重排。

## 未解决问题

- 第一版已决定不 rewrite 代码路径；把原 repo root 保守移动到 `lab/code/imported/<slug>/`，
  原测试在 imported root 内运行。
- Synthetic fixture 当前由 `lab/evals/adoption/run-adoption-smoke.py` 动态生成，不落静态 fixture。
- Adoption report 当前由脚本内置生成；未来如果需要 human 可编辑模板，再提升到 `.agent/templates/`。
- 是否把迁移工具做成可在 template repo 外部运行的 standalone script。
- Phase 7 已选择 AgentR1/Agent-R1（agent-RL / ML-research repo）做真实 replay；
  结果见 `lab/docs/audits/agent-r1-adoption-replay-report.md`。

## 验证标准

第一版完成时至少满足：

- `python scripts/adopt-existing-repo.py <fixture> --phase discover` 可生成 plan。
- `python scripts/adopt-existing-repo.py <fixture> --phase baseline` 可生成 hash/protected/test 基线。
- `python scripts/adopt-existing-repo.py <fixture> --phase scaffold` 可写入完整 control plane，且不覆盖冲突文件。
- `python scripts/adopt-existing-repo.py <fixture> --phase normalize` 可把 synthetic repo 根目录收敛到 template 白名单。
- `python scripts/adopt-existing-repo.py <fixture> --phase prove` 可生成 adoption report。
- `python scripts/check-adoption-integrity.py <fixture>` 可证明未发生未授权删除/改写。
- 本模板自身 `python scripts/validate-governance.py --strict` 通过。
- `git diff --check` 通过。

## 下一步

1. 设计 `lab/docs/audits/template-adoption/state/` schema：plan、baseline manifest、phase log、report。
2. 实现 `scripts/adopt-existing-repo.py` 的 dry-run discover。
3. 为 discover 添加最小 synthetic fixture 测试。
4. 再推进 scaffold/normalize/prove，而不是一口气写完。

## Plan revision log

- 2026-07-09 初稿：根据 human 对“完全转成 template 形式、分步迁移、每步测试、不依赖 human”的要求整理。
- 2026-07-09 v1 实现：新增 phased CLI、integrity checker、skill/command、synthetic smoke eval 与文档索引。
- 2026-07-09 Agent-R1 replay：真实 repo adoption 全阶段通过，并登记报告/ledger。
