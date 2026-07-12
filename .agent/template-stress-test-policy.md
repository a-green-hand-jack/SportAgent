# 模板压力测试政策

模板自己也会漂移。防漂移不能只靠"改的人记得测",而要把"多大改动需要多深的测试"写成
规则,并把每次测试的结果登记成可追溯的记录——即使测试对象是模板自己,也要有真实
case、真实证据,不能靠空模板自测蒙混过关。

## 流水线

```
选择/构建 case（真实、非平凡的外部项目或场景）
→ 迁移/复现进模板结构
→ 按本文件的分级判断测试深度
→ 演练相关 subagent / skill / command，跑对抗性探针
→ 写发现（template gap / validator 按预期工作 / 文档摩擦 / case ledger 债务 / 迁移执行失误）
→ 决定修复范围（记录与修复分离，修复走独立分支/PR）
→ 独立复验（涉及 session-cached 配置的修复需要全新顶层 session）
→ 登记进 lab/docs/audits/stress-test-ledger.yaml
```

具体步骤见 `.claude/skills/template-stress-test/SKILL.md`。

## repo surface

```
lab/docs/audits/<case>-report.md                 case 完整报告
lab/docs/audits/<case>-probe-catalog.md（可选）    case 具体探针记录（有历史价值时才建）
lab/docs/audits/stress-test-ledger.yaml           多 case 登记账（纪律面维护，非 validator 对象）
.claude/skills/template-stress-test/references/
  probe-surface-catalog.md                        面向未来的可复用探针清单，随模板演化追加
```

## 变更幅度 → 测试深度

首版分级(2026-07-09,来自 ELF case round 1-4 的实际经验),后续随更多 case 积累校准,
不假装现在就是精确阈值:

| 变更幅度 | 例子 | 所需测试深度 |
| --- | --- | --- |
| 纯文档/措辞改动 | 改 README 措辞、修 typo | 不需要压力测试 |
| 新增/改一个 subagent、skill、command | 新增一个 skill(如本次的 `template-stress-test` 自己) | 只需针对该表面的定向 smoke(如：用 `Skill` 工具真实调用一次,确认内容自洽),不需要整个 case 回放 |
| 改 validator、hook、Claude `settings.json` / Codex rules 权限面 | 新增/改一条 validator 检查、改 hook 锚定方式 | 需要完整对抗性探针矩阵(mutate→assert→revert,ELF case round 3 P0/P1 那种规模) |
| 改 `lab/`/`deliverables/`/`memory/` 的结构形状本身 | 新增顶层子目录、改四件套约定 | 需要完整 case-based 回放(ELF case round 1-3 那种规模),且应该用不止一个 case 交叉验证 |

## 登记账定位

`lab/docs/audits/stress-test-ledger.yaml` 是 human/agent 纪律面维护的记录,**不受**
`scripts/validate-governance.py` 覆盖(该脚本的 `check_yaml()` 只扫描
`lab/research|artifacts|data|models` 四个目录)。这与 `lab/recipes/claude-code/*.yaml`、
`lab/evals/cc-workflow/*.yaml` 同一定位——如果未来发现这类"文档说是裁决面但代码从没
校验"的落差(参见 P1-4 的教训),再单独决定要不要升级为机器强制。

## 触发压力测试

- 模板新增一类机制(新 validator/新 hook/新 subagent 类别/新 skill 类别)时。
- 模板对 `lab/`/`deliverables/`/`memory/` 结构做过一轮较大调整之后。
- 想验证某个 bug 修复是否真的解决时(尤其是涉及 session 启动时加载的配置——不能靠
  同一个 session 自证,见 ELF case F10 的教训)。
- 定期(建议每次模板版本有实质性变化时至少跑一次 targeted-smoke 级别的复查)。

## 与既有 doctrine 的关系

- 与 `.agent/claude-code-recipe-policy.md` 平行:后者管"Claude Code 使用技巧"的
  漂移,本文件管"模板自身机制"的漂移。两者结构故意保持一致(pipeline / repo surface /
  分级 / 触发条件),降低认知负担。
- 与 `.agent/anatomy-protocol.md` 互补:anatomy 防的是"结构描述 vs 实际结构"漂移,
  本文件防的是"机制声称的行为 vs 实际行为"漂移。
- 与 `.agent/repo-editing-guardrails.md` 互补:后者管改 repo 的门禁流程本身,本文件
  管改完之后需要多深的测试才能确认没引入回归。
