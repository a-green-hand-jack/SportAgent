---
title: "Claude Code 实践手册"
category: "research-writing"
tags:
  - claude-code
  - research-workflow
  - repo-control
  - anatomy
status: "imported"
source: "github-gist"
---
# Claude Code 实践手册

面向 AI PhD Student 的日常工作流、模板和操作纪律

版本：2026-07-05  
状态：gist 草稿  
配套理念文档：`claude_code_optimization_spirit_zh.md`

---

## 0. 使用前提

本文假设你主要用 Claude Code 做：

- ML / AI research repo 阅读和修改。
- paper reproduction。
- baseline / ablation / training loop 实验。
- logs、metrics、checkpoints、W&B / MLflow 结果整理。
- paper / rebuttal / LaTeX 写作。
- 多 repo、多 worktree、多 session 协同。

本文明确不把 `claude -p` 作为常规路径。官方 CLI docs 支持 non-interactive mode，但本 workflow 按当前预算约束排除它，避免把常规 Claude Code plan 工作流变成 API token / usage credit 消耗。

---

## 1. Repo-local control plane

这份手册的默认立场是：Claude Code 的项目策略应尽量落在 repo 内，而不是安装在 user home 下。

原因很简单：repo 是 agent 最直接、最稳定、最可审计的上下文。项目相关的 subagent、skill、command、hook、permission、memory policy、实验 ledger 和结构地图，最好都能被 repo 版本控制、被下一个 fresh session 读取、被 CI 或脚本验证、被 PR review 修改。

### 1.1 参考 repo 的共同形状

从 `pairwise-diffusion`、`DOLoop` 和 LingTai anatomy 方法论抽象出来，更推荐这样的研究 repo 控制面：

```text
repo/
  README.md
  PROJECT.md
  DECISIONS.md
  AGENTS.md
  CLAUDE.md
  ANATOMY.md
  human/
    README.md
    AGENTS.md
    CLAUDE.md
    ANATOMY.md
    briefs/
      active/
      completed/
    reviews/
      plans/
      results/
      recipes/
    decisions/
    inbox/
  .github/
    CODEOWNERS
    pull_request_template.md
    workflows/
  .agent/
    AGENTS.md
    principles.md
    session-protocol.md
    behavior-contract.md
    action-boundary.md
    context-memory-policy.md
    tool-skill-interface.md
    human-gates.md
    checklists/
    templates/
  .claude/
    README.md
    AGENTS.md
    CLAUDE.md
    ANATOMY.md
    agents/
    skills/
    commands/
    hooks/
    rules/
    settings.json
  lab/
    README.md
    AGENTS.md
    CLAUDE.md
    ANATOMY.md
    code/
      README.md
      AGENTS.md
      CLAUDE.md
      ANATOMY.md
      src/
        README.md
        AGENTS.md
        CLAUDE.md
        ANATOMY.md
      configs/
      scripts/
      tests/
      experiments/
    infra/
      README.md
      AGENTS.md
      CLAUDE.md
      ANATOMY.md
      permissions/
      paths/
      storage/
      launch/
      probes/
      private/
    research/
      claims.yaml
      evidence.yaml
      experiment-ledger.yaml
      regression-matrix.yaml
      release-gates.yaml
    data/
      manifests/
      checksums/
      task-sets/
      schemas/
    artifacts/
      result-index.yaml
      model-index.yaml
      trace-index.yaml
    runs/
  memory/
    README.md
    AGENTS.md
    CLAUDE.md
    ANATOMY.md
    current-status.md
    phase-dashboard.yaml
    change-control.yaml
    current-practices.md
    deprecated-practices.md
    gc/
  deliverables/
    README.md
    AGENTS.md
    CLAUDE.md
    ANATOMY.md
    paper/
    slides/
    release/
  scripts/
    README.md
    AGENTS.md
    CLAUDE.md
    ANATOMY.md
    check-agent-harness.py
    check-anatomy-drift.py
    validate-governance.py
```

这不是要求所有 repo 一开始就长成这样。它表达的是分层：

- `AGENTS.md` / `CLAUDE.md`：入口层。Claude Code 官方读 `CLAUDE.md`；如果 repo 已有 `AGENTS.md`，`CLAUDE.md` 可以很薄，只负责导向 `AGENTS.md` / `.agent/`。
- `human/`：human-agent 交互层。任务 brief、plan review、result review、recipe review、轻量决策和批注在这里；它让 human 的可信信息也进入 repo，而不是留在聊天或记忆里。
- `.agent/`：repo-local doctrine。放行为契约、动作边界、上下文/记忆政策、human gates、session protocol。它是“这个 repo 如何允许 agent 工作”的版本化规则。
- `.claude/`：Claude Code 项目能力层。项目专属 subagents、skills、commands、hooks、settings 放这里，而不是塞到 user 全局目录里。
- `ANATOMY.md`：结构地图层。根文件只做路由，复杂目录再放自己的 `ANATOMY.md`；结构 claim 应尽量能指向代码坐标。
- `lab/code/`：实现层。代码、配置、脚本、测试、benchmark、实验执行器在这里。
- `lab/infra/`：运行环境层。依赖、权限、路径、storage、remote target、probe、private overlay 在这里。
- `lab/research/`：研究事实层。claim、hypothesis、evidence、experiment ledger、negative results、regression、release gate 在这里。
- `lab/data/` / `lab/artifacts/` / `lab/runs/`：索引与运行产物层。大数据、checkpoint、日志、模型、输出 bytes 不进 Git；repo 只保留 manifest、checksum、logical path、artifact index、run summary。
- `memory/`：活状态层。当前状态、phase、handoff、change-control、memory GC 在这里；它不是随手堆 notes 的地方。
- `deliverables/`：对外承诺层。paper、slides、release notes 不能超过 `lab/research/evidence.yaml` 支持的证据。
- `scripts/`：门禁层。把“不要漂移”做成可运行检查，而不是只写成愿望。

### 1.1.1 重要目录的四类局部文档

不是每个 leaf directory 都要写文档，但重要目录应该有一个轻量 navigation quartet：

```text
README.md    给 human 的目录说明：这里是什么、什么时候来这里、常见入口。
AGENTS.md    给 agent 的工作规则：允许改什么、禁止改什么、必须验证什么。
CLAUDE.md    给 Claude Code 的薄路由：优先读哪些本目录文件和 repo-local assets。
ANATOMY.md   给 coding agent 的结构地图：组件、调用关系、状态和 line-addressed citations。
```

优先拥有这四类局部文档的目录：

```text
<repo>/
<repo>/human/
<repo>/.agent/
<repo>/.claude/
<repo>/lab/
<repo>/lab/code/
<repo>/lab/code/src/
<repo>/lab/infra/
<repo>/lab/research/
<repo>/lab/artifacts/
<repo>/memory/
<repo>/deliverables/
<repo>/scripts/
```

规则：

- `README.md` 面向 human，不要写成长 spec。
- `AGENTS.md` 面向 agent，写操作边界、验证命令和禁止路径。
- `CLAUDE.md` 面向 Claude Code，应该薄，只做本目录入口和读文件顺序。
- `ANATOMY.md` 面向结构导航，只给有真实协作关系、状态、调用图或 ownership 边界的目录。
- 如果某个目录的 `ANATOMY.md` 写成教程，说明应该拆到 README 或 `.agent/`。
- 如果某个目录只有静态资源或简单 leaf helper，不要为了整齐制造空文档。

### 1.2 单 repo vs 研究项目控制根

对一个普通 ML repo，不要一开始就造超大框架。最小可行结构可以是：

```text
repo/
  AGENTS.md
  CLAUDE.md
  ANATOMY.md
  human/
    briefs/active/
    reviews/
    decisions/
  .claude/
    agents/
    skills/
    commands/
    hooks/
    settings.json
  lab/
    README.md
    AGENTS.md
    CLAUDE.md
    ANATOMY.md
    code/
    infra/
    research/
    artifacts/
    runs/
  memory/
    README.md
    AGENTS.md
    current-status.md
    current-practices.md
  scripts/
    README.md
    AGENTS.md
    validate-governance.py
```

如果一个 project 同时有 code、paper、slides、多个 upstream repos、remote GPU worktrees 和多个实验家族，更像 `pairwise-diffusion`：repo 本身就是研究控制根。此时不要另建一个游离的“总控文件夹”，而应把 repo 变成控制面：

```text
repo/
  PROJECT.md          # 研究对象、当前 family、trunk、remote/worktree 策略
  DECISIONS.md        # 指向 durable decision ledger
  REPO_AUDIT.md       # 阶段性治理目标和审计状态
  ANATOMY.md          # 结构路由
  lab/research/       # claim/evidence/experiment ledgers
  lab/infra/          # remote、路径、storage、launch、permissions
  memory/             # current status、actions、risks、handoffs
  deliverables/       # paper/slides/rebuttal/project-page
  scripts/ops/        # governance and drift gates
```

如果项目本身就是为了开发一个 agent，更像 `DOLoop`：`.agent/` 应成为第一等公民，但要区分两件事。第一，外层 Claude Code development harness：为了让 Claude Code 更好地开发这个 repo。第二，内层 release agent：这个 repo 最后要发布、评估或交付的 agent 本身。不要把外层编辑规则和内层 agent 行为契约混成一个长 prompt；把 release agent 的 behavior contract、action boundary、context policy、tool-skill interface、trace-eval loop、human gates 和 production control plane 放在可验证的 repo-local 文件中。

### 1.3 Repo-local 能力安装原则

Claude Code 的 subagent / skill / command / hook 不应默认装到 user 全局目录。除非它真的是跨所有项目都稳定的个人偏好，否则应该落在 repo 内：

```text
项目相关 agent     → .claude/agents/
项目相关 workflow  → .claude/skills/
项目相关 slash cmd → .claude/commands/
项目相关 hook      → .claude/hooks/ 或 .claude/settings.json
项目行为契约       → .agent/
项目结构地图       → ANATOMY.md + nested ANATOMY.md
项目门禁           → scripts/ + CI
```

落地时也不要靠 human 手动维护散点文件。更好的方式是让 agent 按 repo contract 修改：

```text
read repo-local doctrine
→ propose minimal change
→ update contract / manifest / implementation together
→ run harness validator
→ write evidence / memory update
→ ask for external side-effect approval only when needed
```

### 1.4 防漂移和防膨胀规则

把这些规则写进 `AGENTS.md` / `.agent/` / `ANATOMY.md` / validator：

- 根目录只保留入口和工具必须发现的文件；长文、报告、实验记录不要堆到 root。
- 复杂目录才需要 `ANATOMY.md`；它是结构地图，不是教程。
- 文件移动、目录重构、ownership 变化、状态文件变化、tool routing / prompt routing / workflow 变化，必须同 commit 更新相关 anatomy / ledgers。
- 改结构前先搜索 touched filename 在所有 `ANATOMY.md`、index YAML、ledger 中的引用。
- `lab/runs/`、remote outputs、checkpoints、datasets、logs 默认不进 Git，只写 manifest / index / summary。
- 新能力先登记 contract / manifest，再写实现；没有索引的能力不算正式 surface。
- `scripts/check-agent-harness.py` 或 `scripts/ops/validate-governance.py` 应检查目录、必需文件、引用、禁止路径、权限、实验卡和证据链。
- 外部副作用如 push、PR、merge、release、远端作业、删除远端产物，必须有 human gate。

### 1.5 ANATOMY.md 系统

`ANATOMY.md` 是防止 repo 膨胀、结构漂移和 agent 误判 ownership 的核心系统。它不是 README，不是教程，不是设计长文，而是给 coding agent 使用的结构地图。

它回答的问题是：

```text
这个目录代表什么概念？
哪些文件拥有关键行为？
谁调用谁？
哪些状态会持久化？
结构变化时哪些地图必须同步更新？
```

推荐规则：

- 根 `ANATOMY.md` 只做 router：列出复杂目录及其子 anatomy，不解释全系统。
- 复杂目录才有自己的 `ANATOMY.md`：多个文件协作、跨模块调用、持久状态、生命周期、路由、schema、workflow、权限或 agent 需要独立推理的目录。
- 单文件 trivial helper、空目录、静态资源、没有独立概念边界的 leaf directory 不要写 placeholder anatomy。
- 每个结构性 claim 尽量引用代码坐标：`path/to/file.py:42` 或 `path/to/file.py:42-90`。
- anatomy 目标长度约 80 行，硬上限约 120 行。写不短通常是代码边界不清楚，不是文档应该继续加长。
- 结构改动必须 same-commit 更新相关 anatomy：移动、改名、拆分、合并、删除文件或函数，改变 ownership、调用关系、持久状态 shape、lifecycle、routing、workflow，都算结构改动。
- refactor 前先 grep touched filenames 在所有 `ANATOMY.md`、index YAML、ledger 里的引用。
- drift checker 只能挡住 missing file / out-of-range line；语义是否仍正确还要 agent 打开代码行验证。

标准目录级模板：

```markdown
---
related_files:
  - ../ANATOMY.md
  - src/example/foo.py
maintenance: |
  Structural changes update this file in the same PR.
  Citations must remain repo-relative and line-addressed.
---

# <directory> ANATOMY

## What this is
One paragraph.

## Components
| File | Role |
| --- | --- |
| `foo.py` | Owns X. Entry: `foo.py:42-90`. |

## Connections
Inbound:
- `api.py` calls `foo.build()` at `api.py:55`.

Outbound:
- `foo.py` writes through `storage.py:30-80`.

## Composition
Parent:
Children:

## State
| Path | Written by | Meaning |
| --- | --- | --- |

## Notes
Only gotchas that prevent wrong edits.
```

实践中的信号：

- `pairwise-diffusion` 把根 anatomy、`lab/code/`、`lab/infra/`、`lab/research/`、`lab/docs/` 等分层，并把 `check_anatomy_drift.py` 接入 `validate_governance.py`。
- `DOLoop` 在 `.agent/anatomy-protocol.md` 里把 root router、plane-level anatomy、目录选择规则、citation rule、same-commit rule 和 80/120 行阈值写成 repo doctrine。
- LingTai guide 把 `ANATOMY.md` 视作结构导航协议：agent 用 anatomy 定位 ownership，用 grep 做枚举，用 validator 防 citation rot。

---

## 2. CLAUDE.md 最小模板

`CLAUDE.md` 只放 Claude Code 入口规则，不放长教程。若 repo 已有 `AGENTS.md` 或 `.agent/`，它应该是 thin router，而不是第二套手写 doctrine。

```markdown
# Claude Code Entry

Read these first:

1. `AGENTS.md`
2. `.agent/AGENTS.md` if present
3. `memory/current-status.md` if present
4. root `ANATOMY.md` before structural code exploration

This repo treats project-specific Claude Code assets as repo-local:

- `.claude/agents/`
- `.claude/skills/`
- `.claude/commands/`
- `.claude/hooks/`
- `.claude/settings.json`

Do not use user-global agents/skills/hooks for repo-specific behavior unless
the user explicitly asks.

Safety:
- Never edit or delete `lab/data/`, `lab/runs/`, checkpoints, remote outputs, or private overlays unless explicitly asked.
- Never launch, kill, or restart long-running experiments without explicit instruction.
- Do not add dependencies unless required and justified.
- Do not push, open PRs, merge, release, or mutate remote infrastructure without explicit human approval.

Verification:
- Prefer the repo validator first if it exists, for example `python scripts/check-agent-harness.py` or `python scripts/ops/validate-governance.py`.
- Run targeted tests for touched behavior.
- Report exact commands and outputs.
- Do not claim an experiment result without a run id, config, commit, artifact path, and metric source.
```

如果 `CLAUDE.md` 超过 80-120 行，通常已经错了。拆法：

```text
Claude Code 入口       → CLAUDE.md
跨 agent 项目规则      → AGENTS.md / .agent/
结构地图               → ANATOMY.md
Claude Code subagents  → .claude/agents/
Claude Code workflows  → .claude/skills/
Claude Code commands   → .claude/commands/
Claude Code hooks      → .claude/hooks/ + .claude/settings.json
当前状态               → memory/current-status.md
实验事实               → lab/research/ + lab/artifacts/
```

---

## 3. 推荐的 subagent 体系

不一定马上创建所有配置，但实践上不应再只按“五类 worker”理解 subagent。更合理的分层是：

```text
执行层：repo-researcher / feature-worker / test-runner / experiment-monitor / checkpoint-writer
协调层：experiment-orchestrator / subagent-router-agent
维护交互层：session-boundary-agent / branch-reporter / artifact-librarian / interactive-plan-writer / repo-doc-steward
演化层：sub-agent-maker-agent / hook-maker-agent / workflow-recipe-harvester
```

项目相关 subagent 定义应放在 `.claude/agents/`，并由 repo contract 管理；不要默认安装到 user 全局 agents。

下面的 3.1-3.5 是执行层的最小五件套。

### 3.1 repo-researcher

用途：只读代码探索。

边界：

- 只读。
- 优先 grep/glob/symbol search。
- 不读完整大文件。
- 输出文件、符号、证据、假设。

Prompt：

```text
Use a read-only codebase research agent.
Find the minimal files and symbols related to <topic>.
Do not edit files.
Do not paste long code blocks.
Return:
1. relevant files
2. relevant functions/classes
3. evidence
4. hypotheses
5. next probes
```

### 3.2 feature-worker

用途：实现单个清晰功能或 bugfix。

边界：

- 一个 worker 一个任务。
- 同 repo 并行时用 worktree。
- 必须有文件所有权。
- 必须跑 targeted verification。

Prompt：

```text
Use an implementation worker in an isolated worktree.
Task: <specific task>.
Owned files/modules: <paths>.
Do not touch: <paths>.
Before editing, inspect existing patterns.
After editing, run targeted tests.
Write detailed notes to .claude/agent-reports/<task>.md.
Return only files changed, tests run, risks, and merge notes.
```

### 3.3 test-runner

用途：跑定向测试并总结失败。

边界：

- 只跑指定命令。
- 不擅自全量测试。
- 不贴完整日志。
- 输出失败测试、关键错误、下一步 debug probe。

Prompt：

```text
Use a targeted test runner.
Run exactly:
<command>
Summarize pass/fail, failing tests, top error messages, and likely next debugging step.
Do not paste full logs.
```

### 3.4 experiment-monitor

用途：只读监控长实验。

边界：

- 只读。
- 不 kill、不 restart、不改 config、不删 checkpoint。
- 只看 bounded logs、status files、metrics。

Prompt：

```text
Use an experiment monitor.
Read only:
- <log path>
- <run dir>
- <wandb/mlflow run id if available>
Check last 200 log lines, latest metrics, checkpoint freshness, GPU/process status if relevant.
Report anomalies only: crash, NaN, OOM, stall, missing checkpoint, config mismatch.
Do not modify anything.
```

### 3.5 checkpoint-writer

用途：compact、clear、handoff、结束 session 前落盘状态。

Prompt：

```text
Update memory/current-status.md before compact/clear/handoff.
Do not modify source code.
Include:
- current objective
- constraints
- files inspected
- files modified
- decisions made
- commands/tests run
- subagent reports
- open issues
- exact next steps
- do-not-forget notes
```

### 3.6 独立打包，而不是只写在文档里

这些 subagent 不应该只是本手册里的章节。它们应该作为 repo-local assets 进入 `.claude/agents/`，并和 hooks / skills 一起打包、review、迭代。

本 gist 附带一个 draft package：

```text
claude_code_repo_local_pack.tar.gz.b64
claude_code_repo_local_pack.sha256
claude_code_repo_local_pack_index.md
```

包内包括：

```text
.claude/agents/repo-researcher.md
.claude/agents/feature-worker.md
.claude/agents/test-runner.md
.claude/agents/experiment-monitor.md
.claude/agents/checkpoint-writer.md
.claude/agents/experiment-orchestrator.md
.claude/agents/subagent-router-agent.md
.claude/agents/session-boundary-agent.md
.claude/agents/branch-reporter.md
.claude/agents/artifact-librarian.md
.claude/agents/interactive-plan-writer.md
.claude/agents/repo-doc-steward.md
.claude/agents/sub-agent-maker-agent.md
.claude/agents/hook-maker-agent.md
.claude/agents/workflow-recipe-harvester.md
.claude/skills/subagent-routing/SKILL.md
.claude/skills/session-boundary-control/SKILL.md
.claude/skills/artifact-indexing/SKILL.md
.claude/skills/interactive-plan-doc/SKILL.md
.claude/skills/anatomy-drift-control/SKILL.md
.claude/skills/worktree-pr-flow/SKILL.md
.claude/skills/experiment-workflow/SKILL.md
.claude/skills/workflow-recipe-harvesting/SKILL.md
.claude/hooks/pre_compact_memory_check.py
.claude/hooks/pre_tool_guard.py
.claude/settings.example.json
.agent/anatomy-protocol.md
.agent/repo-editing-guardrails.md
.agent/model-routing-policy.md
.agent/session-tree-protocol.md
.agent/artifact-policy.md
.agent/release-agent-boundary.md
.agent/claude-code-recipe-policy.md
.agent/repo-documentation-topology.md
```

`sub-agent-maker-agent` 和 `hook-maker-agent` 的用途是把 human 使用 Claude Code 时反复出现的工作轨迹沉淀成 repo-local 能力：

```text
human repeated trajectory
→ maker agent summarizes stable pattern
→ choose agent / skill / hook / command / validator
→ draft repo-local asset
→ human review
→ branch / PR
→ validator
→ enabled in repo
```

这样优化不是靠 human 手动搬运规则，而是让 agent 帮你总结真实使用中的摩擦，把它们变成可审计、可回滚、可迭代的项目控制面。

更具体地说，Claude Code workflow 技巧应该进入 `lab/recipes/claude-code/`，而不是只进入“经验总结”。推荐用 `workflow-recipe-harvesting` skill 定期从 human-cc trace 中提炼候选 recipe：

```text
lab/traces/human-cc/<date>/<session>/
  transcript-summary.md
  plan-doc.md
  human-review.md
  git-diff.patch
  verification.log

lab/recipes/claude-code/<recipe-id>.yaml
lab/evals/cc-workflow/<recipe-id>.yaml
lab/reports/cc-workflow/<date>-retest.md
memory/current-practices.md
memory/deprecated-practices.md
```

Candidate recipe 必须有适用条件、反例、证据 trace、复测任务和过期时间。Human review 的对象不是“长篇总结”，而是一个小 diff：这个 recipe 是否真实、是否值得采用、是否应该 stable / deprecated。

### 3.7 五类 worker 之外的维护、交互和演化 subagents

最初推荐的五类 subagent 是执行层：

```text
repo-researcher
feature-worker
test-runner
experiment-monitor
checkpoint-writer
```

但真实 workflow 里还需要一组维护型和交互型 assets，用来替 human 记住“什么时候该切 session、哪个 branch 做什么、东西在哪里、subagent 应该花多少预算、哪些目录需要局部文档”：

```text
subagent-router-agent
  根据任务风险、证据标准、副作用半径，给 child agent 选择 model / effort / tools。

session-boundary-agent
  发现阶段变化、上下文过长、任务树分叉时，提示 checkpoint / compact / clear / branch。

branch-reporter
  汇总不同 branch / worktree 的功能分野、base、issue/PR、owned paths、merge target。

artifact-librarian
  维护 dataset、checkpoint、table、figure、result、document asset 的索引和归档状态。

interactive-plan-writer
  把当前阶段写成中文 plan doc，让 human 在 repo 文件里批注，再由 Claude Code 读取 diff、收敛计划、必要时提交 plan revision commit。

repo-doc-steward
  维护重要目录的 README / AGENTS / CLAUDE / ANATOMY 工作面，避免 repo 只对 agent 可读、对 human 不可读，或反过来只对 human 友好但 agent 找不到边界。
```

还需要演化型 assets，把真实使用轨迹变成可 review 的 repo-local 能力：

```text
sub-agent-maker-agent
  从重复 human-cc 轨迹中提出窄边界 subagent，不创建泛用大角色。

hook-maker-agent
  从反复出现的安全、状态、格式化、compact、artifact 维护动作中提出 hook。

workflow-recipe-harvester
  从 human-cc trace 中提炼 workflow recipe，绑定证据、反例、复测任务和过期时间。
```

这些 agent 不应该替代 main agent 决策。它们的价值是让 main agent 不必靠聊天历史和 human 记忆来维持控制面。

---

## 4. 一次标准 session 的生命周期

核心原则：不要把 session hygiene 交给 human 记忆。Claude Code 应该通过 `checkpoint-writer`、`session-boundary-agent`、`interactive-plan-writer`、statusline、hooks 和 repo-local ledgers 主动维护状态。

### 4.1 开始：定义目标、停止条件和状态文件

每个 session 开头先写清楚：

```text
Objective:
<this session should accomplish exactly what?>

Success criteria:
<what observable evidence proves success?>

Scope:
Allowed paths:
Forbidden paths:

Context budget:
If context > 60%, checkpoint before continuing.

Verification:
Commands / metrics / run ids / expected outputs.

State files:
memory/current-status.md
memory/session-tree.md
plans/<date>-<slug>.zh.md
memory/branches/<slug>.md
```

示例：

```text
Objective:
Understand why Seiler Table 2 baseline differs from our reproduced metric.

Success criteria:
Find the exact data split, checkpoint, preprocessing, or eval setting difference.
No code edits unless the cause is isolated and I explicitly ask.

Scope:
Read only: scripts/eval*, configs/seiler*, docs/runs/seiler*
Forbidden: data/, checkpoints/, wandb/, runs/
```

如果任务已经不是几分钟内能完成的小问题，先让 `interactive-plan-writer` 写一个中文 plan doc，而不是把 plan 只留在聊天里。

### 4.2 交互式中文计划文档

这是比 Vim plan mode 更适合你的实践：让 Claude Code 把一个 session 或阶段要做的事情写成 repo 内中文文档，human 直接在文件里批注，Claude 再读取 diff、修改计划、提交计划修订。

建议路径：

```text
plans/<YYYYMMDD>-<topic>.zh.md
```

模板：

```markdown
# <topic> 交互式计划

## 当前目标

## 非目标

## Branch / worktree

## Linked issue / PR

## Allowed paths

## Forbidden paths

## 任务树
- [ ] Parent task
- [ ] Child task A
- [ ] Child task B

## Human 批注区

## 当前决策

## 未解决问题

## 验证标准

## 下一步

## Plan revision log
```

操作流：

```text
Claude writes initial plan doc in Chinese.
Human edits/comments in the file.
Claude reads git diff of the plan doc.
Claude summarizes changed assumptions and open questions.
Claude revises the plan doc.
Each accepted plan revision gets a small local commit if repo policy asks for traceability.
Implementation starts only after scope / forbidden paths / verification are clear.
```

这样 plan doc 变成当前 session 的锚点：它防止 Claude Code 漂移到额外动作，也防止 human 只凭记忆追踪“刚才我们到底决定了什么”。

### 4.3 探索：read-only first

复杂任务先让 Claude 读，不让它改。

```text
Enter plan/read-only mode.
Use repo-researcher if helpful.
Map where <feature/experiment> is implemented.
Return evidence and a proposed plan.
Do not edit.
```

### 4.4 计划：先拆边界，再开 worker

计划必须包含：

- 任务拆分。
- 每个任务的文件所有权。
- 冲突风险。
- 验证命令。
- 回滚方式。

不要接受只写“我会修改相关文件”的 plan。要求具体路径。

如果需要 subagent，先走 `subagent-routing`：

```text
Use subagent-router-agent.
Return model/effort/tool budget for each child task.
Do not launch broad general-purpose workers.
```

### 4.5 实现：小步修改，小步测试

```text
Implement only step 1 from the plan.
After editing, run the smallest relevant test.
If it fails, stop and summarize the failure before broad changes.
```

非 trivial edit 应该进入 issue / branch / worktree / PR flow，而不是直接在长期 checkout 上改：

```text
issue -> branch from correct base -> fresh worktree -> implementation -> validation -> PR -> review -> merge
```

### 4.6 验证：fresh evidence

验收输出至少包含：

```text
Changed files:
Commands run:
Test result:
Remaining risks:
Evidence paths:
```

对实验结果，还要包含：

```text
git commit:
config path:
run id:
checkpoint path:
data split:
metric source:
```

### 4.7 阶段边界：由 Claude 主动提醒

以下情况不要继续沿着同一上下文滚下去：

- 探索结束，准备实现。
- 实现结束，准备 review。
- debug 已经有多个失败假设。
- 任务树出现两个以上子任务。
- context 进入 repo 阈值。
- 需要从普通结果 promotion 到 paper claim。

操作：

```text
Use session-boundary-agent.
Update memory/session-tree.md and relevant branch status.
Decide: continue / compact / clear / branch / fresh reviewer.
Write exact next prompt before boundary.
```

### 4.8 结束：写状态，不靠记忆

每次结束 session 前，让 `checkpoint-writer` 做，而不是靠 human 想起来：

```text
Use checkpoint-writer to update memory/current-status.md.
Then summarize in 10 lines:
- Done
- Evidence
- Open risks
- Next exact action
```

如果这轮有 plan doc、branch status、artifact index 或 experiment ledger 变化，也要在同一个结束动作里更新，不要把它们留给“以后整理”。

---

## 5. Context 管理纪律

### 5.1 状态阈值应该由系统提醒

建议把 statusline 当仪表盘：

```text
0-40% context:
  正常工作。

40-60%:
  注意是否有无关历史；避免粘贴大日志。

60-70%:
  完成当前小目标后 checkpoint + compact。

70%+:
  不开新方向。先落盘状态，再 compact/clear。

80%+:
  只做恢复动作：memory/current-status、export、compact/clear。
```

这些数值不是官方硬限制，而是操作习惯。社区中有 `/compact` 在 context 满时失败的报告，所以不要等到最后一刻。

把这些阈值写进 repo-local workflow：

```text
statusline:
  显示 context%、model、effort、branch、worktree、session usage。

PreCompact hook:
  compact 前检查 memory/current-status.md 是否更新。

session-boundary-agent:
  当任务进入新阶段或 context 高时，建议 branch / compact / clear / fresh reviewer。
```

human 可以偷懒，系统不能假设 human 会记得。

### 5.2 compact 前清单

```text
Before /compact:
- Is memory/current-status.md updated?
- Are changed files listed?
- Are test commands/results listed?
- Are open decisions listed?
- Are subagent reports linked?
- Is the exact next prompt written?
```

推荐 compact 指令：

```text
/compact Preserve:
- current objective
- decisions made
- changed files
- test commands and results
- unresolved blockers
- exact next steps
- paths that must not be modified
Discard:
- verbose logs
- failed dead-end hypotheses
- repeated tool outputs
```

### 5.3 clear vs compact vs rewind vs branch

```text
/clear
  用于切换无关任务。保留 session 可 resume，但当前上下文清空。

/compact
  用于继续同一任务，但压缩历史。

/rewind
  用于撤回错误方向，或只总结某段历史。

/branch or session fork
  用于从父 session 派生一个子任务，保留父任务树和 child handoff。
```

实践建议：

- 新研究问题：`/clear`
- 同一任务进入下一阶段：checkpoint + `/compact`
- 一个 parent session 下出现多个独立子任务：session branch / child session
- Claude 走错方向：`Esc` / `/rewind`
- 代码已乱：Git diff + checkpoint / rewind / reset by explicit human decision

如果当前 Claude Code surface 支持 `/branch`，把它当作质量工具使用；如果不支持，就用 `memory/session-tree.md` + 新 session + handoff 文件模拟同样的树状结构。

### 5.4 Session tree 模板

`memory/session-tree.md`：

```markdown
# Session Tree

## Parent objective

## Current phase

## Children
| id | purpose | branch/worktree | plan doc | status | next prompt |
|---|---|---|---|---|---|

## Merge / review order

## Global forbidden paths

## Open risks
```

`memory/branches/<slug>.md`：

```markdown
# Branch Status: <slug>

## Purpose
## Parent session
## Branch / base
## Worktree
## Linked issue / PR
## Owned paths
## Forbidden paths
## Plan doc
## Current state
## Evidence
## Exit condition
```

让 `session-boundary-agent` 和 `branch-reporter` 维护这些文件。human 只需要在发现漂移时说“检查 session boundary”或“报告当前 branches”，不需要自己背所有细节。

---

## 6. 多 agent / worktree 工作流

这里不要只理解成“同时开几个 agent”。你现在的真实实践更接近两种 repo-local 协作模式：

```text
pairwise-diffusion:
  Issue -> branch off jieke/dev -> fresh worktree -> PR -> owner review -> merge back to jieke/dev

DOLoop:
  branch-local mainline per task family
  e.g. mainline/agentic_system, mainline/wb
  -> many short topic branches / PRs
  -> branch-local hygiene + harness validation
```

第一种适合单一 active trunk 的 research repo。第二种适合多个任务家族或 agent-system lineages 并行演化，但仍需要 branch-local hygiene，避免不同 domain 的文档、代码、artifact 混线。

### 6.0 默认流程：issue -> branch -> worktree -> PR

非 trivial 开发、bugfix、研究基础设施改动、agent harness 改动，都默认走这个流程：

```text
1. Create or identify issue / task packet.
2. Choose correct base branch.
3. Create short topic branch.
4. Create fresh worktree for that branch.
5. Read AGENTS.md / CLAUDE.md / ANATOMY.md / memory/current-status.md.
6. Implement only branch scope.
7. Update anatomy / ledger / plan / artifact index in the same branch if affected.
8. Run targeted tests and repo validator.
9. Draft PR with evidence and risks.
10. Main agent / human reviews.
11. Merge into the correct target.
12. Archive branch/worktree status.
```

这不是形式主义。它解决的是并行开发最难的问题：每个 branch / worktree 都有清楚功能分野、可审查 diff、可回滚历史和明确 merge target。

### 6.1 什么时候不用并行

不要并行：

- 需求还不清楚。
- 文件边界不清楚。
- 任务共享同一个核心模块。
- 你没有时间审查 merge。
- 只是为了“感觉很强”。

### 6.2 什么时候用并行

适合并行：

- A 读论文，B 读 repo。
- A 实现 dataset，B 写 targeted tests。
- A 修 backend，B 修 frontend，边界清楚。
- A 跑 baseline，B 整理 paper table。
- A 做 implementation，B 在 fresh context review diff。

### 6.3 并行任务单模板

```markdown
# Parallel Task Packet

## Shared objective
<one sentence>

## Global forbidden paths
- lab/data/**
- lab/runs/**
- lab/infra/private/**
- checkpoints/**
- wandb/**

## Worker A
- Task:
- Owns:
- Must not touch:
- Verification:
- Report path:

## Worker B
- Task:
- Owns:
- Must not touch:
- Verification:
- Report path:

## Merge order
1. Worker A
2. Worker B

## Human/main-agent review
- read reports
- inspect git diff
- run integration test
- update anatomy / ledgers / memory if needed
```

### 6.4 Worktree / branch 规则

```text
Non-trivial edit = fresh worktree.
One worktree = one branch purpose.
One branch purpose = one issue / PR / acceptance target.
One branch purpose = one status record in memory/ or branch-local ledger.
```

对 `pairwise-diffusion` 式 trunk workflow：

```text
git fetch origin
git worktree add -b <branch> <repo>-<slug> origin/jieke/dev
cd <repo>-<slug>
sanity check: lab/code/src exists
read AGENTS.md + ANATOMY.md + memory/current-status.md
implement smallest branch scope
run python3 scripts/ops/validate_governance.py
open PR to jieke/dev after human approval
owner/main agent reviews and merges
delete/retire branch/worktree after merge
```

对 `DOLoop` 式 branch-local mainline workflow：

```text
choose mainline/<domain> or benchmark/<domain>
create short topic branch from that branch-local mainline
use dedicated worktree unless this is an approved cross-cutting governance pass
run domain hygiene + harness validator
merge back into that branch-local mainline through PR
do not leak task-family terms, datasets, artifacts, or claims across mainlines
```

每个 worktree / branch 状态记录：

```markdown
# Branch / Worktree Status

## Purpose
## Branch / base
## Owner
## Linked issue / PR
## Scope
## Forbidden paths
## Anatomy impact
## Claim / evidence impact
## Current state
## Commands run
## Latest result
## Open risks
## Exit condition
```

### 6.5 Merge queue

不要让多个 worker 自己互相 merge。main agent 或人类维护一个 merge queue：

```text
1. Read worker report.
2. Inspect diff.
3. Check anatomy impact.
4. Check ledger / evidence impact.
5. Run targeted tests.
6. Run harness validator.
7. Merge/cherry-pick or approve PR.
8. Update memory/current-status.md / branch status.
```

真正能并行的前提不是“agent 多”，而是这些东西提前分清：

- branch base。
- owned files / forbidden paths。
- issue / PR target。
- anatomy impact。
- evidence / release gate impact。
- validator command。
- merge order。

### 6.6 Branch / worktree 功能分野报告

当 branch 或 worktree 多起来，必须有报告机制。否则 human 和 main agent 都会忘记：

- 哪个 branch 是 trunk。
- 哪个是 branch-local mainline。
- 哪个是短期 feature/fix。
- 哪个 worktree 已经过期。
- 哪个 PR 等待 review。
- 哪个实验或 artifact 属于哪个分支。

使用 `branch-reporter` 生成报告：

```text
Report all active branches/worktrees.
For each one include:
- branch
- base
- worktree path
- purpose/domain
- linked issue/PR
- owned paths
- forbidden paths
- anatomy/ledger impact
- latest validation
- merge target
- sibling dependencies
- exit condition
Do not push, merge, delete, or close anything.
```

报告可以落地为：

```text
memory/worktree-status.md
memory/branches/<slug>.md
PR body draft
```

对 `pairwise-diffusion` 式项目，branch 报告重点是所有短分支如何回到 `jieke/dev`。对 `DOLoop` 式项目，branch 报告重点是每个 `mainline/<domain>` 的功能边界，以及短分支是否回到了正确的 branch-local mainline。

---

## 7. 实验工作流

实验 workflow 不应该只存在于手册里。建议把它做成 repo-local `experiment-orchestrator` subagent，并配一个 `.claude/skills/experiment-workflow/SKILL.md`。这个 agent 的职责不是“帮我跑实验”，而是维护实验从 claim 到 artifact 的证据链。

建议能力边界：

```text
experiment-orchestrator
  reads:
    lab/research/claims.yaml
    lab/research/evidence.yaml
    lab/research/experiment-ledger.yaml
    lab/infra/storage/
    lab/infra/launch/
    memory/current-status.md
  writes only with explicit task scope:
    experiment cards
    run summaries
    artifact indexes
    evidence proposals
    memory/current-status.md
  never does without explicit human approval:
    launch remote job
    kill/restart job
    delete checkpoint/output/data
    promote result to paper claim
```

### 7.1 实验前

实验不是“跑一下看看”。先写 experiment card：

```markdown
# Experiment Card

## Question
What claim does this test?

## Hypothesis

## Code commit

## Config

## Data split

## Baseline / comparison

## Expected runtime

## Success metric

## Failure signals
- OOM
- NaN
- metric stall
- missing checkpoint
- data mismatch

## Artifact paths
```

### 7.2 启动实验

Prompt：

```text
Prepare the experiment launch command, but do not run it yet.
Verify:
- config path exists
- data split is correct
- output dir is unique
- checkpoint source is correct
- wandb/mlflow run name is descriptive
- command is reproducible from the repo root
Return the command and checklist.
```

如果需要真的运行，再明确授权。

### 7.3 监控实验

不要让 Claude 长时间“守着”完整日志。让实验自己跑，Claude 定期读 bounded 状态。

```text
Use experiment-monitor.
Read only:
- logs/<run>.log last 200 lines
- runs/<run>/status.json
- wandb/mlflow latest metrics if available
Report only:
- status
- latest metrics
- checkpoint freshness
- anomalies
- whether intervention is needed
```

### 7.4 实验后

每个实验结束后写 run summary：

```markdown
# Run Summary

## Run id
## Commit
## Config
## Data
## Checkpoint
## Metrics
## Comparison
## Interpretation
## Failure / caveats
## Artifact links
## Should promote to paper?
yes/no/unclear
```

只有满足以下条件，结果才进入 `lab/research/evidence.yaml`、`lab/artifacts/result-index.yaml` 或论文：

- run 可定位。
- config 可复现。
- metric 来源清楚。
- 与 baseline 比较清楚。
- caveat 被写明。
- fresh reviewer 或你本人复核过。

### 7.5 资产索引与过期归档

实验事实和实验资产必须一起管理。否则 human 很快会忘记：

- checkpoint 在哪里。
- dataset split 是哪个。
- table 是哪次 run 生成的。
- figure 对应哪个 commit。
- data card / model card 放在哪里。
- 哪些 run 已经被新实验 supersede。

使用 `artifact-librarian` 和 `artifact-indexing` skill 维护这些文件：

```text
lab/artifacts/result-index.yaml
lab/artifacts/table-index.yaml
lab/artifacts/figure-index.yaml
lab/models/checkpoint-index.yaml
lab/data/dataset-index.yaml
deliverables/index.md
```

Prompt：

```text
Use artifact-librarian.
Index the assets produced or referenced by this experiment.
For each asset return:
- logical id
- storage path / URI
- how to inspect it
- commit / config / run id
- claim/table/figure dependency
- active / superseded / archived / unknown
- missing metadata
- archive recommendation
Do not delete or move data/checkpoints/runs.
```

定期让 Claude Code 生成 stale asset report：

```text
Find active artifacts older than <N> days with no linked claim or deliverable.
Find superseded checkpoints still marked active.
Find tables/figures whose source run is missing.
Return archive proposals only; do not delete.
```

repo 干净的目的不是好看，而是让 future session 能快速知道哪些事实还活着。

---

## 8. Paper reproduction 工作流

### 8.1 三层目标

复现 paper 时不要直接说“实现这篇论文”。拆成：

```text
Layer 1: 读懂 claim 和 method。
Layer 2: 找到 repo 中对应实现。
Layer 3: 跑最小 smoke / sanity / metric check。
```

### 8.2 Prompt 模板

```text
We are reproducing <paper>.
Goal: map paper claims to code and identify the minimal runnable reproduction path.

Use read-only mode first.
Return:
1. Paper claims relevant to reproduction
2. Code files implementing each claim
3. Required data/checkpoints
4. Minimal smoke test
5. Full reproduction command if available
6. Missing pieces / ambiguity

Do not edit code yet.
Do not download large assets locally.
```

### 8.3 复现实验证据表

```markdown
| Paper claim | Code path | Config | Data/checkpoint | Run id | Metric | Status |
|---|---|---|---|---|---|---|
```

---

## 9. Paper writing / LaTeX 工作流

TODO：这一节未来需要单独起一个新文档重点阐述，系统整理 AI PhD 论文写作、LaTeX 编辑、证据表、figure/table 来源、compile policy、reviewer workflow 和 Overleaf / local / CI 协作方式；当前只保留最小提示和边界。

### 9.1 写作前先锁 contract

```markdown
# Writing Contract

## Target venue
## Paper story
## Non-negotiable claims
## Claims not yet proven
## Figure/table sources
## Anonymous / public-source constraints
## Sections to edit
## Sections not to edit
```

### 9.2 修改 prompt

```text
Edit only Section <X>.
Use the writing contract and current evidence table.
Do not introduce claims not supported by docs/results/.
Do not change LaTeX macros or bibliography unless needed.
Return:
- changed paragraphs
- claims added/removed
- evidence source for each claim
- compile/test command if run
```

### 9.3 写作 reviewer

用 fresh context 做 reviewer：

```text
Review this section against the evidence table.
Find unsupported claims, overclaims, missing caveats, and inconsistent terminology.
Do not rewrite yet.
Return line-level issues and suggested fixes.
```

---

## 10. 常用 prompt 模板

### 10.1 快速 repo 定位

```text
Use read-only exploration.
Where is <concept> implemented?
Find minimal relevant files and symbols.
Explain the data/control flow.
Do not edit.
```

### 10.2 Debug

```text
We have this failure:
<short error>

Do not fix yet.
First produce:
1. likely root causes
2. evidence for/against each
3. minimal next probe
4. files likely involved

Then wait for implementation instruction.
```

### 10.3 实现

```text
Implement <specific change>.
Scope:
- allowed files:
- forbidden files:

Constraints:
- match existing style
- no new dependency
- targeted tests only unless needed

Verification:
- run <command>
- report exact result
```

### 10.4 代码审查

```text
Review the current diff as a fresh reviewer.
Focus on:
- correctness
- regressions
- missing tests
- research reproducibility
- data/checkpoint safety

Do not summarize first.
List findings by severity with file references.
```

### 10.5 Handoff

```text
Write a handoff for a fresh Claude Code session.
Include only:
- objective
- current status
- decisions
- modified files
- commands/results
- open blockers
- exact next prompt
- forbidden paths
Keep it under 120 lines.
```

---

## 11. Permissions / hooks 设计建议

这不是 user-global 配置补丁，只是 repo-local 实践原则。项目相关 permissions / hooks 应该被仓库记录：`.claude/settings.json` 负责 Claude Code 加载，`.agent/action-boundary.md` 或 `lab/infra/permissions/` 负责解释为什么这样限制，`scripts/` / CI 负责验证关键约束没有漂移。

### 11.1 权限策略

建议 repo-local deny：

```text
Agent(general-purpose)
Edit(lab/data/**)
Edit(lab/runs/**)
Edit(lab/infra/private/**)
Edit(checkpoints/**)
Edit(wandb/**)
Bash(rm -rf *)
Bash(sudo *)
Bash(git push *)
Bash(pip install *)
Bash(curl * | sh)
```

建议 repo-local ask：

```text
Bash(git commit *)
Bash(git checkout *)
Bash(git worktree remove *)
Bash(uv add *)
Bash(uv sync *)
Bash(kill *)
Bash(sbatch *)
Bash(runai *)
Bash(gh pr create *)
Bash(gh pr merge *)
```

建议 repo-local allow：

```text
Bash(git status)
Bash(git diff *)
Bash(git diff --check)
Bash(pytest *)
Bash(ruff check *)
Bash(ruff format --check *)
Bash(mypy *)
Bash(tail *)
Bash(grep *)
Bash(rg *)
Bash(python scripts/check-agent-harness.py *)
Bash(python scripts/ops/validate-governance.py *)
Bash(python scripts/check-anatomy-drift.py *)
```

具体项目要按真实工具调整。关键不是这三张列表本身，而是每条高风险能力都能在 repo 内找到理由、owner、验证方式和 human gate。

### 11.2 Hook 策略

推荐 repo-local hooks：

```text
Notification:
  Claude 等待输入或权限时通知。

PostToolUse(Edit|Write):
  对 Python/JS/TS 等运行 formatter 或静态检查。

PreCompact:
  检查 memory/current-status.md 或 handoff 是否最近更新。

SubagentStart/SubagentStop:
  写 .claude/agent-reports/ 或 memory/handoffs/ 索引。

PreToolUse(Bash):
  阻止 rm -rf、sudo、curl | sh、未知 deployment 等。

PreToolUse(Edit|Write):
  阻止直接写 lab/runs、lab/data bytes、private overlays、checkpoint bytes。

PreToolUse(gh):
  push / PR / merge / release / repo settings mutation 进入 human gate。
```

注意：社区有 worktree / desktop 环境下 hook 行为不一致的 bug 报告，所以依赖 hook 的高风险 workflow 要定期验证。

### 11.3 Repo validator 优先于口头纪律

如果某条规则真的重要，不要只写在 prompt 里。把它变成 repo validator：

```text
Claude Code rule
→ .agent/action-boundary.md or .claude/settings.json
→ scripts/check-agent-harness.py
→ CI / PR template
→ CODEOWNERS review
```

例如：

- 禁止 root 污染：validator 检查 root 只出现白名单文件。
- 禁止大 bytes 进 Git：validator 检查 `lab/runs/`、checkpoint、dataset bytes。
- 禁止 anatomy 漂移：validator 检查 `ANATOMY.md` 引用路径和行号。
- 禁止 release overclaim：validator 检查 deliverables 是否引用 supported evidence。
- 禁止无索引能力：validator 检查 `.claude/agents/`、`.claude/skills/` 是否有 manifest / owner / verification。

---

## 12. 模型与 effort 策略

这里的基本设定是：main agent 可以使用最好的模型和最高 effort，因为它负责理解 human 目标、做权衡、整合 subagent 结果和最终验收。需要自动化的是 child agent 的预算选择。

```text
tier 0:
  no subagent; direct shell / grep / rg

tier 1:
  fast model / low effort / read-only
  lookup, file mapping, bounded log summary

tier 2:
  standard model / medium effort
  bounded implementation, targeted tests, small doc update

tier 3:
  strong model / high effort
  deep debug, architecture, shared contract, anatomy/validator changes

tier 4:
  strong model / high effort / fresh context
  final verifier, paper claim review, release gate, expensive experiment decision
```

自动路由流程：

```text
Human says: open a subagent to do <task>.
Main agent reads .agent/model-routing-policy.md.
If obvious, main agent chooses tier directly.
If not obvious, use subagent-router-agent.
Router returns launch packet.
Main agent launches child with chosen model/effort/tools.
After result, main agent records whether the budget was too low/high/appropriate.
Routing policy is updated through issue/branch/worktree/PR when patterns stabilize.
```

Launch packet 模板：

```text
agent_type:
task:
budget tier:
recommended model:
recommended effort:
allowed paths:
forbidden paths:
tools:
context budget:
evidence required:
stop condition:
escalate condition:
```

不要默认把所有子任务都交给最高 effort。对研究生来说，usage budget 应该花在：

- 复杂 root cause。
- paper claim correctness。
- final review。
- 实验设计。
- 跨 repo 架构理解。
- shared contract / release gate。

而不是：

- `ls`
- `grep`
- tail log
- 改 typo
- 生成重复 boilerplate

校准规则：

- 子 agent 返工多：提高该类任务 tier 或收紧 task packet。
- 子 agent 输出过长污染主线程：改成 report file + summary。
- 子 agent 经常只是读文件：降级为 tier 0 / tier 1。
- 子 agent 触碰 shared contract：升级为 tier 3，并要求 fresh verifier。

---

## 13. 每周维护 checklist

```text
Claude Code:
- claude --version
- /usage 看 24h / 7d subagent-heavy usage
- 检查 statusline 是否显示 context/model/branch/worktree

Project memory:
- memory/current-status.md 是否短且最新
- lab/research/evidence.yaml 是否只含已确认结果
- CLAUDE.md 是否过长
- .agent/ / .claude/skills/ 是否有过时流程

Experiments:
- run summaries 是否齐全
- W&B/MLflow run names 是否可读
- stale checkpoints 是否有保留策略

Git/worktrees:
- git worktree list
- stale worktree 是否可归档
- 未 merge 分支是否有状态说明

Safety:
- lab/data/checkpoints/wandb/lab/runs 是否 gitignored 或只保留索引
- permissions 是否保护危险路径
- hooks 是否仍然触发
```

---

## 14. 推荐默认操作顺序

### 14.1 普通研究代码任务

```text
read-only explore
→ plan
→ implement small step
→ targeted test
→ update memory/current-status.md
→ compact/clear if needed
```

### 14.2 复杂 paper reproduction

```text
paper claim map
→ code path map
→ minimal smoke test
→ baseline reproduction
→ experiment card
→ run
→ run summary
→ fresh verifier
→ promote to paper evidence
```

### 14.3 多 agent 并行实现

```text
main creates task packet
→ worker per worktree
→ each writes report
→ main reviews diff
→ merge queue
→ integration verification
→ session/worktree status update
```

### 14.4 长实验监控

```text
experiment card
→ launch command reviewed
→ run outside chat
→ bounded monitor loop
→ anomaly-only intervention
→ run summary
```

---

## 15. 参考资料

官方文档：

- [Best practices for Claude Code](https://code.claude.com/docs/en/best-practices)
- [Manage costs effectively](https://code.claude.com/docs/en/costs)
- [Create custom subagents](https://code.claude.com/docs/en/sub-agents)
- [Extend Claude with skills](https://code.claude.com/docs/en/skills)
- [Hooks reference](https://code.claude.com/docs/en/hooks)
- [Claude Code settings](https://code.claude.com/docs/en/settings)
- [Customize your status line](https://code.claude.com/docs/en/statusline)
- [Run parallel sessions with worktrees](https://code.claude.com/docs/en/worktrees)
- [Checkpointing](https://code.claude.com/docs/en/checkpointing)
- [Manage sessions](https://code.claude.com/docs/en/sessions)
- [Commands](https://code.claude.com/docs/en/commands)
- [Interactive mode](https://code.claude.com/docs/en/interactive-mode)

官方 blog / engineering：

- [Effective context engineering for AI agents](https://www.anthropic.com/engineering/effective-context-engineering-for-ai-agents)
- [How we built our multi-agent research system](https://www.anthropic.com/engineering/multi-agent-research-system)
- [Enabling Claude Code to work more autonomously](https://www.anthropic.com/news/enabling-claude-code-to-work-more-autonomously)
- [How we built Claude Code auto mode](https://www.anthropic.com/engineering/claude-code-auto-mode)

Repo-local harness / 防漂移参考：

- `a-green-hand-jack/pairwise-diffusion` private repo, access required
- `a-green-hand-jack/DOLoop` private repo, access required
- [LingTai Anatomy System guide](https://gist.github.com/a-green-hand-jack/f2f153c72dda4ed92d35006137243d23)

实验记录工具：

- [W&B Artifacts](https://docs.wandb.ai/models/artifacts)
- [W&B run resuming](https://docs.wandb.ai/models/runs/resuming)
- [MLflow Tracking](https://mlflow.org/docs/latest/ml/tracking/)
- [MLflow for Deep Learning](https://mlflow.org/docs/latest/ml/deep-learning/)

社区材料：

- [Reddit: context management](https://www.reddit.com/r/ClaudeAI/comments/1mezb57/claude_code_tips_on_managing_context/)
- [Reddit: small context window](https://www.reddit.com/r/ClaudeCode/comments/1qps9xj/how_do_you_all_deal_with_claudes_small_context/)
- [Reddit: parallel coding agents](https://www.reddit.com/r/ClaudeCode/comments/1st213z/how_are_you_managing_multiple_coding_agents_in/)
- [Reddit: compacting strategy](https://www.reddit.com/r/ClaudeCode/comments/1trpxbb/what_is_your_claude_code_compacting_strategy/)
- [Hacker News: subagents and context](https://news.ycombinator.com/item?id=45181577)
- [Dan Does Code: custom statusline](https://www.dandoescode.com/blog/claude-code-custom-statusline)
- [ccusage statusline guide](https://ccusage.com/guide/statusline)
- [Voitanos: statusline and token burn](https://www.voitanos.io/blog/claude-code-cli-statusline/)
