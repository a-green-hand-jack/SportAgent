# 探针面目录(面向未来,持续维护)

给每一类"应该被模板拦下的坏状态"记一条探针:做什么、预期什么。这是**可复用的清单**,
不是某一次 case 的具体执行记录——具体某个 case 跑这些探针时的真实 Mutation/Actual
结果,写进该 case 自己的报告(如 `lab/docs/audits/stress-probe-catalog.md` 是 ELF
case round 3 的历史记录,不是本文件)。

格式沿用 ELF case round 3 定下的惯例:`Mutation`(制造什么坏状态)/ `Expected`(预期
报什么错)。执行时补 `Actual` + `Classification`(`validator/hook 按预期工作` |
`template gap` | `case ledger 债务` | `N/A + 原因`)+ `Follow-up`,记进具体 case 的
报告里,不要改动本文件的这两列。

模板新增一类机制(新 validator 检查项、新 hook、新 subagent 类别、新 skill 类别)时,
在对应分区补一行——这是本文件"随模板演化持续维护"的方式。

## `scripts/validate-governance.py`

| 探针 | Mutation | Expected |
| --- | --- | --- |
| `.gitignore` 缺保护路径 token | 从根 `.gitignore` 删除某条保护路径规则(如 `wandb/`) | 报 `.gitignore 未提及受保护路径：<name>` |
| 权重 bytes 误入 Git | `touch foo.ckpt && git add -f foo.ckpt` | 报 `权重 bytes 被误加进 Git：foo.ckpt` |
| `lab/runs/` 前缀写入 | 往 `lab/runs/` 写占位文件 | **注意**:ELF case 实测这条会被**权限层**先一步拒绝,根本到不了 validator——测这条前预期会在权限层被挡,不代表 validator 本身没生效 |
| evidence 无引用 | claim 的 `evidence: []` 为空但 `status: partial`(或更高) | 报 `overclaim：claim ... 但无 evidence 支撑` |
| evidence 引用不存在的 id | claim 的 `evidence:` 列表含不存在的 id | 报 `claim ... 引用未知 evidence：...` |
| evidence 反向引用不存在的 claim | evidence 的 `supports_claim` 指向不存在的 claim id | 报 `evidence ... 的 supports_claim 指向未知 claim：...` |
| paper-grade claim 缺 fresh-reviewer 证据 | claim `verified_by_fresh_reviewer: true` 但挂接 evidence 只有 `grade: log` | 报 overclaim:缺少经 fresh reviewer 的 paper-claim 级证据 |
| release-gates 引用不存在的 claim | `release-gates.yaml` 某条状态离开占位默认值后,`for_claim` 指向不存在的 claim id | 报引用错误(见 P1-4 修复,commit `62a9413`) |
| regression-matrix 引用不存在的 claim | 同上,`guards_claim` 字段 | 同上 |

## `scripts/check-agent-harness.py`

| 探针 | Mutation | Expected |
| --- | --- | --- |
| 导航四件套缺文件 | 临时删除某目录的 `AGENTS.md`(或 README/CLAUDE/ANATOMY 之一) | 报 `缺少导航文件：<path>` |
| 根目录污染 | 仓库根新增一个不在白名单里的文件 | 报根目录疑似污染 warning |
| 能力索引缺 frontmatter | 某 `.claude/agents/*.md` 或 `.claude/skills/*/SKILL.md` 删掉 frontmatter 的 name/description | 报 frontmatter 缺失 |
| `settings.json` 引用不存在的 hook | hook 命令里的脚本路径改成不存在的文件名 | 报 `hook 脚本不存在：<path>`(`<event>`) |
| `DESIGN.md` §10 清单数量漂移 | 手动改 `DESIGN.md` §10 表里某个数字(不改实际文件数量) | 报 `DESIGN.md 能力清单过时：<key> 写 <stated>，实际 <actual>`(warning,DESIGN.md 不存在时跳过) |

## `scripts/check-anatomy-drift.py`

| 探针 | Mutation | Expected |
| --- | --- | --- |
| `related_files` 指向不存在的文件 | 某 `ANATOMY.md` 的 `related_files` 加一条不存在的路径 | 报 `related_files 引用不存在 -> ...` |
| 超过行数硬上限 | 把某 `ANATOMY.md` 撑到超过 120 行 | 报超过硬上限 120 行 |
| citation 阈值 | 被引用文件超过 80/120 行但 anatomy 未做 line-addressed citation | 报缺少行级引用(具体阈值见 `.agent/anatomy-protocol.md`) |

## `scripts/check-same-commit.py --staged`

| 探针 | Mutation | Expected |
| --- | --- | --- |
| 有 ANATOMY 的目录内新增文件未同步登记 | 直接在拥有 `ANATOMY.md` 的目录(如 `memory/`)新增文件,不更新该目录的 `ANATOMY.md` | 报 `FAIL —— 结构改动未同步更新对应 ANATOMY.md` |
| **已知设计边界**(不是 bug,记录以便不重复"发现") | 在全新子树(其下任何位置都没有 `ANATOMY.md`)新增大量文件 | 闸门**不会**要求更新祖先目录的 `ANATOMY.md`——只认直接父目录精确匹配,不感知祖先目录(ELF case F3,保守/低误报设计) |

## Hook / 权限层(`.claude/settings.json` + `.claude/hooks/*.py`)

| 探针 | Mutation | Expected |
| --- | --- | --- |
| 危险命令 | `Bash(sudo *)`、`Bash(curl *\| sh)` | 被 `deny` 拦下 |
| 受保护路径写入 | 对 `lab/data/`、`lab/runs/`、`lab/models/`、`checkpoints/`、`wandb/`、`.env` 的 `Edit`/`Write` | 被 `deny` 拦下 |
| 受保护目录的 `rm -rf`/`mv`/`cp` | 对上述路径做删除/移动 | 被 hook(`pre_tool_guard.py`)拦下 |
| `git push` 到 `main`/`master` | 无 `CLAUDE_ALLOW_PUSH_MAIN=1` 时 push 到 `main` | 被拦;设置该环境变量后放行 |
| `git push` 到 topic 分支 | push 到非 `main`/`master` 分支 | 无条件放行 |
| 嵌套 vendored 仓库 cwd 漂移 | cd 进一个项目内、自带 `.git` 的嵌套仓库,cwd 跨调用停留在里面,再跑 Bash/Edit/Write | 应正常工作,不应因 hook 命令用裸相对路径解析而自锁(ELF case F2/F11,已修复为 `$CLAUDE_PROJECT_DIR` 锚定,commit `6fed240`/`bd1266a`;round 4 已在全新顶层 session 里复验通过) |

## Subagent / Skill / Command 层(非机械对抗性探针,靠真实派发/调用来验证契约)

| 探针 | 做法 | 关注点 |
| --- | --- | --- |
| subagent 边界契约 | 真实派发,观察它是否只做声明允许的动作 | 有没有越权删除/未经授权提升 claim 状态/单方面归档 |
| 不带 Bash 的 subagent 的 cwd 假设 | 观察它实际把文件写到哪 | prompt 里的"Working directory: X"文字约定不可靠(ELF case F13),写完后独立核对文件落地位置 |
| 带 Bash 的 subagent 在隔离 worktree 里的自查 | 观察写操作前是否真的 `pwd` + `git rev-parse --show-toplevel` | cwd 不保证跨 Bash 调用持久化(ELF case F19),round 4 已在 4 处补了自查要求,但这是流程 mitigation 不是根治,新 subagent 仍要单独验证是否遵守 |
| skill 文档 vs 实际执行/subagent 契约 | 对照 SKILL.md 声明的步骤与实际执行结果、以及相关 subagent `.md` 契约的措辞 | 是否有 F17 那种"文档说了但契约没跟上"的漂移 |
| slash command 端到端 | 真实调用(不只静态审阅),尤其涉及 human gate 的(如 `/result-promote`) | 该拒绝的场景是否真的被拒绝(human-gate 正面验证) |
