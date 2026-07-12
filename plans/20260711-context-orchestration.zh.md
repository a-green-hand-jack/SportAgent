# 主动上下文调配（context orchestration）交互式计划

> 这是 human 与 Claude Code 的协商界面：Claude 写初稿 → human 在「Human 批注区」批注 → Claude 读 diff、收敛 → 每次采纳的修订做一个小 commit。实现只在 scope / forbidden paths / verification 清楚后开始。
>
> 触发背景：GPT-5.6 在 Codex 里因窗口变大更容易越过 272K 长上下文计费线（全请求 2× 输入 / 1.5× 输出）。结论是**不硬限窗口**，而是靠"主动调配"把 context 稳在合适区间。本模板本就按 [gist optimization spirit](https://gist.github.com/a-green-hand-jack/c5ffc265f41763f2c58837e1a0b8b037) 建立，但"主动调配"那半边缺失。

## 当前目标

补齐让上下文"停在合适区间"的**主动调配链**，不硬限窗口。具体三块：

1. **statusline context 表** —— 让 context 占用可见（补上唯一缺的那块仪表盘）。
2. **阈值触发 hook** —— 跨过阈值时把"该 checkpoint / 考虑压缩"注入上下文，把主动压缩从"自觉"变成"信号驱动"。
3. **短上下文连续性 hook** —— compact/clear 后自动回注 `memory/current-status.md` 摘要，接续不断档。

本轮 scope：**只出方案文档**（human 已选）。不写实现代码。

## 非目标

- 不硬性设 `model_context_window` / auto-compact token 限制（那是降概率，不是调配，且损失能力）。
- 不改 Codex 侧 `~/.codex/config.toml`（本模板管的是 Claude Code harness）。
- 不改现有 `pre_tool_guard.py` 的安全边界逻辑。
- 不引入第三方依赖（hook 保持零依赖、可审计）。

## Branch / worktree

- 建议分支：`feat/context-orchestration`（topic 分支，push 走 allow）。
- 本轮只写 `plans/`，可直接在 `main` 上做 doc commit，或等实现阶段再开分支。待批注。

## Linked issue / PR

- 待定。若认为该能力应回流上游 template，可走 `template-feedback` skill 开 `from-downstream` issue。

## Allowed paths（实现阶段）

- `.claude/statusline.sh`
- `.claude/hooks/`（新增 hook + `README.md`）
- `.claude/settings.json`（注册 hook）
- `.agent/`（若需补 principle / checklist）
- `scripts/validate-governance.py` 或 `check-agent-harness.py`（若要把新 hook 纳入校验）
- `plans/`（本文件）

## Forbidden paths

- `lab/data/**`、`lab/runs/**`、`lab/models/**`、`checkpoints/**`、`wandb/**`、`lab/infra/private/**`
- 任何远端产物 / 长训练作业

## 诊断（为什么现在"看不到压缩被触发"）

现有 context 相关机制（`settings.json` 已注册）：

| 机制 | 触发时机 | 局限 |
|---|---|---|
| `pre_compact_memory_check.py` | **PreCompact**：压缩真发生的那一刻 | 反应式、末端、仅提醒(exit 0)。不撞 auto-compact / 不手动 `/compact` 就永不 fire。 |
| `checkpoint-writer` / `session-boundary-agent` subagent | 主 agent 主动调用时 | 没有信号"戳"主 agent 去调，于是从不主动派。 |
| `statusline.sh` | 每次刷新 | 显示 model/dir/branch/worktree/**cost**，**唯独没有 context 占用%**。 |

**根因**：gist #4/#16 与 `.agent/principles.md`「没有仪表盘就别开长途」要求阈值仪表盘 + 阈值触发，但**仪表盘上恰恰缺 context 那块表** → 主 agent 和人都感知不到临界点 → 没人主动派 checkpoint/boundary → 只剩 auto-compact 末端那一下。整条"主动调配"链断在最前端。

对照 gist 18 条：已落地 = repo 控制面(#1-3)、report 隔离(#8)、worktree 所有权(#9)、anatomy(#13)、PreToolUse guard(#14)、validator(#15)、artifact 索引(#17)、model/effort 分级(#18)、checkpoint/boundary/session-tree 的 subagent 本身(#5/#10/#11)。**缺 = #4/#16 的阈值仪表盘与触发点，以及短上下文连续性回注。**

### Codex 复核补充（2026-07-11）

Codex 独立查了一遍，确认「配置存在、`validate-governance.py --strict` 通过，但没有常驻自动压缩守护」，并补了两条我原稿没覆盖的关键约束：

- **硬约束：repo hook 只能发信号，不能可靠替你按 `/compact`。** `PreCompact` 只在宿主 agent 真的进入 compact lifecycle 时才触发；它不会自己监控 token 到 60/70% 然后自动压缩。`pre_compact_memory_check.py` 永远 `exit 0`、只提醒，不会自动调 `checkpoint-writer` 也不会执行 compact。`session-boundary-agent` 同理——没有任何 hook 在每轮 turn 后自动启动它，除非主 agent 遵守协议或人显式说 `Use $session-boundary-control before continuing`。**真正"按下 compact"要宿主 CLI 支持；本方案三块的定位因此全部是"信号/提示"，不是"自动执行"。**
- **运行表面不等价（surface parity）。** `.codex/config.toml` 已确认挂了对等的 `PreCompact` / `PreToolUse` / `PostToolUse` / `SubagentStop`（同样指向 `.claude/hooks/*.py`），所以 Claude 与 Codex 两个表面对齐。但**实际是否触发取决于运行表面**：Claude 要信任 `.claude/settings.json`、Codex 要信任 `.codex/config.toml`；Paseo 启动的 agent 是否继承这些 hook，取决于 provider / mode / cwd / worktree、以及它是否以真正的 project session 启动。已知 `~/.paseo/config.json` 的 `mcp.injectIntoAgents = false`，Paseo 启动的 agent 默认不自动拿到编排能力。→ 这解释了"看不到触发"的另一半：不只是机制被动，某些表面下 hook 根本没接上。

**一句话**：现状是"compact 前提醒 + 人/主 agent 主动调用边界 subagent"，不是"后台自动压缩系统"。本方案不试图违背这条硬约束去"自动 compact"，而是把**信号做强、做可见、做早**，让主动压缩有据可依。

## 探测结果（2026-07-11，回答未决问题 1）

实测本 session 的 transcript JSONL（`~/.claude/projects/<slug>/<session>.jsonl`）：

- **确定：context 占用有精确来源，不用字符估算。** 每条 assistant message 的 `message.usage` 含 `input_tokens` + `cache_read_input_tokens` + `cache_creation_input_tokens`，三者之和 = 当前上下文精确 token 数（实测某条 = 71,883 tokens）。读 transcript 最后一条 assistant usage 求和即可，零依赖、精确。
- **statusline 自身 stdin 字段**：临时 probe 跨一整个回合仍未捕获 → 本 session 表面根本没调用 statusline（probe 已移除，statusline.sh 复原）。按 Claude Code 官方 statusline schema，stdin 含 `session_id` / `transcript_path` / `cwd` / `model{id,display_name}` / `workspace{current_dir,project_dir}` / `version` / `output_style` / `cost{...}` / `exceeds_200k_tokens`(bool)——**给 `transcript_path`，不给精确 token 计数**。故块 1 走 `transcript_path` 读 usage 求和；`exceeds_200k_tokens` 可作 200k 窗口的兜底信号。此项**不阻塞**。
- **结论**：块 1/2 的 token 来源从"字符/4 近似"**升级为 transcript usage 精确值**。窗口大小按 model 取（Opus 4.8 [1m] = 1,000,000；常规 200k），可用 `CLAUDE_CTX_WINDOW` 覆盖。

## Paseo 表面（2026-07-11，回答未决问题 5，已改配置）

- `~/.paseo/config.json` 已改（备份 `~/.paseo/config.json.bak-20260711`）：
  - `daemon.mcp.injectIntoAgents`: `false → true`（Paseo agent 拿到 Paseo MCP，可自我编排/参与上下文调配）
  - `daemon.enableTerminalAgentHooks`: `false → true`（Paseo 给终端 agent 挂生命周期 hook 回调；印证于 `paseo hooks <agent> <event>` 子命令存在）
- **注意**：改动需 `paseo daemon restart` 才生效（本次未重启——需 human 授权）。
- **仍成立的边界**：Paseo 的这两个开关控的是 Paseo 自己的 MCP/hook 注入，不等同于子 CLI 是否 honor 项目 `.claude/settings.json` / `.codex/config.toml` hook——后者取决于 Paseo 是否以真正的 project session、在受信任 cwd/worktree 启动。因此方案覆盖面仍应声明"以 Claude/Codex project session 表面为准"，Paseo 表面靠这两个开关尽量对齐、但不保证逐一等价。

## 发版路径（2026-07-11，回答未决问题 4：回流 template）

我们**就在 template repo 里**，所以这不是"下游回流"，而是 `template-versioning-policy.md` 的 **②b 模板源（template → template）**：

- **不用 `template-feedback` skill**（它是下游专用，②a）。直接在本 repo 开发（可选打 `template-native` 标签的 issue）→ issue→PR→merge。
- **判级 = MINOR**：三块是"新增 agent/skill/hook/validator、向后兼容、sync 干净落地、下游净得能力"，正落 semver 表的 MINOR 行。merge 后跑 `python scripts/bump-template-version.py --level minor` 写 `VERSION` + 打 tag。
- **必须登记进 `template-manifest.toml` 框架层**：新 hook（threshold / continuity）、statusline 改动、settings.json 的 hook 注册要归到框架层受管路径，否则 `template-sync.py` 不会把它们同步到下游——等于下游拿不到这个能力。这是本方案能"惠及所有下游"的关键一步，实现时不能漏。
- 混合文件（如 `.claude/settings.json`、statusline.sh 若被 manifest 判为混合）要遵守 `fb70fb1` 引入的哨兵结构（`template:begin/end` 块），改动只动模板拥有的块。

## 过渡缓解（实现前立即可用，来自 Codex 建议）

在长任务开头固定加一句提示，把"主动调配"从模型自觉临时抬成显式协议：

```text
每完成一个阶段或 context 变长时，先运行 $session-boundary-control；
若建议 compact/clear/handoff，先用 checkpoint-writer 更新 memory/current-status.md。
```

这不需要任何代码改动，是三块 hook 落地前的 stopgap。三块做的事，本质就是把这句话从"人每次记得贴"变成"仪表盘可见 + 阈值自动注入"。

## 方案细节（三块）

> 定位统一：三块都是**信号/提示**层，不试图自动执行 `/compact`（见 Codex 硬约束）。目标是让主动压缩"看得见、提醒得早、有据可依"，最终按下 compact 的仍是宿主 CLI + 主 agent 的判断。

### 块 1：statusline context 表（最高杠杆）

- **做什么**：`statusline.sh` 增一段，从 stdin JSON 的 `transcript_path` 读当前 session transcript，估算已用 token，换算成占窗口百分比，拼进现有 ` | ` 面板。
- **估算法（已由探测确定）**：读 transcript 最后一条 assistant message 的 `message.usage`，取 `input_tokens + cache_read_input_tokens + cache_creation_input_tokens` = 精确上下文 token（非字符近似）。窗口大小可配 `CLAUDE_CTX_WINDOW`，默认按 model（[1m]=1e6 / 常规=2e5）。
- **展示**：`🧠 62%`；≥65% 黄、≥80% 红（终端色码，无色环境降级为 `[!]` 前缀）。
- **降级**：无 `jq`、无 transcript、解析失败 → 不显示这段，绝不报错阻断（沿用现有防御式风格）。
- **对应精神**：#4/#16「没有仪表盘就别开长途」。
- **未决**：token 估算精度 vs 复杂度；是否读官方 token 字段（需确认 statusline JSON 到底给不给 token 计数——见「未解决问题」）。

### 块 2：阈值触发 hook（把主动压缩变信号驱动）

- **事件**：`UserPromptSubmit`（每轮用户输入时触发，能向上下文注入文本）。
- **做什么**：读同一 transcript 估算占用；跨阈值时 `stderr`/stdout 注入建议，例如：
  - ≥65%：`[context] 已用 ~67%。建议：派 checkpoint-writer 落盘 current-status.md；接近任务边界可考虑 /compact。`
  - ≥80%：升级措辞为"现在就 checkpoint 并 compact/clear"。
- **纪律**：纯建议（不 block、不自动 compact）——压缩时机仍由主 agent 在任务边界判断，hook 只提供信号。避免每轮刷屏：同一 session 内每档阈值只提醒一次（用 transcript 目录旁的 marker 文件去重）。
- **对应精神**：#4/#16 阈值操作、#5 在任务边界主动压缩。
- **未决**：阈值数值（60/75 还是 65/80）；去重 marker 放哪（`.omc/` 已是忽略产物区，或 transcript 同目录）。

### 块 3：短上下文连续性 hook（你提的第一个点）

- **事件**：`SessionStart`，`source ∈ {compact, clear}`（Claude Code 会在 compact/clear 后以该 source 触发 SessionStart）。
- **做什么**：读 `memory/current-status.md`，把其摘要（objective / 最近决策 / changed files / next steps）注入新上下文开头，让压缩/清空后立刻恢复"我在干什么、下一步"，不断档。
- **配合 PreCompact**：`pre_compact_memory_check.py` 保证压缩前 status 已落盘（提醒）；本 hook 保证压缩后 status 被读回。一前一后闭环。
- **对应精神**：#5 compact 前更新 status、#11 handoff 文档、你说的「优化短上下文连续性」。
- **未决**：是否只在 status 文件"新鲜"时回注（旧的可能误导）；注入长度上限（避免回注本身吃掉太多 context）。

## 任务树（实现阶段——三块**并行**，human 已定）

抽一个公共 `context_usage.py` helper（读 transcript_path → usage 三项求和 → 百分比），块 1/2 共用；三块之间无顺序依赖，可并行落地。

- [x] 公共 helper：`context_usage.py`（transcript → 精确 token% + 窗口按 model/`CLAUDE_CTX_WINDOW`）— commit `a5435c6`
- [x] 块 1 statusline context 表（🧠 NN%，≥65% 黄 / ≥80% 红）— `a5435c6`
- [x] 块 2 UserPromptSubmit 阈值 hook（65/80 注入建议，每档去重）— `a5435c6`
- [x] 块 3 SessionStart(compact/clear) 连续性回注 hook — `a5435c6`
- [x] 收口：`.claude/hooks/README.md` hook 表 + `settings.json` 注册（Claude 表面）+ DESIGN.md §10 hooks 5→8
- [x] `.codex/config.toml` 对等（commit `a0c1435`）：确认 Codex 支持 UserPromptSubmit（~/.codex 全局 hooks 佐证）；压缩走独立 PostCompact（SessionStart matcher 只含 startup|resume|clear）→ 注册 UserPromptSubmit + SessionStart(clear) + PostCompact，continuity hook 内认 PostCompact。
- [x] 窗口感知（点1，commit `a0c1435`）：CLAUDE_CTX_WINDOW > 会话窗口缓存（statusline 从 model.id 认出写、hook 读）> model > 证据推断 > 200k。解决 1M session hook 早报警。
- [x] manifest：新 hook 落 `.claude/hooks/**` 自动归框架层，无需改 `template-manifest.toml`。
- [x] fresh reviewer 审查（code-reviewer，结论 COMMENT，无 CRITICAL/HIGH）→ 4 项发现全修，commit `22356e1`。
- [ ] 发版收口：`bump-template-version.py --level minor`（**merge 到 main 后再做**，避免在 feature 分支打 tag）。
- [x] 走 PR（human 已批准提交）→ 待 review/merge → 发版 → sync 下游。

### reviewer 发现与处置（commit `22356e1`）
- [MEDIUM] 非 dict 的合法 JSON 行 → `obj.get` 抛 AttributeError 冒泡，破坏「绝不抛异常」契约 → 加 `isinstance(obj,dict)` 守卫（按 reviewer 复现验证 exit=0）。
- [MEDIUM] percent() 默认 200k 路径全量读 transcript 两遍 → 合并 `_scan_transcript` 单遍。
- [LOW] 删未用 `import os`；[LOW] `_colorize` docstring 对齐实现。
- 一致性/边界/去重升级/statusline 降级等项 reviewer 已核对无误。

## Human 批注区

> 在这里批注：改优先级、调阈值、砍某块、加约束。我读 diff 后收敛。

## 当前决策

- 不硬限窗口，走主动调配。（human 已定）
- 本轮只出方案文档，不写实现。（human 已选）
- token 来源 = transcript 最后一条 usage 的三项求和（精确），非字符近似。（探测已定，见「探测结果」）
- 三块定位为"信号/提示"，不追求 hook 自动执行 compact（Codex 硬约束：按下 compact 需宿主 CLI）。（复核已定）
- Paseo 两开关已置 true（injectIntoAgents / enableTerminalAgentHooks），**由 human 稍后手动 `paseo daemon restart` 生效**（本次不重启，human 还有任务在跑）。
- **阈值 = 65 / 80**（黄 / 红）。（human 已定）
- **三块并行落地**，共用 `context_usage.py` helper。（human 已定）
- 发版走 **②b 模板源 → MINOR bump**，不用 template-feedback skill；新能力须登记 manifest 框架层。（human 已定"回流 template"，据 policy 定型）
- 本文件所在分支：`feat/context-orchestration`（已从 `main` 拉出，不含 template-upstream-sync 的改动）。

## 未解决问题

1. ~~token 来源~~ → 已探测：transcript usage 精确；statusline 给 transcript_path 不给 token 计数。**已定**。
2. ~~阈值~~ → **65 / 80**。**已定**。
3. ~~落地顺序~~ → **并行**（共用 helper）。**已定**。
4. ~~回流 template~~ → **②b 模板源 → MINOR bump + manifest 登记**，不用 template-feedback。**已定**。
5. ~~Paseo 表面~~ → 已改配置（待 human 手动 restart）。

**剩余仅一处待批注**：是否接受方案中"覆盖面以 Claude/Codex project session 为准、Paseo 靠两开关尽量对齐但不保证逐一等价"的声明？（默认接受，除非批注否决）

## 验证标准（实现阶段）

- 块 1：构造含 `transcript_path` 的假 JSON 喂 `statusline.sh`，输出含 `🧠 NN%` 且颜色随阈值变；无 transcript 时优雅降级。
- 块 2：喂高/低占用 transcript，验证跨阈值注入、同档只提醒一次。
- 块 3：模拟 `source=compact` 的 SessionStart，验证 status 摘要被注入。
- 全局：`python scripts/validate-governance.py` 通过；hook 零依赖；受保护路径边界不变。

## 下一步

- 等 human 在批注区落笔（尤其"未解决问题 1/2/3"）。
- 批注收敛后：确认是否进入实现阶段、是否开 `feat/context-orchestration` 分支。

## Plan revision log

- 2026-07-11 初稿（诊断 + 三块方案 + 未决问题）
- 2026-07-11 并入 Codex 复核（硬约束：hook 只发信号不执行 compact；运行表面不等价 / Paseo injectIntoAgents=false；.codex 侧 hook 对等已确认）+ 过渡缓解句 + 未决问题 5
- 2026-07-11 探测：确认 transcript usage 提供精确 token（块 1/2 改用精确值）；statusline 自身字段待回合边界 probe。改 Paseo 配置（injectIntoAgents / enableTerminalAgentHooks → true，待 restart）。收敛未决问题 1、5。
- 2026-07-11 human 定调：阈值 65/80、三块并行（共用 helper）、发版走 ②b 模板源 MINOR bump + manifest 登记（不用 template-feedback skill）；statusline probe 未捕获（本 session 未调用 statusline）已移除、改用官方 schema 记录；分支 rebase 到最新 main（含模板发版基建）。未决问题收敛至仅 1 处（Paseo 覆盖面声明，human 已接受）。
- 2026-07-11 实现落地 commit `a5435c6`：三块 + 共用 helper + statusline + settings 注册 + DESIGN/README。全部 validator（governance/harness/anatomy/codex-adapters）OK，定向测试通过。发现并处理一个真 bug 方向：hook stdin 无 model、transcript 只存 base id（无 `[1m]`）→ 1M session 会按 200k 早报警；定为安全方向 + `CLAUDE_CTX_WINDOW` 覆盖 + 文档说明。已派 fresh code-reviewer 审查（作者/审查分离）。
- 2026-07-11 reviewer 结论 COMMENT（无 CRITICAL/HIGH）；4 项发现（2 MEDIUM + 2 LOW）全修 commit `22356e1`，复测 + validator 全绿。**实运行确认**：本 session settings.json 生效后 UserPromptSubmit hook 已真实触发（1M session 按 200k 报 ~76-83%，印证 CLAUDE_CTX_WINDOW 提示的必要）。
- 2026-07-11 补点1（窗口感知）+ 点2（Codex 对等），commit `a0c1435`。窗口链：env > 会话缓存（statusline 写/hook 读）> model > 证据 > 200k，实测 hook 读 1M 缓存后 100%→16% 静默。Codex 查证支持 UserPromptSubmit + PostCompact，.codex/config.toml 注册对等。human 批准提交 PR。
- 2026-07-11 PR #10 开。诊断 statusline 感知：本 session UI 未渲染 statusline（故 hook 一直按 200k 报警），机制本身验证可用，已手动 prime 本 session 窗口缓存；正常交互 session statusline 持续渲染自动做此事。
- 2026-07-11 PR 合并前 fresh 复审（code-reviewer，COMMENT，无 CRITICAL/HIGH），3 项发现全修 commit `1e155e7`：①[MEDIUM] 缓存粘滞——statusline 改绕过缓存以本帧 model 为准再刷新；②[LOW] 缓存原子写 os.replace；③[LOW] 两 hook 顶层 stdin dict 守卫。回归 + validator 全绿，复审结论已贴 PR。剩余仅 human merge → `bump-template-version.py --level minor` 发版。
