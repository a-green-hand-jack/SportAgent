---
related_files:
  - ../ANATOMY.md
  - check-agent-harness.py
  - check-anatomy-drift.py
  - validate-governance.py
  - adopt-existing-repo.py
  - check-adoption-integrity.py
  - sync-codex-adapters.py
  - bump-template-version.py
  - template-sync.py
  - ../template-manifest.toml
  - ../VERSION
maintenance: |
  新增/删除检查脚本时同 commit 更新本表。检查项与 .agent/ doctrine 对应关系变化时也更新。
---

# scripts/ ANATOMY

## What this is

repo 的可运行门禁层与迁移工具层。validator 无第三方硬依赖，只读、只报告、返回退出码；
adoption 脚本用于把外部 repo 收敛成本模板形态，并自带 proof/integrity 检查；
Codex adapter 同步脚本把 `.claude/` canonical 能力生成到 `.codex/` 与 `.agents/`。

## Components

| 文件 | 角色 | 对应 doctrine |
| --- | --- | --- |
| `check-agent-harness.py` | 结构/必需文件/根污染/四件套/能力索引/settings/DESIGN 清单 校验 | `.agent/repo-editing-guardrails.md` · `repo-documentation-topology.md` |
| `check-anatomy-drift.py` | ANATOMY related_files 与 line citation 漂移 + 120 行硬上限 | `.agent/anatomy-protocol.md` |
| `validate-governance.py` | 聚合上两者 + gitignore/YAML/tracked-bytes + 证据链一致性(overclaim 拦截) | `.agent/action-boundary.md` · `artifact-policy.md` · `principles.md` |
| `check-same-commit.py` | same-commit rule：结构改动(A/D/R)未同变更集更新对应 ANATOMY → 拦。diff 驱动，不进 governance；由 `.githooks/pre-commit` + CI 调用 | `.agent/anatomy-protocol.md` |
| `adopt-existing-repo.py` | 分 phase 迁移已有 Git repo：discover/baseline/scaffold/normalize/prove | `plans/20260709-adopt-existing-repo.zh.md` · `.claude/skills/adopt-existing-repo/SKILL.md` |
| `check-adoption-integrity.py` | 读取 adoption baseline，按 hash 证明原 tracked bytes 仍存在 | `.claude/skills/adopt-existing-repo/SKILL.md` |
| `sync-codex-adapters.py` | 从 `.claude/agents` / `skills` / `commands` 生成并校验 Codex adapters | `.agent/tool-skill-interface.md` |
| `bump-template-version.py` | 按 agent 判定的 level 递增 `VERSION`、更 `CHANGELOG.md`、打本地 git tag | `.agent/template-versioning-policy.md` |
| `template-sync.py` | 下游按 `template-manifest.toml` 追平上游框架层：覆盖/保护/scaffold/merge + 重建适配 + 验收 | `.agent/template-versioning-policy.md` · `template-manifest.toml` |

## Connections

Inbound:
- `.github/workflows/` CI 调用 `validate-governance.py --strict` 与 `check-same-commit.py --against`。
- `.githooks/pre-commit` 调用 `check-same-commit.py --staged`。
- `.claude/settings.json` 与 `.codex/rules/default.rules` 把关键脚本列入 allow。
- `.claude/commands/adopt-existing-repo.md` 调用 adoption 脚本。
- `.codex/agents/*.toml` 与 `.agents/skills/*/SKILL.md` 由 `sync-codex-adapters.py` 生成。

Outbound:
- `validate-governance.py` 以 subprocess 调用另两个脚本（用 `sys.executable`）。
- `check-adoption-integrity.py` 通过 `importlib` 加载 `adopt-existing-repo.py` 的
  `integrity_result()`，避免两份 hash 逻辑漂移。

## Notes

- validator 只能挡结构性漂移（missing file / out-of-range line / 根污染 / 误 track bytes）；语义正确性仍需 human/agent 打开代码验证。
- 退出码：0 通过，1 失败；`--strict` 让 warning 也算失败（用于 CI）。
