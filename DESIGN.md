# 模板设计与实现说明

> **这份文档是什么**：`ml-project-repo-agent-native-template` 的**设计地图与实现 rationale**——
> 为什么这样分层、每个机制在哪实现、如何扩展维护。给 human 随时了解全局，也给 fresh agent
> 建立心智模型。
>
> **这份文档不是什么**：不是第二套 doctrine。真正的规则住在 `.agent/*.md`、`.claude/`、`.codex/`、`.agents/`、`scripts/`；
> 本文与它们冲突时**以源文件为准**。本文只做地图与解释，尽量指向源文件而非复制其内容。
>
> **来源**：设计精神与实践依据是 `.reference-docs/` 两份来源文档（spirit + practice）。本文是它们在本
> repo 的落地说明；`implementation-coverage-note.md` 记录当前实现相对参考文档的覆盖/超集关系。

---

## 0. 一句话

把「AI agent 如何在一个 ML 研究项目里工作」的治理，**固化进 repo 本身**：repo 是控制面，chat 只是短期意识流。agent 一进 repo 就知道能做什么、边界在哪、状态如何接续、结论是否可信。

---

## 1. 核心哲学（十二条的落地）

不可协商的原则在 `.agent/principles.md`（源自 spirit §7）。最影响架构的四条：

1. **Repo 是可信控制面**，不是代码容器；长期状态写文件，不写在聊天里。
2. **Main agent 做决策（PI/tech lead），subagents 做隔离任务（RA）。**
3. **Prompt 表达意图，hooks/permissions 执行硬约束。** 想让某事必然发生就写 hook。
4. **高模型/高 effort 是子任务预算，不是 agent 身份。**

---

## 2. 分层架构：好处由谁提供、在哪实现

benefit 不来自单个文件，而是**三层强制 + 一层人机接口**的协作：

```
Doctrine 层（为什么这样限制） ──  .agent/*.md
Enforcement 层（机器强制）    ──  .claude/settings.json · .codex/config.toml · .codex/rules · .claude/hooks/*.py · .claude/statusline.sh
Validation 层（证明没漂移）   ──  scripts/*.py · .github/workflows/governance.yml
人机接口层（human 可信信息也进 repo）── human/ · memory/ · plans/ · DECISIONS.md
```

**铁律：三层必须对齐。** doctrine 说「为什么」，settings/rules+hooks「机器执行」，scripts「验证没失配」。
改一层就要同步另两层（见 §11 same-commit rule）。

repo 的物理分层（"plane" 地图）在 `ANATOMY.md`（root router）。各 plane：

| plane | 目录 | 作用 |
| --- | --- | --- |
| 入口 | `README/AGENTS/CLAUDE/ANATOMY/PROJECT/DECISIONS` | human/agent 入口 |
| 交互 | `human/` | brief / review / decision / inbox |
| doctrine | `.agent/` | 行为契约、边界、政策、协议 |
| 能力 | `.claude/` + `.codex/` + `.agents/` | canonical subagents / skills / commands / hooks + Codex adapters |
| 研究控制面 | `lab/` | code / infra / research / data / artifacts / runs / recipes |
| 活状态 | `memory/` | current-status / session-tree / practices / dashboards |
| 对外承诺 | `deliverables/` | paper / slides / release |
| 门禁 | `scripts/` | harness / anatomy-drift / governance validators |

---

## 3. 安全模型：两层，性质不同（本模板最关键的设计）

> 详见 `.agent/action-boundary.md`（三档）、`.agent/human-gates.md`、`.agent/autonomous-window.md`。

把权限分成两层，性质完全不同：

| 层 | 谁 | auto mode / bypass 时 |
| --- | --- | --- |
| **permission**（allow/ask/deny/prompt，Claude settings + Codex rules/permission mode） | **可调** | 放宽，不打断低风险 |
| **hook 地板**（`.claude/hooks/pre_tool_guard.py`） | **不可调** | 照常拦截红线 |

**设计要点**：把「绝对不能发生」下沉到 hook 地板（数据/产物 bytes、`.git`、提权、远程执行、推 `main`），
只把「有人在就确认一下」留在 `ask`。于是**放宽 permission 才安全**——致命动作根本不在可放宽的那层。
这让「human 开 auto mode 后不再被自己的实现打断」与「红线永远守得住」同时成立。

### 3.1 permission 三档（Claude `settings.json` / Codex rules）

- **deny**：受保护路径写入、`sudo`、`curl|sh`、`pip install`、无边界 `general-purpose` agent。
- **ask**：有损/改历史 git（checkout/reset/clean/rebase/merge/branch -d）、`uv add/sync`、`kill/sbatch/runai`、`gh pr create/merge`。
- **allow**（Claude settings 约 ~115 条；Codex rules 覆盖关键低风险前缀）：只读 shell、只读 git、开发工具、`uv run`、`python -c`、`Edit/Write`（受保护路径除外）、可逆 git（add/commit/stash）、清缓存目录。

### 3.2 hook 地板（`pre_tool_guard.py`）

用 **shlex 真正解析命令**（不是子串正则），因此：
- 引号里的字面量（commit message、`echo "..."`）**不误伤**；
- 引号里的真实路径/分支（`rm -rf "lab/data"`、`git push origin "main"`）**仍识别**。

它拦：提权/远程执行、`pip install`、`rm -r` **按目标分级**（缓存/构建/临时可删；数据·产物·`.git`·绝对路径·仓库根·`..` 拦；`find -exec` 嵌套有兜底正则）、`mv/cp/rsync/dd` 触碰受保护路径、受保护路径的 `Edit`/`Write`/Codex `apply_patch`、push 到 `main/master`（除非 `CLAUDE_ALLOW_PUSH_MAIN=1` 或 `CODEX_ALLOW_PUSH_MAIN=1`）。

诚实边界：hook 是**防误操作护栏，非对抗性沙箱**——不审查 `python -c`/`uv run`/`pytest` 内部的代码（这类代码执行本就被信任），数据最终靠 gitignore + 备份。

### 3.3 自主窗口（`autonomous-window.md` + `settings.local.json.example`）

human 出门/睡觉但任务要跑时：Claude Code 可 `cp` 出 `settings.local.json`（git-ignored）临时放宽
`ask→allow`；Codex 用本次 task permission mode / approved rules 控制同一层。permission 放宽而 hook
地板照守，所以「授权自主」安全。

### 3.4 副作用半径与人机门禁

选动作按「错了会怎样」判断（`action-boundary.md` §副作用半径）。外部/不可逆动作走 `human-gates.md`：
agent **准备**（写好 commit、起草 PR body、生成归档提案），human **触发**。
机器层是 Claude settings / Codex rules + hook；流程层是 `pull_request_template.md` + `CODEOWNERS`；记录层是 `human/decisions/`。

---

## 4. Subagent 与模型路由

> 详见 `.agent/model-routing-policy.md`、`.agent/templates/launch-packet.md`、`.claude/skills/subagent-routing/`。

- 16 个 subagent canonical 定义在 `.claude/agents/`，Codex custom-agent adapters 生成到 `.codex/agents/`。
  除 `zh-review-gate`（刻意锁定廉价模型，见其
  frontmatter 说明）外全部 `model: inherit`——**不写死模型**。
- 因为「预算不是身份」：模型/effort 由**任务形状**决定，不由角色名决定；`zh-review-gate`
  是经 human 明确要求的窄例外——它的存在理由就是「不管主 session 用什么模型都要有廉价兜底」。
- 派发时按 tier 0–4 选预算（tier 0 直接 shell；tier 4 = paper claim / final verifier，strong+high+fresh）。
  不明显时由 `subagent-router-agent` 生成 launch packet（agent 类型/tier/model/effort/边界/停止条件）。
- main agent 可用最强模型 + 最高 effort（负责目标/整合/验收）；child 按任务自动路由。
- subagent 分四层：执行 / 协调 / 维护交互 / 演化（见 §10 清单）。长报告写 `.claude/agent-reports/`，主线程只接摘要。
- Codex 不读取 `.claude/commands/*.md` 作为项目 slash commands；这些命令会生成 `.agents/skills/command-*`
  adapters，作为 Codex 可显式调用的技能入口。

---

## 5. 结构防漂移：ANATOMY 系统

> 详见 `.agent/anatomy-protocol.md`、`.agent/repo-documentation-topology.md`。

- 每个重要目录有**导航四件套**：`README`（给 human）/`AGENTS`（给 agent）/`CLAUDE`（薄路由）/`ANATOMY`（结构地图）。
- `ANATOMY.md` 是给 coding agent 的**地图不是教程**：组件、调用关系、持久状态、line-addressed 引用（`file.py:42`）。根只做 router。
- **same-commit rule**：结构改动（移动/改名/拆分/合并/改 ownership/状态 shape）必须同 commit 更新相关 anatomy 与 ledger。由 `scripts/check-same-commit.py` 机器强制（pre-commit hook `.githooks/` + CI），逃生 `SAME_COMMIT_SKIP=1`/`--no-verify`。
- `scripts/check-anatomy-drift.py` 挡 missing file / out-of-range line / 超 120 行硬上限；语义正确性仍需 agent 打开代码验证。

---

## 6. 研究事实与资产：证据链

> 详见 `.agent/artifact-policy.md`、`.agent/principles.md` §证据分层。

- 证据分层：`log < metric < table < figure < paper claim`。
- **台账**（`lab/research/`）：`claims.yaml`（主张）↔ `evidence.yaml`（已确认证据，含 commit/run_id/config/checkpoint/data_split/metric_source）互相引用，构成可追溯证据链。
- **索引**（`lab/artifacts/` + `lab/data/` + `lab/models/`）：大 bytes 不进 Git，只留逻辑索引（status: active/superseded/archived/unknown）。由 `artifact-librarian` 维护。
- **进 evidence 的门槛**：run 可定位、config 可复现、metric 来源清楚、与 baseline 比较清楚、caveat 写明、经 fresh verifier。
- **overclaim 由 validator 拦截**（不只口头）：`validate-governance.py` 校验 claims↔evidence 引用可解析，且 claim 强度 ≤ 最强证据（`supported` 需 ≥metric 证据；paper-grade 需经 fresh reviewer 的 paper-claim 证据）。
- promote 结果为 paper claim 走 human gate。

---

## 7. 状态与记忆：让 fresh session 永远能接续

> 详见 `.agent/context-memory-policy.md`、`.agent/session-protocol.md`、`session-tree-protocol.md`。

- context 是昂贵工作记忆，磁盘是长期记忆。阈值（40/60/70/80%）驱动 checkpoint/compact，由 statusline + `PreCompact` hook + `session-boundary-agent` 提醒。
- 落盘位置：`memory/current-status.md`（单一真相源）、`session-tree.md`（分支树）、`branches/<slug>.md`、`plans/<date>-<slug>.zh.md`、`phase-dashboard.yaml`、`change-control.yaml`。
- 新 session 不是失忆是分支：parent 保全局目标，child 只背一个小目标 + 证据标准。

---

## 8. Recipe 演化循环：把 CC 技巧沉淀成可复测资产

> 详见 `.agent/claude-code-recipe-policy.md`。

```
lab/traces/human-cc/  →  lab/recipes/claude-code/<id>.yaml  →  lab/evals/cc-workflow/  →  lab/reports/  →  memory/current-practices.md
（原始轨迹）              （候选 recipe，带状态机+过期）        （复测任务）              （报告）          （采用索引）
```

recipe 有状态机（candidate→provisional→stable→deprecated）、证据 trace、反例、过期时间；由 `workflow-recipe-harvester` 提炼，human review 的是小 diff。Claude Code 会漂移，所以技巧要能复测、会降级。

---

## 9. 人机接口：human 的可信信息也进 repo

`human/`（briefs / reviews / decisions / inbox）+ `plans/`（交互式中文 plan doc）+ `DECISIONS.md`（ADR 索引）。
human 通过 repo-local brief / review / decision 与 agent 协作，而不是靠回忆聊天。

---

## 10. 能力清单（实现在哪）

| 类别 | 位置 | 数量 | 说明 |
| --- | --- | --- | --- |
| Subagents | `.claude/agents/` | 16 | 执行(6) / 协调(2) / 维护交互(5) / 演化(3)，除 `zh-review-gate`（锁定 `haiku`）外全 `model: inherit` |
| Skills | `.claude/skills/` | 13 | worktree-pr-flow / experiment-workflow / artifact-indexing / session-boundary-control / subagent-routing / interactive-plan-doc / anatomy-drift-control / workflow-recipe-harvesting / template-stress-test / adopt-existing-repo / coding-agent-quota / template-feedback / spawn |
| Commands | `.claude/commands/` | 8 | checkpoint / experiment-watch / feature-split / paper-reproduce / pr-review / result-promote / weekly-maintenance / adopt-existing-repo |
| Hooks | `.claude/hooks/` | 11 | pre_tool_guard（地板）/ format_changed_python（提醒）/ pre_compact_memory_check（提醒）/ subagent_report_index（记录）/ zh_review_advisory（提醒）/ context_threshold_notice（阈值注入）/ context_continuity（compact 后回注）/ agent_identity_hook（自命名指令+自知注入）/ context_usage（helper）/ agent_identity（身份解析 helper）/ agent_name_set（自命名 setter：rename+roster） |
| Codex adapters | `.codex/` `.agents/` | 16 agents + 21 skills | `.codex/agents` custom-agent adapters；`.agents/skills` 包含 13 个 workflow skill + 8 个 command adapter |
| Validators / tools | `scripts/` | 9 | check-agent-harness / check-anatomy-drift / validate-governance / check-same-commit / adopt-existing-repo / check-adoption-integrity / sync-codex-adapters / bump-template-version / template-sync |
| Doctrine | `.agent/` | 20 md | 索引在 `.agent/AGENTS.md`（读取顺序 1–17，另含 `AGENTS.md`/`README.md` 本身） |
| 模板 | `.agent/templates/` | 9 | launch-packet / experiment-card / run-summary / handoff / branch-status / plan-doc / session-brief / parallel-task-packet / anatomy |
| 清单 | `.agent/checklists/` | 4 | pre-compact / pre-parallel / session-boundary / weekly-maintenance |

---

## 11. 如何扩展与维护

- **新能力先登记 contract/manifest 再写实现**；没有索引的能力不算正式 surface（`tool-skill-interface.md`）。
- **能力 repo-local**：项目相关 agent/skill/command/hook canonical 源放 `.claude/`，Codex adapters 放 `.codex/` / `.agents/`，不装 user 全局。
- **same-commit rule**：改结构/doctrine/能力，同 commit 更新相关 anatomy / README / ledger / validator。
- **改前后跑门禁**：`python scripts/validate-governance.py`（CI 在 push/PR 跑 `--strict`）。
- **演化靠 maker agents**：`sub-agent-maker-agent` / `hook-maker-agent` / `workflow-recipe-harvester` 从真实使用轨迹提炼草稿，human review 后经 PR 纳入。
- **每周维护**：`/weekly-maintenance` 驱动 `.agent/checklists/weekly-maintenance.md`。

---

## 12. 关键设计决策（rationale）

| 决策 | 为什么 |
| --- | --- |
| 能力 repo-local 而非 user 全局 | repo 是最直接、可审计、可被 fresh session 读取的上下文；技巧不该只在某个人的机器上 |
| `.claude/` canonical + Codex generated adapters | Claude Code 与 Codex 的发现路径/格式不同；保留一个源真相，机械生成 `.codex/agents` 与 `.agents/skills`，避免两套能力手写漂移 |
| subagent `model: inherit`，不写死 | 预算是任务属性不是角色属性；写死会把成本绑在名字上，且无法校准。唯一例外 `zh-review-gate` 锁定 `haiku`——它的职责就是「不管主 session 多贵都要有廉价兜底」，经 human 明确要求，见该 agent 文件内说明 |
| 权限两层（permission 可调 / hook 不可调） | 让「授权自主」安全：放宽的那层不含致命动作，红线在不可调的地板 |
| hook 用命令解析而非子串正则 | 子串匹配会把 commit message 里的 `rm -rf` 误当命令拦——消除误伤同时不漏真实调用 |
| 分支感知 push（topic allow / main 需显式放行） | 日常不打断，同时推 main 即使在 bypass 下也需 human 明确 opt-in |
| `rm -r` 目标分级而非 blanket deny | blanket deny 会连清缓存都拦；分级让清理无摩擦、数据/产物仍守 |
| 大 bytes 只留 index | 可复现性靠 index+manifest，不靠把 GB 塞进 Git |
| `.reference-docs` 保留在 repo | doctrine 有版本、可 review；派生项目可保留或更新自己信奉的版本；覆盖说明单独记录，避免误读为逐字实现每个示例 |
| 不设通用 `docs/`，文档按角色分布 | 通用 docs 会引出「给 human 还是 agent / 规则还是地图」的归属歧义并造成两处写；四件套 + `.agent/` + `DESIGN.md` 已在源头分工（详见 `.agent/repo-documentation-topology.md`）。项目级长文用嵌套 `lab/docs/` |

决策变更应记入 `DECISIONS.md` → `human/decisions/`，并同步对应 doctrine/能力。

---

## 13. 从哪读起

- **human 想了解全局**：本文 → `README.md` → `ANATOMY.md`。
- **human 想上手协作**：`human/README.md` → `PROJECT.md` → `memory/current-status.md`。
- **agent 进 repo**：`AGENTS.md` → `.agent/AGENTS.md` → `memory/current-status.md` → 目标目录 `ANATOMY.md`。
- **想改治理/权限**：`.agent/action-boundary.md` + `.claude/settings.json` + `.codex/config.toml` / `.codex/rules` + `scripts/`（一起改）。

---

## 维护说明

本文随架构演进会过时。它是**地图不是源真相**：新增/删除 plane、改安全模型、改能力清单数量时同步本文；
细粒度规则（具体 allow 条目、每条 doctrine）以源文件为准，不在本文复制。校准点：§2 分层、§3 安全模型、§10 清单。

维护不靠人记：§10 清单表的 agents/skills/commands/hooks 数量由 `scripts/check-agent-harness.py` 校验，
与实际不符则告警（CI `--strict` 会红）；同步职责归 `repo-doc-steward`（见 `.agent/repo-documentation-topology.md`）。
