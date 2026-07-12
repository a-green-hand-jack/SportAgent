# template-versioning-policy — 模板版本与上下游同步契约

> 这个模板会被多个下游 ml-research-project 采用。下游在使用中发现缺口 → 上报成本 repo 的 issue
> → 在本 repo 解决并发版 → 下游同步追平。这份 doctrine 定义「版本怎么判级」与「四站闭环」。

## 四站闭环

```
①发现缺口  →  ②登记成 issue  →  ③本 repo 解决(issue→PR→merge, 版本+1)  →  ④sync 回各下游
      ↑________________________________________________________________________|
                   每个下游 .template.toml 记着自己追到哪个版本
```

### ② 有两个入口（源头不同，都汇到 ③④）

- **②a 下游源（downstream → template）**：某个下游项目在使用中发现缺口。下游跑
  `template-feedback` skill，自动带上 `.template.toml` 的版本 + 涉及的框架层路径 + 场景/期望/复现，
  `gh issue create --repo <origin> --label from-downstream`。见
  `.claude/skills/template-feedback/SKILL.md`。
- **②b 模板源（template → template）**：直接在本 template repo 开发/试用时发现要改的东西——源头就是
  模板自己，不存在「下游上报」。**不要用 `template-feedback` skill**（它是下游专用），直接在本 repo
  建 issue（可打 `template-native` 标签区分）或直接进入 ③。判级与发版流程与 ②a 完全一致。

无论哪个入口，③（判级+发版）与 ④（sync 到所有下游）都一样——闭环的下半段是共用的。
- **③ 解决 + 发版**：正常 issue→PR→merge。合并影响**框架层**的 PR 后，agent 判级并跑
  `python scripts/bump-template-version.py --level <major|minor|patch>` 写 `VERSION` + 打 git tag。
- **④ 同步**：下游跑 `python scripts/template-sync.py`，按 `template-manifest.toml` 只覆盖框架层、
  保护项目层与下游私货，跑生成器 + `validate-governance.py` 验收，写回新版本。见 `scripts/ANATOMY.md`。

## semver 判级（agent 可判定的合同）

版本号 `vMAJOR.MINOR.PATCH`。语义**以「对下游 sync 的影响」为准**，不是代码行数：

| 级别 | 含义（对下游的影响） | 典型改动 |
| --- | --- | --- |
| **MAJOR** `vX.0.0` | 破坏性：sync **无法全自动**，下游必须人工 reconcile | manifest 路径分类变更、doctrine 文件重构/改名、hook/validator 契约变更、混合文件哨兵结构变、删除或重命名框架层能力 |
| **MINOR** `v_.Y.0` | 向后兼容的新能力：sync 干净落地，下游净得能力 | 新增 agent/skill/command/hook/validator、doctrine 增补一节、新增受管路径 |
| **PATCH** `v_._.Z` | 修复/微调：全自动可同步，无新表面 | hook/validator/script 的 bugfix、文案订正、无新增能力的内部重写 |

### 判级流程（agent）

1. 看已合并进本次发布的改动集 + 关联 issue + human 批注。
2. 按上表取**最高**适用级别（一次发布若同时含新能力与破坏性变更，取 MAJOR）。
3. **human 批注可覆盖**：若 human 在 issue/PR 注明期望级别，以 human 为准。
4. 跑 `bump-template-version.py --level <lvl>`，它写 `VERSION`、更 `CHANGELOG.md`、打 tag `vX.Y.Z`。

## human gate（见 `.agent/human-gates.md`）

- 打 tag 是本地 git 写操作，允许；**push tag / 建 release 需 human 批准**。
- 下游 sync 时：PATCH/MINOR 可自动落地 + validator 验收；**MAJOR 强制停下让 human 确认**
  （定义上就需要人工 reconcile）。`template-sync.py` 遇 MAJOR 跨越默认拒绝，除非 `--allow-major`。

## 混合文件的哨兵约定（merge kind）

`AGENTS.md` / `ANATOMY.md` / `CLAUDE.md` 这类导航文件，模板骨架与项目内容缠在一起，
既不能整体覆盖（会冲掉下游填的内容）也不能不同步（骨架更新传不下去）。用哨兵块切开：

```
# <标题>                      ← H1，块外
（frontmatter 若有，在 H1 之上，块外）
<!-- template:begin -->
… 模板拥有的骨架/doctrine（sync 只替换这一段）…
<!-- template:end -->

<!-- 项目自定义区（块外，sync 不碰）：下游在此追加项目特定内容 -->
```

- `template-sync.py` 对 merge 文件**只替换 begin/end 之间**；块外的自定义区与 frontmatter 原样保留。
- 下游**不要改块内**——要改模板骨架走 ②（上报 issue）。项目特定内容一律写块外自定义区。
- `validate-governance.py` 的 `check_merge_sentinels()` 强制每个 merge 文件都有成对哨兵，缺了即 FAIL
  （否则该文件会被 sync 整体跳过、静默漂移）。
- **已知边界**：frontmatter 在块外，不随 sync 更新（哨兵不能放 frontmatter 前，否则破坏 `^---` 解析）。
  frontmatter 的结构性变更需人工同步或把该文件改判为 framework。

## 什么算「框架层」

只有框架层变更才触发发版与 sync。分类的**唯一真源**是 `template-manifest.toml`。粗略地：
框架层 = `.agent/`、`.claude/{agents,skills,commands,hooks,settings}`、`scripts/` validator、
`.githooks/`、`.github/` CI/模板、以及混合文件里的 `template:` 哨兵块。项目层 =
`lab/`、`memory/`、`deliverables/`、`plans/`、`human/`、`PROJECT.md`、`DECISIONS.md`。
