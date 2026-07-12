# 参考文档覆盖说明

> 这份小文档回答一个问题：当前 `ml-project-repo-agent-native-template` 是否覆盖了
> `.reference-docs/` 里的设计安排？结论是：**覆盖核心安排，并在治理、验证、压力测试层面形成工程化超集；
> 但不是逐字实现每一个示例、TODO 或旧 `.harness` 世代机制。**

## 覆盖结论

当前实现以两份参考文档为设计来源：

- `claude_code_optimization_spirit_zh.md`：心智模型与不可协商原则。
- `claude_code_practice_for_ai_phd_zh.md`：repo-local control plane、subagent/skill/hook/permission、实验与论文工作流。

核心安排均已落地：

| 参考安排 | 当前实现 | 验证/证据 |
| --- | --- | --- |
| repo 是控制面，chat 只是短期意识流 | `AGENTS.md`、`.agent/`、`memory/`、`human/`、`lab/`、`deliverables/` 分层 | `DESIGN.md`、root `ANATOMY.md`、`scripts/check-agent-harness.py` |
| repo-local 能力，不装 user 全局 | `.claude/agents/`、`.claude/skills/`、`.claude/commands/`、`.claude/hooks/` | `check-agent-harness.py` 校验 frontmatter / settings / hooks |
| ANATOMY 防漂移 | root 与目录级 `ANATOMY.md`、`.agent/anatomy-protocol.md` | `check-anatomy-drift.py`、`check-same-commit.py`、CI |
| main agent / subagent 分工 | 16 个 subagent，分执行/协调/维护交互/演化四层 | ELF case round 1-4 压力测试；`stress-test-ledger.yaml` |
| context / session / handoff 纪律 | `memory/current-status.md`、`session-tree.md`、templates、PreCompact hook | 本轮已补齐 main 活状态；`pre_compact_memory_check.py` |
| 多 agent / worktree 流程 | `worktree-pr-flow` skill、`feature-worker`、branch/worktree 状态模板 | ELF case F19 后已加写操作前 cwd 自查 mitigation |
| 研究事实证据链 | `lab/research/{claims,evidence,experiment-ledger,release-gates,regression-matrix}.yaml` | `validate-governance.py` 校验证据链、release gates、regression matrix |
| artifact / data / model 索引 | `lab/artifacts/*.yaml`、`lab/data/`、`lab/models/checkpoint-index.yaml` | `.agent/artifact-policy.md`、`artifact-indexing` skill、gitignore/tracked-bytes 检查 |
| paper reproduction | `/paper-reproduce` command + `experiment-workflow` skill | ELF case round 3：静态审阅通过；无 synthetic paper 目标时不伪造 live test |
| paper writing 最小边界 | `deliverables/paper/README.md` writing contract、`deliverables/index.md` no-overclaim 索引 | reference 文档本身把完整写作流标为 TODO；当前实现覆盖最小契约与 human gate |
| permissions / hooks | `.claude/settings.json` + parser-based `pre_tool_guard.py` + advisory hooks | ELF case hook/permission 探针；`validate-governance.py --strict` |
| model / effort 是预算 | `.agent/model-routing-policy.md`、`subagent-routing` skill | `zh-review-gate` 是 human 批准的廉价模型窄例外 |
| workflow recipe 可复测 | `lab/recipes/claude-code/`、`lab/evals/cc-workflow/`、`workflow-recipe-harvesting` | F17 漂移已修复，补齐 recipe/eval 对应关系 |
| 定期维护 | `/weekly-maintenance` command、`.agent/checklists/weekly-maintenance.md` | round 3 command 覆盖记录 |

## 工程化超出参考文档的部分

当前模板比参考文档多了几类可运行机制：

- `scripts/check-same-commit.py`：结构改动与 ANATOMY 同变更集门禁。
- `scripts/validate-governance.py`：聚合 harness / anatomy / evidence / release gate / regression matrix / tracked bytes 检查。
- parser-based `pre_tool_guard.py`：比示例式字符串 deny 更精确，降低误伤。
- branch-aware push guard：topic 分支可推，`main/master` 需 `CLAUDE_ALLOW_PUSH_MAIN=1`。
- `zh-review-gate` + `zh_review_advisory.py`：对 human-facing 中文输出做轻量兜底。
- `template-stress-test` skill + `.agent/template-stress-test-policy.md` + `stress-test-ledger.yaml`：把“模板自身也要被真实 case 压测”变成持久能力。
- `DESIGN.md` inventory sync：能力数量由 validator 防漂移，不靠人记。

## 有意不逐字实现的部分

这些不是遗漏，而是 v1 的边界选择：

- 不恢复旧 `.harness` / component activation / reactivation / template mode CLI；新模板改用 `.agent/` +
  `.claude/` + `scripts/`。
- 不把所有 human gate 做成机械 validator；venue、claim、baseline 等判断仍由 human review 和 ADR 承载。
- 不提供语言特定 formatter PostToolUse hook；模板是 ML 研究控制根，派生项目可按栈添加。
- 不把完整 paper writing / LaTeX 协作做成独立 skill；参考文档也标为 TODO，当前只保留 writing contract、
  evidence/no-overclaim 边界与 human gate。
- 不设根目录通用 `docs/`；项目长文按角色落到 `human/`、`lab/docs/`、`deliverables/`、`.agent/`。

## 测试覆盖状态

截至 2026-07-09：

- validators：4 个 validator 均有正常路径与对抗性探针记录；release-gates/regression-matrix 覆盖缺口已修。
- hooks/permissions：危险命令、受保护路径、push guard、嵌套 vendored repo cwd 漂移均被 ELF case 覆盖；F2/F11 已修并做 round 4 复验。
- skills：9 个 project-local skill 均至少有调用或流程级覆盖；`template-stress-test` 是最新新增项，已在落地 commit 中做一次真实调用 smoke。
- commands：7 个 slash command 已覆盖；`paper-reproduce` 因缺少干净 synthetic paper 目标只做静态审阅，这是有意避免伪造测试对象。
- subagents：核心 subagent 行为已通过 ELF case 大量真实派发覆盖；`feature-worker` 与 `sub-agent-maker-agent` 的历史“未测”记录已在后续 round/ledger 中闭环或降级为“无需新 draft”。

后续不需要为了 v1 继续做无目标的全量压测；应按 `.agent/template-stress-test-policy.md`，在新增/修改
validator、hook、权限面、结构面或能力面时触发对应深度测试。
