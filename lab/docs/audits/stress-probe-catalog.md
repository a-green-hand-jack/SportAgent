# 压力测试探针目录（本模板版本，2026-07-09）

参考旧 `.harness` 世代的 `research-template-case-harness-test` skill 附带的
`stress-probe-catalog.md`（原路径：
`~/Projects/ELF-template-case/.harness/skills/skills/research-template-case-harness-test/references/stress-probe-catalog.md`），
逐行判断是否适用于本模板，并记录 round 3 实际跑过的探针结果。按 human 的要求：**不适用的行也显式保留，
标 N/A + 原因，不静默丢弃**。

沿用旧目录的报告格式：`Mutation / Expected / Commands / Actual / Classification / Follow-up`。
Classification 取值沿用旧惯例：upstream harness gap（本模板：template gap）| generated template
gap（本模板：case ledger 债务）| documentation friction | accepted regression fixture | **validator
按预期工作**（新增，因为本模板大部分探针结果是"验证器正确拦截"，不是发现 gap）。

## 旧目录 15 行 → 本模板映射总表

| 旧 probe（stress-probe-catalog.md） | 本模板对应 | 状态 |
| --- | --- | --- |
| Template mode | `.harness/manifest.yaml` 的 complete/partial 概念 | **N/A** — 本模板没有"模式"这个机制 |
| Component activation | 标记 code/paper/reference 为 inactive | **N/A** — 本模板没有组件激活脚本 |
| Missing component file | 删除必需 scaffold 文件 | → P1-1（`check-agent-harness.py` 的导航四件套检查） |
| Evidence link drift | claim 指向缺失 evidence | → P0-2 / P0-3 |
| Evidence provenance | evidence 无 provenance/visibility | → P0-1 / P0-4（本模板没有独立 provenance 字段，落进 overclaim 检查） |
| Source visibility | 私有源用在 paper-facing claim | **降级为纯文档，非 validator 对象**——见 round 1 迁移决策（`lab/docs/reference/provenance.md`），不需要新探针 |
| Experiment closure | 实验标 complete 但缺 commit/config/metric/artifact | → 概念对应 `lab/research/experiment-ledger.yaml` 字段完整性；本模板**没有 validator 强制检查**这一条，靠 `experiment-orchestrator`/`experiment-workflow` skill 的纪律（见下方 P3 补充发现：round 2 里这条纪律实际执行时就漏了 experiment card / run summary 两项） |
| Artifact index | 产物无 index 条目 | → 概念对应 `lab/artifacts/*-index.yaml`；同样**没有 validator 强制**，靠 `artifact-librarian` 纪律（软约束，非 bug） |
| Paper claim drift | paper-facing claim 未登记进 claims.yaml | → 部分对应 P0 系列（overclaim 检查），但本模板没有"论文段落 vs claims.yaml"的交叉检查，是纯人工纪律 |
| Generated/private leakage | 受保护路径 bytes 进 Git | → P0-5（.gitignore 缺 token）/ P0-6（tracked bytes 检查） |
| Human gate bypass | 改 venue/claim/baseline 无 gate 记录 | **N/A（人工判断面）**——`.agent/human-gates.md` 是 doctrine，本模板没有把它做成 validator；这是刻意的设计（人类决策不该被机器规则代替），不是 gap |
| Anatomy drift | 移动目录不更新 ANATOMY | → P1-2（`check-anatomy-drift.py`）/ P1-3（`check-same-commit.py`） |
| Skill routing | 跨组件工作没读必需入口 | 部分对应 round 2 的 `subagent-router-agent` 测试；没有独立 validator，纪律面 |
| Reapplication safety | 组件重新激活覆盖已编辑文件无 `--force` | **N/A** — 本模板没有组件激活脚本 |
| Branch CD boundary | push 模板改动到非模板分支却期望同步 | **N/A** — 旧方法论讲的是 harness 自身对下游模板仓库的同步机制，本模板没有这类下游同步 CD |

## Round 3 P0：evidence-chain 对抗性探针（`scripts/validate-governance.py` 的 `check_evidence_chain`）

### P0-1

Mutation：
- `lab/research/claims.yaml`：新增一条 `status: partial`、`evidence: []` 的 claim。

Expected：
- `validate-governance.py` 报 `overclaim：claim ... status=partial 但无 evidence 支撑`。

Commands：
```bash
python scripts/validate-governance.py
```

Actual：
- `ERROR overclaim：claim probe-p0-1-no-evidence status=partial 但无 evidence 支撑` —— 与预期一致。

Classification：validator 按预期工作。

Follow-up：无（已 revert，未保留）。

### P0-2

Mutation：
- 某 claim 的 `evidence:` 列表包含一个不存在的 id（`ev-does-not-exist-xyz`）。

Expected：
- 报 `claim ... 引用未知 evidence：...`。

Commands：同上。

Actual：
- `ERROR claim probe-p0-2-unknown-evidence-ref 引用未知 evidence：ev-does-not-exist-xyz` —— 一致。

Classification：validator 按预期工作。Follow-up：无。

### P0-3

Mutation：
- 一条 evidence 的 `supports_claim` 指向不存在的 claim id。

Expected：
- 报 `evidence ... 的 supports_claim 指向未知 claim：...`。

Actual：
- `ERROR evidence ev-probe-p0-3-orphan 的 supports_claim 指向未知 claim：claim-does-not-exist-xyz` —— 一致。

Classification：validator 按预期工作。Follow-up：无。

### P0-4

Mutation：
- 一条 claim `verified_by_fresh_reviewer: true`，但挂接的 evidence 只有 `grade: log`（不是 `paper-claim`）。

Expected：
- 报 overclaim：缺少经 fresh reviewer 的 paper-claim 级证据。

Actual：
- `ERROR overclaim：claim probe-p0-4-fresh-reviewer-no-paper-evidence 标记 paper-grade（fresh reviewer）但缺少经 fresh reviewer 的 paper-claim 级证据` —— 一致。这是四条 overclaim 分支里唯一涉及 paper-grade 的一条，此前从未测过。

Classification：validator 按预期工作。Follow-up：无。

### P0-5

Mutation：
- 从根 `.gitignore` 删除 `wandb/` 这一行。

Expected：
- 报 `.gitignore 未提及受保护路径：wandb`。

Actual：
- 一致；revert 后 `git diff` 确认恢复干净。

Classification：validator 按预期工作。Follow-up：无。

### P0-6

Mutation：
- `touch foo.ckpt && git add -f foo.ckpt`（绕过 gitignore 强行 stage 一个假 checkpoint 文件）。

Expected：
- 报 `权重 bytes 被误加进 Git：foo.ckpt`。

Actual：
- 一致：`ERROR 权重 bytes 被误加进 Git：foo.ckpt`。`git reset` + 删除文件后确认恢复干净。

Classification：validator 按预期工作。

Follow-up：**原计划还想测 `lab/runs/dummy.bin` 这个 `bad_prefixes` 分支（对应 `lab/runs/` 前缀检查），但 `mkdir lab/runs/__probe__ && touch .../dummy.bin` 这条命令被 permission 层直接拒绝了**（"Permission to use Bash with command ... has been denied"，不是 validator 或 hook 报的错，是权限层本身拒绝了这次组合命令）。这本身是一条真实观察：即使是无害的空探针文件，往 `lab/runs/` 这类受保护目录里写东西也会在权限层被拦，比预期的"只有 validator 会报错"更早一步、更严格地挡下来——算是一个正面发现（纵深防御），但也意味着 `bad_prefixes` 分支本身没有被这次探针直接验证到（只验证了 `bad_suffixes` 分支）。

## Round 3 P1：其余 3 个 validator 的对抗性探针

### P1-1（`check-agent-harness.py`）

Mutation A：临时删除 `lab/code/AGENTS.md`。
Mutation B：在仓库根新增一个不在白名单里的文件 `__probe_root_pollution__.txt`。

Expected：A → `缺少导航文件：lab/code/AGENTS.md`；B → `根目录疑似污染` warning。

Actual：两条同时命中，`FAIL — 1 error(s), 1 warning(s)`，文案与预期一致。Revert 后确认干净。

Classification：validator 按预期工作。Follow-up：无。

### P1-2（`check-anatomy-drift.py`）

Mutation A：`lab/code/ANATOMY.md` 的 `related_files` 加一条指向不存在文件的引用。
Mutation B：把同一份 `ANATOMY.md` 撑到 153 行（超过 120 行硬上限）。

Expected：A → `related_files 引用不存在 -> ...`；B → `超过硬上限 120 行`。

Actual：两条分开测试，均与预期一致（`FAIL — ... 1 处漂移`，各自文案匹配）。Revert 后确认干净。

Classification：validator 按预期工作。Follow-up：无。

### P1-3（`check-same-commit.py --staged`）

Mutation：在 `lab/code/` 下新增一个文件并 `git add`，但不在同一变更集里更新 `lab/code/ANATOMY.md`。

Expected：`FAIL`，报"改了...但同变更集未更新..."。

Actual：一致。`git reset` + 删除文件后确认恢复干净。

Classification：validator 按预期工作。Follow-up：无。

### P1-4（investigation，非 mutation）

问题：`lab/research/ANATOMY.md` 把 `release-gates.yaml`/`regression-matrix.yaml` 描述为"汇总
claims + regression-matrix，产出可否交付的判定"的关键面，但读完 `scripts/validate-governance.py`
全文、并对整个仓库 `grep -rn "release-gates\|regression-matrix"`，**没有找到任何脚本引用或校验
这两个文件**。

Classification：**case ledger 债务 / 潜在 template gap**（未定论）——不确定这是刻意的"人工判断面，
不该被机器强制"设计，还是一个真实的 validator 覆盖缺口。只记录，不擅自修，留给 human 或后续
`DECISIONS.md` 判断。

Follow-up：待 human 决定是否值得给这两个文件加校验（比如 release-gates.yaml 引用的 claim id 是否
都存在、regression-matrix 的指标名是否和 evidence.yaml 一致），还是明确记一条决策说"这是人工判断面"。

## Round 3 P3：skill 声明流程 vs. 实际执行的一致性检查（非 mutation 探针，是文档-实践一致性核查）

- **`experiment-workflow` skill 声明的完整产出**（experiment card + ledger 条目 + run summary +
  达标后进 evidence）**在 round 2 实际执行时只落地了 ledger 条目和 evidence 条目**（由
  `experiment-orchestrator` subagent 完成，不是通过这个 skill 被显式调用的）——`run-elf-pytorch-runtime-smoke-replay-claude`
  没有对应的 experiment card 文件，也没有 run summary 文件。
  Classification：documentation friction / 纪律执行缺口。Follow-up：不追溯补齐（这是一次真实的
  round 2 执行留下的既成状态，事后补写意义不大），但值得在下一次真正跑实验时注意这条 skill 的
  完整步骤没有被自动强制，容易漏。
- **`artifact-indexing` skill 文档里描述的字段名**（`path`/`inspect`/`commit-config-run`/
  `dependency`）**与 `lab/artifacts/*-index.yaml` 实际使用的字段名**（`storage_path`/
  `how_to_inspect`/分开的 `commit`+`config`+`run_id`/`supports`）**不一致**——纯文档措辞漂移，
  不影响 validator（validator 不校验字段名语义，只校验 YAML 能 parse），但会让照着 skill 文档
  去写新条目的人短暂困惑。
  Classification：documentation friction。Follow-up：待 human 决定是否修 SKILL.md 措辞对齐实际
  schema（本轮不擅自改）。
- **`workflow-recipe-harvesting` skill 声明的第 3-4 步**（"绑复测：`lab/evals/cc-workflow/<id>.yaml`
  写 1-3 个小任务" + "跑复测，报告落 `lab/reports/cc-workflow/`"）**在 round 2 实际执行时完全没有
  发生**——两条 candidate recipe 只写了 `lab/recipes/claude-code/<id>.yaml` 本身，`lab/evals/cc-workflow/`
  和 `lab/reports/cc-workflow/` 里都只有 README/EXAMPLE，没有真实条目。追查原因：**`workflow-recipe-harvester`
  subagent 自己的 `.claude/agents/workflow-recipe-harvester.md` 定义里的"输出格式"根本没提"绑复测任务"
  这一项**——SKILL.md 和对应 subagent 的 `.md` 契约之间不一致，subagent 只是老实按自己的契约做了它
  声明会做的事，没有做 SKILL.md 多要求的那一步。
  Classification：documentation friction（skill-vs-subagent 契约漂移）。Follow-up：待 human 决定是
  否要让 `workflow-recipe-harvester.md` 的契约吸收 SKILL.md 的"绑复测"步骤，还是反过来简化 SKILL.md。
- **`worktree-pr-flow`**：本轮的 Track 1 修复（隔离 worktree → 实现 → 跑 validator → PR → human
  gate）走的就是这个 skill 声明的流程；但 Track 1 本身在本报告写作时仍被 auto-mode classifier
  拦下、等待 human 二次明确确认，尚未跑完，所以这一条暂时**部分验证**（步骤 1-3 的流程设计已经在
  round 1/2 里反复验证过是安全、正确的模式，步骤 6-7 的 PR/review/merge/归档部分待 Track 1 真正
  跑完后补充确认）。

## 未采纳/未测部分（诚实记录，不做完整性的静默声明）

- `lab/runs/` 前缀的 tracked-bytes 探针（P0-6 的 `bad_prefixes` 分支）被权限层拦下，未直接验证到。
- P1-4 是记录性发现，不是已解决问题。
- P2（slash command）与 skill 的其余部分详情见 `memory/current-status.md` 的 Commands+results 表，
  本文件只收录 P0/P1/P3 的对抗性/一致性探针，不重复贴 P2 内容。
