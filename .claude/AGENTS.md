# .claude/ — AGENTS

<!-- template:begin -->

给维护本能力层的 agent。

## 允许改

- 新增/修改 `agents/*.md`、`skills/*/SKILL.md`、`commands/*.md`、`hooks/*.py`。
- 修改 `settings.json` 的 allow/ask/deny 与 hooks 映射——但每条高风险条目必须能在 `.agent/action-boundary.md` / `lab/infra/permissions/` 找到理由。

## 必须验证

- 改 `settings.json` 或 hooks 后：`python scripts/check-agent-harness.py`，并用 `/hooks` 或 debug mode 确认 hook 触发。
- 新增 agent/skill 必须有 frontmatter（name/description）与明确边界；没有索引的能力不算正式 surface。
- 改 `agents/`、`skills/` 或 `commands/` 后：运行 `python scripts/sync-codex-adapters.py`，保证 Codex adapters 同步。

## 禁止

- 把 repo 专属能力偷偷装到 user 全局。
- 让 hook 变大变复杂而无人审计（hook 以本机权限执行）。

## 演化

反复出现的轨迹用 `sub-agent-maker-agent` / `hook-maker-agent` / `workflow-recipe-harvester` 提炼成 draft，走 human review + branch/PR + validator 才启用。

<!-- template:end -->

<!-- 项目自定义区（template:end 之后，sync 不碰）：下游在此追加本项目特定内容；template:begin/end 块内是模板拥有的内容，如需改动请走 template-feedback 上报，勿在此直接改块内。 -->
