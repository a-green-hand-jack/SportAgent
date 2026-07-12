# Agent 身份/命名 + 更易唤起 subagent —— 交互式计划

> 这是 human 与 Claude Code 的协商界面：Claude 写初稿 → human 在「Human 批注区」批注 → Claude 读 diff、收敛 → 每次采纳的修订做一个小 commit。实现只在 scope / forbidden paths / verification 清楚后开始。
>
> 触发背景：human 用 Paseo 多 agent 并行工作，每个「标签页」≈ 一个需与 human 交互的 agent。痛点：①Paseo 自动用「开场 prompt 前缀」命名 → 标签列表全是噪音（实测：`终于知道codex5.6额度不耐用的原因了`、`".claude/worktrees/...` 这类）；②唤起 subagent 不够方便。

## 当前目标

给模板加两件互相咬合的能力（**信号/工具层，不改 Paseo 运行时**）：

1. **Agent 身份/命名**：让每个 agent 有一个人类可读、能一眼看出「在做什么」的名字，供 human↔agent 与 agent↔agent 交流。
2. **更易唤起 subagent**：发现有哪些能 agent、一键配好 launch packet、in-session 与 Paseo tab 两种 spawn 都更顺。

## 非目标

- 不重造 Paseo 已有的命名/消息机制（`--title`/`rename`/`send`/`label`/`PASEO_AGENT_ID` 都已存在）。
- 不硬耦合 Paseo：身份层 runtime-agnostic（identity 文件 + statusline + roster 在纯 Claude/Codex 也可用），Paseo 只是可选 adapter。
- 不在本轮写实现代码（先出计划 + 定 doctrine，等批注）。

## 已探明的 Paseo 能力（设计地基，已实测）

| 能力 | 命令/事实 | 用途 |
| --- | --- | --- |
| 启动带名 | `paseo run --title <name>` / `--label k=v` / `--worktree <name>` | launcher 出生即命名 |
| 自知 id | 环境变量 **`PASEO_AGENT_ID`** 注入 + `paseo whoami`/`self`/`me` | agent 自我重命名前拿到自己的 id |
| 自我改名 | `paseo rename <id> <name>`（另有 `edit`/`set`/`label`） | 缺省自命名可修好标签列表 |
| agent 间发消息 | `paseo send <id|prefix> <prompt>`（**按 id，不按 name**） | 故需 roster 做 name→id 解析 |
| 现成 roster 字段 | `paseo ls --json`：`id/shortId/name/cwd/status/thinking/provider/created` | 大半 roster 列白送，只补语义层 |

## 决策（已定，human 逐条确认）

- **命名方案 = `<persona>·<动作字>·<focus>`**（human 已定，喜欢 `师爷·审·窗口感知` 这种）。persona 给角色人格 + 动作字给显式动词 + focus 给话题 → 三段一眼读出「谁·在做什么·对什么」。
- **获取方式 = 混合**：launcher/human `--title` 优先；缺省则 agent 首轮按 doctrine 自命名并 `paseo rename "$PASEO_AGENT_ID"` + 写 identity 文件 + 注册 roster。
- **agent↔agent = 命名 + roster（name→id）+ 复用 `paseo send`**，不内建消息板。
- **roster = 新建 `memory/agents-roster.md`**（活 agent、易变），与 `memory/session-tree.md`（任务血缘、持久）分开。
- **分阶段实现**（见下）。

## Doctrine 草案：persona ↔ 动作映射（`.agent/agent-identity.md`）

> 名字 = `<persona>·<动作字>·<focus>`。persona 给角色人格、动作字给显式动词、focus 给话题。`师爷·审·窗口感知`＝「师爷（把关者）·审（审查）·窗口感知（话题）」。

| 做什么 (action) | persona | 动作字 | 覆盖的 template agent 家族 | 示例名 |
| --- | --- | --- | --- | --- |
| 调查/侦察 investigate | **斥候** | 查 | explore · repo-researcher · tracer · debugger · document-specialist | `斥候·查·codex额度` |
| 改代码/实现 build | **干将** | 改 | executor · feature-worker · code-simplifier | `干将·改·auth重构` |
| 审查/把关 review | **师爷** | 审 | code-reviewer · critic · verifier · security-reviewer · zh-review-gate | `师爷·审·窗口感知` |
| 规划/统筹 plan/coordinate | **都督** | 统 | planner · architect · analyst · interactive-plan-writer（含「协调」） | `都督·统·发版` |
| 记录/文档 document | **主簿** | 记 | repo-doc-steward · checkpoint-writer · writer · artifact-librarian | `主簿·记·anatomy` |
| 测试 test | **巡检** | 测 | test-engineer · test-runner · qa-tester | `巡检·测·e2e` |
| 实验/数据 experiment | **博士** | 验 | scientist · experiment-orchestrator · experiment-monitor | `博士·验·CFD数据` |
| 设计 design | **画师** | 设 | designer | `画师·设·登录页` |
| git/整合 integrate | **校书** | 并 | git-master（校书郎＝校勘/合并版本，贴合 merge/rebase） | `校书·并·main合流` |

> 新增（批注 Q1）：**画师**（设计，从 build 拆出）、**校书**（git/整合）。「协调」并入 **都督**（batch Q1 注：都督已含）。

规则：
- **唯一性**：同 persona 多开靠 focus 区分（`师爷·审·窗口感知` vs `师爷·审·codex`）；roster 冲突则追加短 id。
- **生命周期**：agent 结束/归档时 roster 标 done（不立即删，留痕）。

## 分阶段实现（每阶段独立可用）

### Phase 1 —— 身份可见（最快见效）
- `.agent/agent-identity.md` doctrine（上表 + 规则）。
- **statusline 加 `🤖 <name>` 段**（复用已建的 gauge 管线；读 identity 文件 / `AGENT_NAME` env / `paseo whoami`）。
- identity 来源文件（如 worktree 内 `.agent-identity`，gitignore）。
- 产出：human 一眼分清每个 tab 在做什么。

### Phase 2 —— 自命名 + roster + 自知
- 首轮**自命名（默认开启，human 已定 = 选项 A）**：无 `--title`/无 `AGENT_NAME` 时按 doctrine 生成名 → **默认自动** `paseo rename "$PASEO_AGENT_ID" <name>`（彻底清理垃圾 tab 名）+ 写 `.agent-identity` + 注册 `memory/agents-roster.md`。
  - 触发一次即止（写了 `.agent-identity` 后不重复 rename）。
  - 无 `PASEO_AGENT_ID`（非 Paseo 表面）→ 跳过 rename，仅写文件 + roster（runtime-agnostic）。
  - kill switch：留一个 env（如 `AGENT_NO_AUTORENAME=1`）给个别不想自动改名的场景，但默认关（即默认会 rename）。
- **roster** `memory/agents-roster.md`：`name | persona/action | focus | branch/worktree | paseo-id | status | updated`；字段大半取自 `paseo ls --json` + 语义层。
- **自知 hook**：SessionStart 注入「你是 <name>，动作=审查，focus=…」（扩展已建的 continuity hook），compact 后不失忆。
- 维护者：复用/扩展 `branch-reporter` / `session-boundary-agent`。

### Phase 3 —— 更易唤起 subagent（**做成 skill**，批注 Q4）
human 已定：不做成一键 command，而是 **skill**——交互式流程：human 启动 skill → 交代意图 → main-agent 补充它要交代的事 → 再启动 subagent 去干。skill 更可编排、留出「两层交代」的空间。

`spawn` skill 内部串起（覆盖 human 提的 4 类不便）：
- **发现**：列 `.claude/agents/*.md` frontmatter（name/一句话/触发词/tier）——解决「不知道有哪些能 agent」。
- **选型 + packet**：`subagent-router-agent` 选 agent+model+effort+tools+边界+停止条件——解决「配置繁琐」。
- **两层交代**：human brief + main-agent brief 合成最终 launch prompt——解决「步骤多」但保留人/主 agent 的意图注入。
- **两种 spawn**：
  - in-session 子 agent（跑完汇报）；
  - **Paseo-tab launcher（keystone）**：`paseo run --title <doctrine名> --worktree … <profile>` → 持久可交互、出生即好名 + 入 roster。

> keystone 洞察：**launcher 是两个目标的交汇点**——起 Paseo agent 时顺手 `--title` 好名 + 建 worktree + 选 profile + 入 roster，命名与易唤起一次解决；把命名从源头做对（比事后 rename 更干净）。

### 框架层 vs 运行时（批注 Q3 —— identity 作为 template 一部分、下游继承）
| 层 | 内容 | 归属 | 下游是否继承 |
| --- | --- | --- | --- |
| **框架层（=template，随 sync 继承，正如 `.agent/`/`.claude/`）** | `.agent/agent-identity.md` doctrine + persona 表、statusline `🤖` 段、自命名/自知 hook、`spawn` skill、roster **模板/表头** | `.agent/**` `.claude/**`（manifest 已归 framework） | ✅ 是 |
| **运行时（每 agent/每 project 私有，不继承、不 sync）** | 某个活 agent 的**当前名字值**、`memory/agents-roster.md` 的**具体内容** | 名字值来自 `paseo whoami`/`AGENT_NAME` env（gitignore 兜底文件）；roster 内容在 `memory/**`（manifest 已归 **project**） | ❌ 否（各 project 各自的活 agent，不该混） |

→ 所以「identity 作为 template 一部分、下游继承」= **doctrine + 机制进框架层**（和 `.agent/`/`.claude/` 完全一样，随 `template-sync` 落到每个下游）；唯一不继承的是**具体某个活 agent 的名字值**（那是运行时状态，每个 agent 不同，不是模板产物）。

## 任务树（供批注确认拆分）
- [x] Phase 1：doctrine + statusline `🤖` 段 + `agent_identity.py` + gitignore（commit `84d428f`；fresh review 进行中）
- [x] Phase 2：自命名（`paseo agent update --name`，默认开启）+ `memory/agents-roster.md`（gitignore）+ 自知 hook（commit `1ec62fd`；fresh review 进行中）。注：实测 `paseo rename` 不存在，正确命令是 `paseo agent update <id> --name`。
- [x] Phase 3：`spawn` **skill**（发现 `list_agents.py` + 选型/packet(subagent-routing) + 两层交代 + in-session/Paseo-tab launcher；`agent_name_set.py --register` 登记子 agent）——commit `f4dcd80`（`feat/agent-spawn`）；validators 全绿；fresh review 进行中。keystone：`paseo run --title + --env AGENT_NAME + --worktree` 出生即双表面命名。
- [ ] 各阶段：validator 通过 + `.claude/hooks/README`/`DESIGN.md §10` 同步 + manifest 归类
- [ ] 走 PR（human gate）→ merge → 发版（新增能力 = MINOR）

## Human 批注区

> 在这里批注：persona 集合改字（斥候/干将/师爷/都督/主簿/巡检/博士 是否满意、要不要加/减）、是否要「动作 tag 更显式」那个可选项、Phase 顺序、roster 字段。

## 当前决策（批注后已收敛）
- 名字格式 = **`<persona>·<动作字>·<focus>`**（batch Q2 采纳）。
- persona 集合 = 9 个：斥候/干将/师爷/都督/主簿/巡检/博士 + 新增 **画师**(设计)、**校书**(git/整合)；「协调」并入都督（batch Q1）。
- 获取 = 混合（launcher/`--title` 优先，缺省自命名 `paseo rename "$PASEO_AGENT_ID"`）。
- agent↔agent = 命名 + roster(name→id) + `paseo send`。
- **框架层 vs 运行时**已厘清（batch Q3）：doctrine+机制进框架层随下游继承；活 agent 名字值/roster 内容是运行时、不继承。
- Phase 3 spawn = **skill**（batch Q4，human→main-agent 两层交代后再起 subagent）。
- **Phase 2 自命名默认开启（选项 A）**：agent 启动后自动 `paseo rename` 清理垃圾名（human 已定）；非 Paseo 表面跳过 rename，留 `AGENT_NO_AUTORENAME` kill switch。

## 待最终确认（仅 2 处小项）
1. 新增两 persona 的**具体用字**：设计→**画师**、git/整合→**校书**（校书郎＝校勘合并版本）。认可否？想换字（如设计→图师/匠作；git→编修/总管）就在此改。
2. 框架/运行时那张表（batch Q3 的落地）是否如你意——即「doctrine+机制继承、活 agent 名字值不继承」。

（原 Q2/Q4 已由批注定案，见「当前决策」。）
## 验证标准（实现阶段）
- Phase 1：喂含 name 的场景，statusline 显示 `🤖 <name>`；无 name 优雅降级。
- Phase 2：模拟无 `--title` 启动 → agent 自命名、`paseo rename` 生效（标签列表变干净）、roster 出现该行；compact 后自知注入。
- Phase 3：`/agents` 列全；`/spawn` 一步起对 agent；launcher 起的 Paseo tab 出生即好名 + 入 roster。
- 全局：`validate-governance` 通过；runtime-agnostic（无 Paseo 时身份层仍工作）。

## 下一步
- 等 human 批注 persona 集合 + 未解决问题 1-4。
- 敲定后：确认从 Phase 1 起，开 `feat/agent-identity` 分支实现。

## Plan revision log
- 2026-07-12 初稿（Paseo 能力探明 + persona↔动作 doctrine + 三阶段 + 4 决策已定）
- 2026-07-12 收敛 human 批注 Q1-Q4：格式改 `persona·动作字·focus`；persona 加 画师/校书（协调并入都督）；framework/runtime 分层表（doctrine 继承、活名字值不继承）；Phase 3 定为 skill（两层交代）。仅剩 2 处小确认（新 persona 用字、分层表认可）。
- 2026-07-12 Phase 1 落地 commit `84d428f`（doctrine + statusline 🤖 + agent_identity.py + gitignore + DESIGN/README）；validator 全绿、定向测试通过；派 fresh code-reviewer 审查。human 定 Phase 2 自命名**默认开启**（选项 A：自动 paseo rename 清垃圾名）。
- 2026-07-12 Phase 1+2 两轮 fresh review 全修，PR #20 merged，发版 **v1.2.0**（MINOR）；live demo 把本标签页重命名为 `都督·统·模板演进`。
- 2026-07-12 Phase 3 落地 commit `f4dcd80`（`feat/agent-spawn`）：`spawn` skill + `list_agents.py` 发现助手 + `agent_name_set.py --register`（launcher 登记子 agent）；DESIGN §10 Skills 12→13 / Codex 20→21 skills；Codex 适配器已生成；validators 全绿。派 fresh code-reviewer 审查（重点：register 回归、frontmatter 解析、launcher 命令可跑）。human 定：下游 DOLoop#107/pairwise-diffusion#62 暂不追平。
- 2026-07-12 Phase 3 fresh review 结论 **APPROVE**（无 CRITICAL/HIGH/MEDIUM）；折叠 2 开放问题 + 2 LOW（commit `742bc9e`）：launcher 加 `--detach`、id 提取兼容 `{id}`/`{agent:{id}}` 两形状、register 空 pid 拒绝、frontmatter 单行假设写明。复测全过、codex 0 drift、governance 0/0。**待 human：PR → merge → 发版（v1.2.0→v1.3.0 MINOR）。**
