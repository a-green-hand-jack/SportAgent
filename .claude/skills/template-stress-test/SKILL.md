---
name: template-stress-test
description: 用一个真实、非平凡的 case（外部项目或真实场景）压力测试模板自身的 validators/hooks/skills/subagent/command，在模板大改之后或想验证某类机制是否真的可用时使用；测试记录与修复实现分离，绝不在 case 分支里顺手改模板。
---

# template-stress-test

模板自己也会漂移。这个 skill 把 ELF-template-case（round 1-4,`lab/docs/audits/
agent-native-template-functional-test-report.md`）实际走过的流程 formalize 成可
重复步骤,供以后任何一次模板大改、或想再拿一个新 case 测试时照做,不用从头摸索。

## 适用边界

适用:模板新增一类机制之后想验证它是否真的可用;模板对 `lab/`/`deliverables/`/
`memory/` 结构做过较大调整之后;怀疑某个 bug 修复没有真正生效,想找证据。

不适用:纯文档措辞改动(不需要压力测试,见 `.agent/template-stress-test-policy.md`
的分级);已经在走 `worktree-pr-flow` 的常规功能改动(那是改一处代码,不是测整个
模板)。

## 输入 / 输出 artifact

- 输入:一个真实、非平凡的 case 来源(外部开源项目、真实研究场景等——不要用空手
  合成的玩具 case,信号太弱)。
- 输出:`case/<name>` 分支 + worktree、发现记录(`lab/docs/audits/<case>-report.md`,
  必要时附 `<case>-probe-catalog.md`)、`lab/docs/audits/stress-test-ledger.yaml`
  新增一条记录、按发现分出的独立修复分支/PR(不在 case 分支里改)。

## 需要读取的 ledger

- `.agent/template-stress-test-policy.md`(变更幅度 → 测试深度分级、登记账定位)。
- `.claude/skills/template-stress-test/references/probe-surface-catalog.md`
  (面向未来的探针清单起点)。
- `lab/docs/audits/stress-test-ledger.yaml`(已有 case 的登记,避免重复劳动)。
- `.agent/claude-code-recipe-policy.md`(如果测试过程中发现值得沉淀的 Claude Code
  使用技巧,走这条既有流水线,不要在本 skill 里另造一套)。

## 允许修改的路径

- `case/<name>` 分支 / 对应 worktree 内的任意路径(隔离,不影响 `main`)。
- `lab/docs/audits/`(发现记录、登记账)。
- 修复本身**不**在这个 skill 的允许路径内——修复走独立分支/PR(见步骤 7)。

## 步骤

1. **挑/建 case**:选一个真实、非平凡的外部项目或场景。分支命名 `case/<name>`
   (如 `case/elf-template-replay`),worktree 建在 `.claude/worktrees/<name>/`,
   从 `main` 分出。先在 `lab/docs/audits/stress-test-ledger.yaml` 查有没有已测过
   相近 case,避免重复劳动。
2. **迁移/复现进模板结构**:把 case 内容按模板既有约定放进去(如外部 vendor 代码走
   `lab/code/external/`,见 `human/decisions/20260709-lab-docs-reference-and-
   external-vendor-placement.md`)。
3. **判断测试深度**:按 `.agent/template-stress-test-policy.md` 的分级表,对照
   这次要测的机制属于哪一档,决定要不要做完整对抗性探针矩阵还是定向 smoke。
4. **演练相关 subagent/skill/command**:真实派发/调用,不只看契约文档;记录实际
   行为是否符合声明的边界。
5. **对抗性探针**(深度达标才做):对每个 validator/hook,参照
   `references/probe-surface-catalog.md` 做 mutate→assert→revert——制造一个应该
   被拦截的坏状态,确认真的被拦、错误信息准确,然后 revert 干净,`git status`
   确认无残留。
6. **写发现**:分类沿用 F1-F19 用过的惯例——template gap(模板缺一种机制)/
   validator 按预期工作 / case ledger 债务 / 文档摩擦 / 迁移执行失误(自己的失误,
   不是模板的 bug)。写进 `lab/docs/audits/<case>-report.md`。
7. **决定修复范围,记录与修复分离**:发现的 bug/漂移**不在 case 分支里顺手改**——
   开独立分支/PR 修,走 `worktree-pr-flow`。case 分支只读记录,保持"case 测的是
   哪个模板版本"这件事可追溯。
8. **独立复验**:如果修复涉及 session 启动时加载的配置(hook/settings.json 之类),
   同一个持续运行的 session 可能无法自证修复生效(它自己的配置在启动时就已固定)——
   需要在一个全新顶层 session 里复验,不能只用同 session 内的 subagent 进程替代
   (subagent 进程和顶层 session 的加载机制可能仍有细微差异)。
9. **登记**:在 `lab/docs/audits/stress-test-ledger.yaml` 追加一条记录(case 来源、
   测试的模板 commit 范围、深度、发现摘要、报告路径)。
10. **决定 case 分支去留**:默认 case 分支不合并回 `main`(避免把外部 case 的具体
    内容污染进模板);如果 case 产出中有值得沉淀成模板永久内容的部分(如通用探针、
    可复用 recipe),原样 `git checkout <case-branch> -- <path>` promote 到 `main`
    对应位置,不改动内容(见 PR #5/#6 的先例)。

## 验证命令

```
python scripts/validate-governance.py
python scripts/check-same-commit.py --staged
```

## 失败时的 handoff

- 探针没有按预期被拦下:这是真实的 template gap,先记录(不要现场顺手修),按步骤 7
  分出独立修复分支。
- case 本身涉及需要人类批准的外部资源(clone 私有仓库、启动远端作业等):停下问人类,
  不擅自扩权。
