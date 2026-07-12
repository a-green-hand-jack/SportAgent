---
title: "Claude Code 优化精神"
category: "agent-workflows"
tags:
  - claude-code
  - coding-agents
  - repo-control
  - anatomy
status: "imported"
source: "github-gist"
---
# Claude Code 优化精神

面向 AI PhD Student 的 agentic research operating philosophy

版本：2026-07-05  
状态：gist 草稿  
适用对象：主要使用 Claude Code 做机器学习研究、代码复现、实验迭代、论文写作和多 repo 协作的人。

---

## 0. 一句话

Claude Code 不是一个更会写代码的聊天窗口，而是一套带文件系统、shell、权限、记忆、subagent、hooks、worktree 和 session 管理的研究执行环境。

优化 Claude Code 的核心，不是让它“更努力”，而是让它在正确的边界里工作：

```text
短上下文做当前判断，
repo 文件做长期控制面，
subagent 做隔离任务，
worktree 做并行边界，
hook/permission 做硬约束，
anatomy/ledger/validator 做防漂移机制，
测试和实验记录做事实来源。
```

如果你是 AI PhD student，Claude Code 最好的角色不是“替你想一切”，而是一个可编排的研究助手群：它能读代码、写脚本、跑测试、整理实验、改论文，但你必须把研究问题、证据标准、状态边界和失败恢复机制设计进 repo，而不是只留在聊天里或 user 全局配置里。

---

## 1. 这个文档解决什么问题

本文不是 Claude Code 配置指南，也不是 subagent 模板集合。它回答更上层的问题：

- 为什么 Claude Code 容易在长 session 里变贵、变慢、变糊？
- 为什么 multi-agent workflow 有用，但也容易失控？
- 为什么 `CLAUDE.md`、skills、subagents、hooks、worktrees、statusline 应该分工，而不是混成一团？
- AI PhD student 应该如何把 Claude Code 当成科研工作流的一部分，而不是一个临时聊天助手？

配套实践文档见：

```text
claude_code_practice_for_ai_phd_zh.md
```

---

## 2. 信息来源与置信度

本文综合了三类来源：

- 官方稳定机制：Claude Code docs，包括 best practices、subagents、skills、hooks、settings、statusline、worktrees、checkpointing、sessions、costs。
- 官方 blog / engineering posts：关于 autonomous Claude Code、auto mode、context engineering、multi-agent research system、产品质量 postmortem 等。
- 社区经验：Reddit、Hacker News、GitHub issues/discussions、个人博客。社区材料只当作“使用者痛点和边界条件”，不当作产品保证。

重要限制：

- Claude Code 更新很快。写作日期是 2026-07-05，使用前应运行 `claude --version` 并核对官方 docs。
- 官方文档推荐 `claude -p` 作为 non-interactive path，但本工作流明确不把它作为常规建议，因为用户指出它可能走 API token / usage credit 路径，不符合当前预算策略。
- 社区对 subagents、worktrees、hooks、ccusage 的评价有分歧。本文把它们当作“有用但会漏水的工程部件”，而不是魔法。

---

## 3. 核心精神

### 3.1 Context 是工作记忆，不是档案馆

Claude Code 的每一轮都要处理当前上下文。上下文越长，后续每一步越贵，也越容易被旧决策、旧日志、失败尝试和无关工具输出污染。

官方成本文档明确说 token cost 会随上下文规模增长，并建议主动使用 `/usage`、status line、`/clear`、`/compact`、模型选择和 effort 调整来控制成本。Anthropic 的 context engineering 文章也强调，agent 应该用文件路径、查询、链接等轻量引用来按需取用信息，而不是把所有内容一次性塞进 prompt。

所以，Claude Code 的第一原则是：

```text
不要把聊天上下文当作项目记忆。
上下文只保留当前推理需要的最小活动集。
```

对 AI PhD student，这意味着：

- 不要把整篇论文、全部实验日志、完整训练输出、所有 reviewer notes 都塞进一个 session。
- 论文、实验、代码状态必须落到文件里。
- 长 session 不是成就，而是债务。它可能让 Claude 更“知道很多”，也可能让它越来越难分清什么还重要。

### 3.2 磁盘是长期记忆，chat 是短期意识流

Claude Code docs 把 `CLAUDE.md` 定义为每个 session 启动时会读取的项目记忆，但也提醒它应该短、稳定、人类可读。特殊 workflow 应该进 skills，而不是堆进 `CLAUDE.md`。社区经验也反复指向同一件事：重要状态要写进 markdown、issue、worktree 状态文件，而不是期待 compact 后还能完整保留。

推荐心智模型：

```text
CLAUDE.md / AGENTS.md       入口规则
.agent/                    repo-local doctrine
.claude/agents/            项目专属 subagents
.claude/skills/            项目专属 workflows
.claude/commands/          项目专属 commands
.claude/hooks/             项目专属 lifecycle checks
ANATOMY.md                 结构地图
lab/research/              claim / evidence / regression ledgers
lab/infra/                 path / permission / storage / runtime contracts
memory/current-status.md   活状态和 handoff
scripts/*validator*        可运行门禁
git commits                可审计历史
W&B / MLflow               指标、artifact、checkpoint 索引
```

Chat 里可以有推理，但不要把 chat 当成唯一证据。真正的研究状态应该能被下一个 fresh session、另一个 agent、未来的你读懂。

### 3.3 Repo 是 agent 的控制面，不是代码容器

这次从 `pairwise-diffusion`、`DOLoop` 和 LingTai anatomy 方法论里看到的共同规律是：好的 AI research repo 不只是 `src/` 加 `tests/`。它应该让 agent 一进 repo 就知道：

- 当前研究 claim 是什么。
- 哪些 evidence 支持它，哪些只是 partial / planned。
- 哪些目录能写，哪些目录只读，哪些 bytes 永远不进 Git。
- 哪个 worktree / branch / remote 是唯一可写目标。
- 哪些结构 claim 需要 `ANATOMY.md` 维护。
- 哪些 external side effects 必须 human gate。
- 哪个 validator 能证明 repo 仍然可控。

所以 Claude Code 优化的主战场不是 user home，而是 repo：

```text
不要把项目能力藏进个人全局 agents/skills/hooks。
把它们做成 repo-local control plane。
```

这会改变工作方式：

- subagent 不只是“一个好用角色”，而是 repo-local、项目特化、可 review 的执行单元。
- skill 不只是“一个 prompt 模板”，而是 repo-local workflow，最好带 manifest、输入输出、适用边界和验证命令。
- hook 不只是“个人自动化”，而是 repo-local gate，用来保护 data、runs、checkpoints、remote side effects 和 structure maps。
- command 不只是快捷入口，而是项目协作协议的一部分，应该尊重 `.agent/`、`ANATOMY.md`、`memory/` 和 `lab/research/`。
- validator 不只是 CI 附件，而是 agent 能否继续扩展 repo 的护栏。

精神必须体现在 repo 里。否则它只是一段在某个 session 里说得很漂亮的话，下一次 fresh context 就会变成传闻。

进一步说，repo 还应该有“能力生成者”：

```text
sub-agent-maker-agent  把反复出现的工作轨迹沉淀成 repo-local subagent
hook-maker-agent       把反复出现的安全/状态/门禁动作沉淀成 repo-local hook
skill-maker workflow   把反复出现的流程沉淀成 repo-local skill
```

这类 maker agent 不替 human 做最终决定。它们负责观察轨迹、总结稳定模式、提出最小可审计 asset，然后让 human 通过 branch / PR / validator 把它纳入 repo 控制面。

### 3.4 ANATOMY.md 是结构防漂移系统

`ANATOMY.md` 的价值不是“多一层文档”，而是把项目结构变成 agent 可导航、可验证、可维护的地图。

没有 anatomy 时，agent 往往靠 grep 误判 ownership：命中旧代码、兼容层、fixture、历史文档，然后在错误位置继续堆逻辑。随着 session 增长，这种误判会逐渐变成代码膨胀和结构漂移。

Anatomy 系统的精神是：

```text
结构不是记忆，是地图。
结构 claim 必须尽量能指向代码坐标。
结构改变必须同步更新地图。
地图过长说明边界该重构，不是文档该加长。
```

它和 Claude Code 的关系非常直接：

- agent 读代码前，先走 root `ANATOMY.md` 找最近 ownership。
- agent 改结构前，先查相关 anatomy 和 index YAML。
- agent 改结构时，同 commit 更新 anatomy。
- agent 验证时，跑 drift checker 和 repo validator。
- human review 时，检查 anatomy impact 和 same-commit rule。

所以 anatomy 是一种 repo-local cognition scaffold：它让未来的 agent 更难乱读、乱改、乱扩张。

### 3.5 Main agent 是 PI / tech lead，不是万能工人

Claude Code 的 subagents 运行在独立 context 中，可以隔离搜索、日志、测试输出和实现细节。官方 docs 把 subagents 的用途概括为保存主会话 context、限制工具、复用专用配置。Anthropic 的 multi-agent research system 文章也把 subagent 看作搜索和压缩机制：多个 agent 探索不同方向，再把关键信息压缩回 lead agent。

但社区反馈同样清楚：subagent 不是越多越好。它们可能继承太多上下文、权限行为可能让人困惑、handoff 可能丢失任务语境。正确姿势是：

```text
main agent = 目标、边界、决策、整合、验收
subagent   = 有限范围内的读、写、测、查、监控、总结
```

AI PhD 场景里，main agent 像 PI 或 tech lead：

- 决定这轮实验要验证什么 claim。
- 决定复现 paper 的成功标准。
- 决定哪些结果可以进入论文，哪些只是草稿。
- 决定什么时候 compact、clear、开 worktree、开 reviewer。

Subagents 像 RA：

- 一个读 paper 和 repo。
- 一个实现 dataset loader。
- 一个跑 targeted tests。
- 一个 tail log 和检查 W&B。
- 一个把当前 session 写成 handoff。

### 3.6 隔离先于并行

并行不是开更多终端，而是先定义所有权边界。

官方 worktree 文档建议用 worktrees 隔离并行 sessions 和 subagent edits，避免互相覆盖。社区也高度一致地指出：多 agent 真正爆炸的不是终端数量，而是 ownership。一个 Reddit 讨论把经验总结成：每个任务一个 worktree，一个小任务说明，一个禁止触碰的文件列表，一个人类 merge queue。

这条原则对 AI PhD 更重要：

- baseline、ablation、paper draft、refactor 不能在同一个脏工作区里乱跑。
- 数据、checkpoint、wandb、runs 不能被实现 agent 当成普通代码随手改。
- 同一 repo 内并行实现必须拆开文件边界，否则省下的 coding 时间会在 merge/review 中还回去。

并行前先问：

```text
这些任务是否真的独立？
每个 agent 拥有什么文件/模块？
哪些路径绝对不能碰？
谁负责 merge 和最终验证？
```

### 3.7 Prompt 是意图，hook/permission 是约束

Claude 会努力遵守 `CLAUDE.md` 和 prompt，但它们仍然是自然语言指令。官方 hooks 文档把 hooks 定义为生命周期事件上的命令、HTTP、prompt 或 agent handler；它们可以在 `PreToolUse`、`PostToolUse`、`PreCompact`、`SubagentStart` 等事件上运行。官方 best practices 也建议：必须每次发生的动作，应该用 hooks。

所以：

```text
想让 Claude 理解你的偏好，用 CLAUDE.md / skills。
想让某事必然发生，用 hooks。
想限制危险行为，用 permissions。
```

比如：

- “Python 项目优先用 uv”可以写进 `CLAUDE.md`。
- “每次改 Python 后格式化”适合 PostToolUse hook。
- “永远不要编辑 checkpoints/ 和 data/”适合 permissions deny。
- “compact 前必须更新 `memory/current-status.md`”适合 PreCompact hook 或专门 checkpoint workflow。

这也是科研安全问题：不要只靠一句“不要删 checkpoint”。把 checkpoint path 从 repo-local permissions、hook、validator、artifact index 四层一起保护起来。

### 3.8 Checkpoint 是本地 undo，Git 是历史，实验系统是事实

Claude Code checkpointing 可以在 `/rewind` 中恢复代码、对话或做局部 summarization。官方文档同时明确：checkpoint 不追踪 Bash 造成的文件变动，不追踪外部系统副作用，也不是 Git 的替代品。

因此：

```text
checkpoint 用来试错。
git 用来保留可审计代码历史。
W&B / MLflow / result files 用来保留实验事实。
```

AI PhD 里尤其不要混淆：

- “Claude 可以 rewind”不代表可以放心乱动远程集群、数据库、云存储或 checkpoint。
- “实验日志在 chat 里出现过”不代表它是可引用证据。
- “模型说测试通过”不代表测试真的通过。要有命令输出、run id、commit hash、artifact path。

### 3.9 可观察性会改变行为

Statusline 看起来只是 UI，但它改变的是操作纪律。官方 statusline 文档支持显示 context、cost、git branch、worktree、model 等信息。社区工具如 ccusage/statusline 系列也说明：用户最需要的是实时知道自己还有多少 context、session quota、weekly quota 和 burn rate。

没有 statusline 时，context 增长是隐形的；等到强制 auto-compact 或 limit warning 出现，往往已经晚了。可观察性让你能在自然断点行动：

```text
40% context：开始问这段历史是否还值得保留。
60% context：完成当前小目标后 checkpoint + compact。
70%+ context：不再开启新方向，先落盘状态。
```

数字不是硬规则，而是提醒：不要在 context 爆满时才想起整理。

### 3.10 Model 和 effort 是预算，不是身份

Claude Code 的模型选择和 effort level 会影响质量、延迟和用量。官方成本文档建议把强模型和高 effort 留给复杂架构、多步 reasoning、最终审查等场景；官方 postmortem 也显示过，默认 effort 或 prompt 行为变化会影响 coding quality。

这里最重要的区分是：

```text
main agent 的质量预算可以很高。
subagent 的预算应该按任务自动路由。
```

你可以在 main agent 里使用最好的模型和最高 effort，因为 main agent 负责目标、边界、整合、验收和人机协作。它像 PI / tech lead，错误决策的代价高。

但 subagent 不是身份贵族。`repo-researcher`、`reviewer`、`experiment-monitor` 这些名字只是角色，不应该自动决定最高模型和最高 effort。真正决定预算的应该是任务形状：

- 这是不是 read-only？
- 会不会改 shared contract、ANATOMY、validator、paper claim？
- 错了会不会浪费 GPU、污染数据、误导论文？
- 需要的是文件定位、普通实现、复杂 debug，还是 final verifier？
- 输出是否需要 claim-grade evidence？

因此：

```text
不要把最高模型/最高 effort 当作默认背景。
用任务风险、证据标准和副作用半径来选择模型和 effort。
```

一个实用分层：

```text
tier 0: 直接 shell / grep，不开 subagent。
tier 1: 低风险查找、文件定位、日志摘要：低 effort / 快模型 / read-only subagent。
tier 2: 普通实现、测试修复：标准模型 / medium effort。
tier 3: 架构决策、复杂 debug、shared contract：高 effort / 强模型。
tier 4: 论文 claim、release gate、最终 verifier：高 effort / 强模型 / fresh context。
```

这个选择过程最好 repo-local 化，而不是靠 human 每次想起来。可以放进：

```text
.agent/model-routing-policy.md
.claude/agents/subagent-router-agent.md
.claude/skills/subagent-routing/SKILL.md
```

当 human 只是说“开一个 subagent 去做 X”，main agent 应该先让 routing policy 或 `subagent-router-agent` 生成 launch packet：

```text
agent_type:
task:
budget tier:
recommended model:
recommended effort:
allowed paths:
forbidden paths:
evidence required:
stop / escalate condition:
```

这样模型和 effort 就从“我喜欢哪个模型”变成“这个任务值得花多少钱”。更重要的是，它可以被校准：如果某个任务 tier 太低导致返工，就在 PR 里更新 routing policy；如果某类任务一直用高 tier 但只是 grep，就降级。

对 AI PhD，这尤其影响 usage：实验周期长、repo 多、paper 多。如果每个小任务都用最高档，很快会把预算烧在无关探索上。

### 3.11 “新鲜上下文”是一种质量工具

官方 best practices 推荐在复杂任务中先 explore / plan / implement / commit，并在无关任务之间用 `/clear`。社区也反复建议：一个 feature、一个 issue、一个实验阶段用一个清晰 session；长 session 中反复纠错会把失败路径留在上下文里，污染后续判断。

新鲜上下文不只是省 token，也能减少认知偏置：

- 写代码的 session 不应该自己做最终审稿人。
- 跑失败三次的 debug session 不一定适合继续做架构判断。
- paper drafting session 不应该背着一堆训练 OOM 日志写 abstract。

但真实问题是：human 经常忘记切 session。任务做着做着就从探索进入实现，从实现进入 review，从 review 进入论文 claim；这个时候本该 `/branch`、开新 session、写 checkpoint 或换 fresh verifier，但人很容易懒，agent 也容易顺着当前上下文继续滚。

所以 fresh context 也应该 repo-local 自动化：

```text
.agent/session-tree-protocol.md
.claude/agents/session-boundary-agent.md
.claude/skills/session-boundary-control/SKILL.md
memory/session-tree.md
memory/branches/<slug>.md
plans/<date>-<slug>.zh.md
```

思想是：

```text
新 session 不是失忆，而是分支。
parent session 保留全局目标和任务树。
child session 只背一个小目标和证据标准。
```

当一个 session 里出现好几个值得独立完成的小任务时，应该把它记录成树状结构：父节点是当前阶段，子节点是 issue、branch、worktree、实验、review 或 paper section。每个子节点有自己的 allowed paths、forbidden paths、验证命令、exit condition 和 handoff。

提醒机制可以来自 statusline、PreCompact hook、session-boundary agent 或 checkpoint-writer，而不是靠 human 的意志力。比如：

- context 超过阈值：提示先写 `memory/current-status.md`。
- 新目标出现：建议开 child session 或 `/branch`。
- 探索结束准备实现：建议 fresh context + worktree。
- 实现结束准备 review：建议 fresh reviewer。
- paper claim 准备进入 deliverable：建议高 effort fresh verifier。

推荐：

```text
探索后写 plan，然后 clear/compact 再实现。
实现后开 fresh reviewer / verifier。
切换研究问题就 clear，不要拖着旧语境。
多个子任务出现时，用 session tree，而不是一条长聊天线。
```

### 3.12 Claude Code 是会漂移的产品，workflow 要可复测

官方 engineering postmortem 说明过，默认 effort、verbosity、cache 等变化都可能影响 Claude Code quality。社区 GitHub issues 也显示，subagent、worktree、hook、compact 行为会随版本出现问题或变化。

所以一个成熟 workflow 不应该只写“验证日期 / Claude Code 版本 / 最小复现”。那只是防漂移的元数据，不是防漂移机制。

真正的机制应该把 Claude Code 技巧当成 repo-local recipe：

```text
human-cc trace
  -> 自动切片
  -> 自动提出候选 workflow recipe
  -> 绑定证据、适用条件、反例和复测任务
  -> human review
  -> 写入 repo-local current practice
  -> 定期复测、降级或废弃
```

这里的 `human-cc trace` 指 human 与 Claude Code 协作完成任务时留下的工作轨迹：对话摘要、plan doc、human 批注、git diff、测试输出、失败恢复、人工介入点、commit / PR 结果。它不是为了永久保存聊天记录，而是为了从真实摩擦中提炼可复测 workflow。

推荐 repo surface：

```text
lab/traces/human-cc/          原始或脱敏后的 session 轨迹
lab/recipes/claude-code/      Claude Code workflow recipe
lab/evals/cc-workflow/        recipe 复测任务和判定器
lab/reports/cc-workflow/      自动复测报告
memory/current-practices.md   当前采用的 recipe 索引
memory/deprecated-practices.md 失效技巧和原因
human/reviews/                human 对候选 recipe 的 review
```

每条 recipe 至少应该记录：

```yaml
id: cc-recipe-001
title: "用 repo-local plan doc 承载多步任务"
status: candidate  # candidate | provisional | stable | deprecated
observed:
  date: 2026-07-06
  product: Claude Code
  version: "<claude --version>"
claim: >
  对跨多个文件的任务，先写 repo-local plan doc，再实现，
  比只在聊天中维护 plan 更容易恢复上下文和 review。
preconditions:
  - 任务会跨多个文件或多个 session
  - repo 有 human/、plans/ 或 docs/ 工作面
steps:
  - 创建或更新 plan doc
  - human 在文件中批注
  - Claude Code 读取 diff 并收敛 plan
evidence:
  traces:
    - lab/traces/human-cc/2026-07-06/session-abc/
  commits:
    - "<commit-sha>"
evals:
  - lab/evals/cc-workflow/plan-doc-recovery.yaml
metrics:
  - recovery_turns_after_context_drop
  - unresolved_assumption_count
  - human_review_minutes
counterexamples:
  - "小于 20 行的单文件修改会被 plan doc 拖慢"
expires_at: 2026-08-06
```

Harvester 不应总结“Claude Code 很好用”。它只提炼有行为证据的结构性片段：

- `stuck -> recovery`：agent 卡住后，哪种 human 提示或 repo 文件让它恢复？
- `plan drift -> correction`：哪个检查、文档或 human 批注把计划拉回边界？
- `tool failure -> fallback`：工具失败后，哪个 fallback 真的成功？
- `review comment -> durable rule`：human 反复指出的问题是否应该变成 AGENTS、hook、validator 或 recipe？
- `context loss -> repo recovery`：上下文断裂后，哪些 repo 文件足够让 fresh session 接续？

Recipe 状态机：

```text
candidate     只有少量 trace 支持，不能作为默认规则。
provisional   有复测任务，并连续通过至少两次，可以局部采用。
stable        跨多个任务类别仍然有效，写入 current-practices。
deprecated    复测失败、产品行为变化，或被更简单 recipe 取代。
```

触发复测：

- 每周固定一次。
- Claude Code、模型、权限策略、hooks、settings、subagent 行为升级后。
- AGENTS.md、`.agent/`、repo-local skills / hooks / validators 变化后。
- 某个 recipe 相关任务失败后。

复测任务不需要很大。每个 recipe 绑定 1-3 个小任务即可：一个正例、一个边界例、一个反例。这样“技巧”就不会变成永恒真理。它会像训练 recipe、依赖版本和实验配置一样，有证据、有适用条件、有过期时间、有降级路径。

---

## 4. Claude Code 部件分工

### 4.1 CLAUDE.md

用途：Claude Code 的 repo-local 入口。它应该短，负责把 Claude 导向 `AGENTS.md`、`.agent/`、`ANATOMY.md`、`memory/current-status.md` 和项目 validator。

适合放：

- 必读入口文件。
- 构建命令、测试命令、repo validator。
- 数据、checkpoint、实验输出的安全边界。
- 说明项目相关 Claude Code assets 在 `.claude/`，不是 user 全局。

不适合放：

- 长教程。
- 每个文件的解释。
- 临时任务状态。
- 大段 API 文档。
- 只在某个 workflow 中用到的步骤。
- 另一套和 `AGENTS.md` / `.agent/` 冲突的 doctrine。

### 4.2 Skills

用途：repo-local 可复用流程和领域知识，按需加载。项目相关 skills 应放进 `.claude/skills/`，并像代码一样被 review、版本化、验证。

适合：

- `/checkpoint`
- `/experiment-watch`
- `/paper-reproduce`
- `/feature-split`
- `/result-promote`
- `/pr-review`

核心理由：specialized workflow 放进 skills，可以避免每个 session 都把它塞进基础 context。

但 skill 不应该只是一个“聪明 prompt”。对研究 repo，它最好有：

- 适用边界。
- 输入/输出 artifact。
- 需要读取的 ledger。
- 允许修改的路径。
- 验证命令。
- 失败时的 handoff 规则。

### 4.3 Subagents

用途：隔离上下文、限制工具、并行执行。项目相关 subagents 应放进 `.claude/agents/`，并由 repo contract 管理，而不是全局安装一堆对所有项目都可见的角色。

适合：

- repo 只读探索。
- targeted test run。
- 实验日志监控。
- checkpoint/handoff 写作。
- 实现一个边界清楚的小功能。
- 独立 reviewer/verifier。

不适合：

- 没有边界的大型“帮我把项目做好”。
- 需要完整主线程历史才能理解的任务，除非显式 fork。
- 多个 agent 同时编辑同一模块。
- 高风险外部系统操作。

### 4.4 Hooks

用途：repo-local 确定性自动化与强约束。hooks 应保护具体 repo 的真实边界，例如 data bytes、remote outputs、private overlays、anatomy drift、release overclaim。

适合：

- Notification：Claude 等待输入时通知。
- PostToolUse：编辑后格式化或记录。
- PreToolUse：阻止危险命令。
- PreCompact：检查 `memory/current-status.md` 或 handoff 是否更新。
- SubagentStart/Stop：记录 agent 生命周期。
- WorktreeCreate：自定义 worktree 初始化。

风险：hooks 本身是代码，且命令 hooks 以本机权限执行。要小而可审计，最好和 `.agent/action-boundary.md`、`lab/infra/permissions/`、validator 对齐。

### 4.5 Permissions

用途：把危险行为从“请你不要”变成“不能做 / 要问”。

AI PhD 常见保护对象：

- `lab/data/**`
- `checkpoints/**`
- `wandb/**`
- `lab/runs/**`
- `lab/infra/private/**`
- `.env`
- remote push / deployment / cluster kill job / sudo / package install

### 4.6 Worktrees

用途：同一 repo 内并行编辑的隔离边界。

适合：

- baseline vs ablation。
- refactor vs paper deadline hotfix。
- 多个 feature-worker 并行。
- fresh reviewer 在独立 checkout 里审查。

注意：worktrees 不是免 merge 成本。它们只是把冲突从“同时乱改”推迟成“显式 merge/review”。

### 4.7 Statusline / Usage

用途：把 context、quota、model、branch、worktree 变成可见仪表盘。

推荐显示：

```text
model | effort | context% | session/weekly usage | repo | branch | worktree | cost/burn
```

### 4.8 MCP / Connectors / CLI

用途：外部系统访问。

原则：

- 能用 CLI 解决的，通常比 MCP 更省 context。
- MCP 适合有结构化接口、权限清楚、重复调用频繁的系统。
- 高权限 MCP 必须谨慎，尤其是能读 secrets、改数据库、发邮件、改 issue 状态的工具。

---

## 5. AI PhD Student 的特殊约束

### 5.1 研究不是普通 feature delivery

研究工作有几个特别麻烦的性质：

- 目标会变：一个实验结果可能推翻当前 plan。
- 证据有层级：log、metric、table、figure、paper claim 不能混为一谈。
- 计算昂贵：训练可能跑几小时到几天，不能让 agent 随手重启或删除。
- 代码与论文耦合：一个 bugfix 可能改变实验结论和文字叙事。
- 多 repo 并行：paper repo、code repo、baseline repo、forked upstream repo 往往同时存在。

因此，Claude Code workflow 应该像实验室 protocol，而不只是工程 checklist。

### 5.2 每个 session 都应该有研究对象

好的 session 目标类似：

```text
验证 Figure 3 的 latent interpolation 代码路径是否和 paper 描述一致。
复现 baseline X 的 preprocessing，并输出最小 smoke test。
检查 ablation run A/B 的 metric 差异是否足以进入 paper table。
把 reviewer comment R2.3 映射到 intro 和 experiment section 的修改计划。
```

坏的 session 目标类似：

```text
帮我看看这个项目。
把实验做好。
优化一下论文。
把所有 bug 修掉。
```

Claude Code 可以探索，但你要给它一个可收敛的研究对象。

### 5.3 研究事实必须可追溯

每个重要结论都应该能回答：

- 来自哪个 command？
- 哪个 git commit？
- 哪个 run id？
- 哪个 config？
- 哪个 checkpoint？
- 哪个数据 split？
- 哪个表格/figure？
- 是否经过 fresh verifier？

如果答案只存在于 chat 中，它还不是研究事实。

追溯性还不只是“结论从哪里来”。对 AI PhD 来说，更常见的问题是：human 忘了东西在哪里。

Claude 可能总结过一个文档、生成过一个表格、整理过一个 figure、跑过一个 checkpoint、下载过一个 dataset、写过一个 data card，但三周后你只记得“好像做过”。并行实验一多，这会变成真正的研究风险：你不知道哪个 run 还有效，哪个 checkpoint 已经过期，哪个 table 是旧口径，哪个 dataset split 支持当前 paper claim。

所以 repo 需要 artifact memory：

```text
lab/artifacts/result-index.yaml
lab/artifacts/table-index.yaml
lab/artifacts/figure-index.yaml
lab/models/checkpoint-index.yaml
lab/data/dataset-index.yaml
lab/research/experiment-ledger.yaml
deliverables/index.md
```

每个资产至少应该能回答：

- 在哪里？
- 怎么看？
- 对应哪个 commit / config / run id？
- 支持哪个 claim / table / figure？
- 当前是 active、superseded、archived，还是 unknown？
- 什么时候应该归档或删除索引？

这件事也不应依赖 human 记忆。可以用 repo-local `artifact-librarian` agent 和 `artifact-indexing` skill，让 Claude Code 在实验结束、table 更新、figure 生成、checkpoint 选择、paper claim promotion 之后主动维护索引。

保持 repo 干净不是洁癖，而是研究记忆压缩。过期资产及时标记、归档或从 active index 移除，能让 future session 更快判断“当前有效事实”是什么。

### 5.4 开发 Agent 时，区分外层 harness 和内层 release agent

如果项目本身就是为了开发一个 agent，更需要区分两套东西：

```text
外层 Claude Code development harness:
  为了让 Claude Code 更好地开发这个 repo。
  例如 AGENTS.md、CLAUDE.md、.claude/、.agent/repo-editing-guardrails.md。

内层 release agent:
  这个 repo 最后要发布、评估或交付的 agent 本身。
  例如 src/、agent/、evals/、traces/、docs/release/、release-gates。
```

不要把“开发时约束 Claude Code 的规则”和“产品 agent 的行为契约”混成一个长 prompt。前者属于 repo editing harness，后者属于 release artifact。它们可能互相影响，但应该有不同的 anatomy、validator、trace/eval 和 human gate。

类似 `DOLoop` 这样的 repo，`.agent/` 成为第一等公民是合理的；但 `.agent/` 里也要讲清楚哪些文件服务于外层开发，哪些文件定义内层 agent 的 behavior contract、action boundary、context policy、tool-skill interface、trace-eval loop、human gates 和 production control plane。

---

## 6. 反模式

### 6.1 一个 mega-session 承载整个项目

症状：

- context 过 70% 后还继续开新方向。
- compact 后忘记早期约束。
- 同一 session 里做了 paper reading、debug、训练监控、LaTeX 修改、Git 操作。

修复：

- 每个阶段写 handoff。
- clear 或新 session。
- 用 session name 和文件状态恢复。

### 6.2 把 subagent 当无限 worker

症状：

- 让 general-purpose agent 到处探索。
- 多个 worker 没有文件所有权。
- subagent 输出大段日志回主线程。
- main agent 不读报告，直接相信“done”。

修复：

- agent prompt 必须有边界、工具、输出格式、停止条件。
- 报告写文件，主线程只接摘要。
- main agent 负责最终 verification。

### 6.3 把 hooks 当魔法安全层

症状：

- hook 很复杂，没人审计。
- 在 worktree / desktop / remote surface 下假设 hook 一定生效。
- 没有 fallback。

修复：

- hook 小而确定。
- 高风险操作仍需 permission / Git / manual review。
- 定期用 `/hooks` 或 debug mode 验证。

### 6.4 把 compact 当最后一刻救生艇

社区里有 `/compact` 在 context 已满时失败的报告。即使不考虑 bug，最后一刻 compact 也最容易丢掉关键状态。

修复：

- 在自然阶段结束时 compact。
- compact 前写 `memory/current-status.md` 或 handoff。
- 不在 context 接近满时开启新任务。

### 6.5 粘贴整段日志或论文

症状：

- 直接贴 5000 行训练日志。
- 直接贴整篇 paper。
- 直接贴完整 source file。

修复：

- 让 agent 用 `tail -n 200`、`grep ERROR`、结构化 parser。
- 给文件路径、run id、section name。
- 让 subagent 读，然后返回 summary。

### 6.6 在高风险系统上用 auto / bypass 心态

Auto mode 和 bypass permissions 可以提高自主性，但论文实验和集群资源常常有真实成本。

不要让 agent 未经确认：

- 删除数据或 checkpoint。
- kill/restart 长训练。
- push 到共享 branch。
- 改生产/共享数据库。
- 修改导师/合作者可见的最终材料。

### 6.7 把 session、branch、artifact 都交给 human 记忆

症状：

- human 忘了哪个 branch 做什么。
- 不知道哪个 worktree 对应哪个 issue / PR。
- 记得 Claude 总结过一个表格，但不知道文件在哪里。
- 多个并行实验结束后，不知道哪个 checkpoint 还能用。
- plan 只在聊天里，没有 repo-local anchor。

修复：

- 用 `branch-reporter` 维护 branch/worktree 功能分野。
- 用 `session-boundary-agent` 维护 session tree。
- 用 `artifact-librarian` 维护 dataset/checkpoint/table/figure index。
- 用中文 interactive plan doc 作为 human 与 Claude Code 的协商界面。
- plan doc 的关键修改用 commit 追踪，避免“我们刚才说过什么”只存在于短期记忆里。

---

## 7. 最小可行哲学

最小可行不是“少建目录、少写文档”，而是让 human 和 Claude Code 都能从 repo 里读到可信信息，并通过 repo 改变可信信息。

Chat 是临时控制台；repo 是共同可信平面。Human 的目标、批注、plan review、结果 review、决策和反例，都应该能进入 repo 中一个容易读的位置，而不是留在聊天窗口或 human 记忆里。

推荐最小 human-agent 交互面：

```text
README.md                 给 human 的入口：这个 repo 是什么、现在怎么看
AGENTS.md / CLAUDE.md     给 agent 的入口：从哪里读、哪些规则必须遵守
human/briefs/active/      human 与 agent 共同编辑的任务 brief
human/reviews/            plan review、result review、争议点
human/decisions/          轻量 ADR：为什么接受或拒绝某个规则 / recipe
memory/current-status.md  当前状态和 handoff
lab/recipes/claude-code/  可复测 Claude Code workflow recipe
```

如果只记住十二条：

1. Repo 是可信控制面，不是代码容器；chat 只是短期意识流。
2. Context 是昂贵工作记忆，不是仓库。
3. 长期状态写文件，不写在聊天里。
4. Human 通过 repo-local brief / review / decision 与 agent 协作，而不是靠回忆聊天。
5. Main agent 做决策，subagents 做隔离任务。
6. 并行之前先定义 ownership，必要时用 worktree。
7. Prompt 表达意图，hooks/permissions 执行硬约束。
8. Checkpoint 不是 Git，Git 也不是实验记录。
9. Statusline 是仪表盘，没有仪表盘就别开长途。
10. 高模型和高 effort 是子任务预算，不是 agent 身份。
11. Fresh context 是质量工具，session tree 是它的索引。
12. Claude Code 会更新，workflow recipe 要从 human-cc trace 中自动提炼并定期复测。

---

## 8. 推荐口号

```text
Treat Claude Code as a lab instrument.
Calibrate it, constrain it, log it, verify it.
Do not worship the agent; design the harness.
```

中文版本：

```text
把 Claude Code 当作实验仪器：
校准它、约束它、记录它、验证它。
不要崇拜 agent，要设计 harness。
```

---

## 9. 参考资料

官方文档：

- [Best practices for Claude Code](https://code.claude.com/docs/en/best-practices)
- [Manage costs effectively](https://code.claude.com/docs/en/costs)
- [Create custom subagents](https://code.claude.com/docs/en/sub-agents)
- [Extend Claude with skills](https://code.claude.com/docs/en/skills)
- [Hooks reference](https://code.claude.com/docs/en/hooks)
- [Automate actions with hooks](https://code.claude.com/docs/en/hooks-guide)
- [Claude Code settings](https://code.claude.com/docs/en/settings)
- [Customize your status line](https://code.claude.com/docs/en/statusline)
- [Run parallel sessions with worktrees](https://code.claude.com/docs/en/worktrees)
- [Checkpointing](https://code.claude.com/docs/en/checkpointing)
- [Manage sessions](https://code.claude.com/docs/en/sessions)
- [Commands](https://code.claude.com/docs/en/commands)
- [Interactive mode](https://code.claude.com/docs/en/interactive-mode)
- [How do usage and length limits work?](https://support.claude.com/en/articles/11647753-how-do-usage-and-length-limits-work)
- [Use Claude Code with your Pro or Max plan](https://support.claude.com/en/articles/11145838-use-claude-code-with-your-pro-or-max-plan)

Anthropic blog / engineering：

- [Effective context engineering for AI agents](https://www.anthropic.com/engineering/effective-context-engineering-for-ai-agents)
- [How we built our multi-agent research system](https://www.anthropic.com/engineering/multi-agent-research-system)
- [Enabling Claude Code to work more autonomously](https://www.anthropic.com/news/enabling-claude-code-to-work-more-autonomously)
- [How we built Claude Code auto mode](https://www.anthropic.com/engineering/claude-code-auto-mode)
- [An update on recent Claude Code quality reports](https://www.anthropic.com/engineering/april-23-postmortem)

Repo-local harness / 防漂移参考：

- `a-green-hand-jack/pairwise-diffusion` private repo, access required
- `a-green-hand-jack/DOLoop` private repo, access required
- [LingTai Anatomy System guide](https://gist.github.com/a-green-hand-jack/f2f153c72dda4ed92d35006137243d23)

社区与实践材料：

- [Reddit: Claude Code tips on managing context](https://www.reddit.com/r/ClaudeAI/comments/1mezb57/claude_code_tips_on_managing_context/)
- [Reddit: small context window discussion](https://www.reddit.com/r/ClaudeCode/comments/1qps9xj/how_do_you_all_deal_with_claudes_small_context/)
- [Reddit: managing multiple coding agents in parallel](https://www.reddit.com/r/ClaudeCode/comments/1st213z/how_are_you_managing_multiple_coding_agents_in/)
- [Reddit: compacting strategy](https://www.reddit.com/r/ClaudeCode/comments/1trpxbb/what_is_your_claude_code_compacting_strategy/)
- [Hacker News: subagents and context skepticism](https://news.ycombinator.com/item?id=45181577)
- [Dan Does Code: custom Claude Code statusline](https://www.dandoescode.com/blog/claude-code-custom-statusline)
- [ccusage statusline guide](https://ccusage.com/guide/statusline)
- [Voitanos: Claude Code status line and token burn](https://www.voitanos.io/blog/claude-code-cli-statusline/)
