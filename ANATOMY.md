---
related_files:
  - human/ANATOMY.md
  - .agent/AGENTS.md
  - .claude/ANATOMY.md
  - .codex/ANATOMY.md
  - .agents/ANATOMY.md
  - lab/ANATOMY.md
  - memory/ANATOMY.md
  - deliverables/ANATOMY.md
  - scripts/ANATOMY.md
maintenance: |
  这是 root router。结构改动必须同 commit 更新本文件与相关子 ANATOMY。
  引用必须 repo-relative 且尽量 line-addressed（path/to/file.py:42 或 :42-90）。
  本文件只做路由，不解释全系统；单目录细节放各自 ANATOMY.md。
---

# repo ANATOMY（root router）

<!-- template:begin -->

## What this is

`ml-project-repo` 的结构路由。它把 agent 导向「最近的 ownership」，避免 grep 误判。
每个复杂目录有自己的 `ANATOMY.md`；本文件只列分层与去哪里。

## 分层地图

| 平面 | 目录 | 作用 | 子地图 |
| --- | --- | --- | --- |
| 入口层 | `AGENTS.md` `CLAUDE.md` `PROJECT.md` `DESIGN.md` | agent/human 入口、项目描述、模板设计说明 | — |
| 交互层 | `human/` | brief / review / decision / inbox | `human/ANATOMY.md` |
| doctrine 层 | `.agent/` | 行为契约、边界、政策、协议 | `.agent/AGENTS.md` |
| Claude 能力层 | `.claude/` | canonical subagents / skills / commands / hooks / settings | `.claude/ANATOMY.md` |
| Codex 适配层 | `.codex/` `.agents/` | Codex config / custom agents / repo skills adapters | `.codex/ANATOMY.md` · `.agents/ANATOMY.md` |
| 研究控制面 | `lab/` | code / infra / research / data / artifacts / runs / recipes | `lab/ANATOMY.md` |
| 活状态层 | `memory/` | current-status / session-tree / practices | `memory/ANATOMY.md` |
| 对外承诺层 | `deliverables/` | paper / slides / release | `deliverables/ANATOMY.md` |
| 门禁层 | `scripts/` | harness / anatomy-drift / governance validators | `scripts/ANATOMY.md` |
| 版本同步层 | `VERSION` `CHANGELOG.md` `template-manifest.toml` | 模板版本真源与上下游同步分类锚点（下游另持 `.template.toml`） | `.agent/template-versioning-policy.md` |

## 结构规则（详见 `.agent/anatomy-protocol.md`）

- 根 `ANATOMY.md` 只做 router。
- 只有「多文件协作 / 跨模块调用 / 持久状态 / 生命周期 / 路由 / schema / 权限」的目录才写自己的 `ANATOMY.md`。
- 结构 claim 尽量引用代码坐标；single-file trivial helper、空目录、静态资源不写 placeholder anatomy。
- 目录级 anatomy 目标 ~80 行，硬上限 ~120 行；写不短通常是边界该重构。

## Notes

- 大 bytes（`lab/data`、`lab/runs`、`lab/models`、checkpoints、wandb）不进 Git，repo 只留 index。

<!-- template:end -->

<!-- 项目自定义区（template:end 之后，sync 不碰）：下游在此追加本项目特定内容；template:begin/end 块内是模板拥有的内容，如需改动请走 template-feedback 上报，勿在此直接改块内。 -->

## SportAgent 项目单元

| 路径 | 作用 | 入口 |
| --- | --- | --- |
| `lab/code/imported/SportAgent/` | 可运行的 Fitness Agent 产品单元 | `README.md` · `pyproject.toml` |
| `human/imported/adoption-conflicts/` | 采用模板时保留的原始冲突文件 | 原 README / CLAUDE / gitignore |

产品单元保持原来的 `src/`、`tests/`、`data/`、`docs/` 和 uv 布局，避免改变运行时路径语义。
