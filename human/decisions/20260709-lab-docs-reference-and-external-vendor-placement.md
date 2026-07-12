# lab/docs/ 下 reference / research-narrative 平面与外部 vendor 代码位置

## Context

模板本身有意不设通用根级 `docs/`（见 `.agent/repo-documentation-topology.md`「为什么没有通用
`docs/`」一节、`DESIGN.md` §12），文档按角色分布到各级 README/AGENTS/CLAUDE/ANATOMY +
`.agent/` + `lab/research/`。但这留下两个此前未正式约定的缺口：

- **(F5)** 面向文献/参考资料整理、以及不落在 `lab/research/*.yaml` 结构化 schema 里的自由
  叙事性研究记录（如假设记录、risk/action board、探索死胡同与负结果的叙事记录），模板没有
  专属的模板平面——不属于任何 `README.md` 该负责的「这里是什么」，也不是 `.agent/` 的行为
  契约，塞进 `lab/research/` 又不符合它的结构化 evidence schema。
- **(F6)** 外部 vendored 第三方源码（例如把上游 GitHub repo clone 进本地做参考/复现基线，
  clone 出来的目录自带自己的 `.git`）应该放在哪里、要不要进 Git、provenance 记录在哪，也没有
  正式约定。

这两个缺口在 `worktree-case+elf-template-replay` 分支做 ELF-template-case 迁移测试（把
`lillian039/ELF` 这个真实 PyTorch 项目迁移进本模板）时被实际撞到：旧周期遗留的 `reference/`、
`research-artifact/`、旧 `docs/` 三类内容需要落地到某处，且需要 clone 一份 ELF 上游代码做本地
验证。当时不得不现场做判断，采用了一套具体方案（见 Decision），但这套方案只存在于那一次迁移
的产物里，没有被固化成 fresh session 也能读到的规则——不写下来，下一次迁移/新 session 会重新
面对同样的「往哪放」问题，且可能做出不一致的选择。

## Decision

固化 ELF-template-case 迁移时实际采用、且证明可行的方案（**不改变现状，只是把已经在做的事情
写成规则**）：

1. **F5 — reference / research-narrative 落到嵌套 `lab/docs/` 下的专属子目录**，遵循「文档
   按角色分布、项目级长文用嵌套 `lab/docs/`」的既有设计（`.agent/repo-documentation-topology.md`）：
   - `lab/docs/reference/` —— 项目本地来源、来源卡片（`reference/cards/`）、来源笔记
     （`reference/notes/`）、处理状态、来源-项目对照笔记，以及第三方来源的 provenance 记录
     （`reference/provenance.md`，见第 2 条）。
   - `lab/docs/research-narrative/` —— 不落在 `lab/research/*.yaml` 结构化 schema 里的自由
     叙事性研究记录，例如假设记录（`logic/`）、risk/action board、探索死胡同与负结果的叙事
     记录（`trace/`）。
   - `lab/docs/audits/` —— 一致性审计、功能测试报告、就绪检查等长文审计记录（原「旧 `docs/`」
     内容的去处）。
   - 这些子目录都是 `lab/ANATOMY.md` 归类下的 leaf 层：只有 `README.md`，不需要独立
     `ANATOMY.md`；不是 validator 校验对象，对外 claim 仍须能追溯到 `lab/research/evidence.yaml`。
   - 来源材料可能私密/有版权限制，默认不假设可提交；只提交已脱敏的卡片与项目笔记。

2. **F6 — 外部 vendored 第三方源码走 `lab/code/external/`，整体 gitignore 掉**（bytes 不进
   Git，含其自带的 `.git`），只在 `lab/docs/reference/provenance.md` 留 provenance 记录（来源
   URL、分支、commit、baseline commit、可见性 public/internal、导入方式与理由）。理由与「data/
   checkpoint/run bytes 不进 Git，只登记 index」（`.agent/artifact-policy.md`）同构：第三方源码
   不是本项目的一等公民产物，克隆它是为了本地参考/复现，不是为了维护它的历史；进 Git 会造成
   体积膨胀、许可证边界模糊，且它本来就有自己的版本历史（可用 provenance 记录的 commit 精确
   定位复现）。

## Consequences

- 好处：
  - 关闭了 F5/F6 两个此前模板层面缺失的正式约定，未来的迁移/新项目不用再现场做判断，减少
    不一致。
  - 与既有「不设通用 `docs/`、大 bytes 不进 Git、只留 index/provenance」两条既有设计原则同构，
    不引入新的分类哲学。
  - 已经过一次真实、非平凡的迁移测试验证可行（ELF-template-case，见
    `worktree-case+elf-template-replay` 分支的
    `lab/docs/audits/agent-native-template-functional-test-report.md`）。
- 代价 / 约束：
  - 本决策只固化规则，不在模板本身预先创建 `lab/docs/` 目录骨架或 `lab/code/external/` 的
    `.gitignore` 条目——按「不为整齐制造空文档/空目录」的既有原则，留给第一次真正需要它们的
    项目/session 现场创建。
  - `lab/docs/reference/` 下的第三方来源材料默认视为可能私密或有版权限制，agent 不应默认可
    提交原始来源，只能提交已脱敏卡片；违反会造成许可证/隐私风险。
  - `lab/code/external/` 内容 gitignore 掉后，可复现性完全依赖 `provenance.md` 记录是否准确
    （来源、commit、导入方式）；provenance 记录缺失或过期会导致该外部依赖不可追溯，需要按
    `.agent/artifact-policy.md` 的「缺元数据」精神对待。
  - 若某个具体子目录（如 `research-narrative/`）后续证明需要更细的结构化 schema，应另开 ADR
    演进，而不是直接改这条决策的既定分类。

## Status

accepted
