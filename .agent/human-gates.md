# Human Gates

外部副作用与不可逆动作必须经过人类审批点。agent 可以**准备**，但不能**触发**。

## 必须门禁的动作

| 动作 | 为什么 | agent 可做的准备 |
| --- | --- | --- |
| 建远端 repo / 首次推到新远端 / 改远端基础设施 | 外发、不可逆、可能被索引缓存 | 写好 commit、给出 diff 摘要 |
| 开/合 PR、merge | 影响共享分支 | 起草 PR body（evidence + risks） |
| release / 更新 deliverables 对外材料 | 影响导师/合作者可见 | 起草并标注 evidence 支持 |
| 启动/kill/restart 训练或远端作业 | 真实计算成本 | 准备可复现 launch 命令 + checklist |
| 删除/移动 data / checkpoint / run bytes | 不可逆、毁事实来源 | 生成归档提案，不执行 |
| 新增依赖 | 影响可复现环境 | 说明必要性与最小集 |
| promote 结果为 paper claim | 证据升级 | 附 run id/config/commit/metric + fresh verifier 结论 |

> 例外（分支感知 push）：`git push` 到 **topic / 实验分支** 是 `allow`——agent 可做，不打断。
> push 到 `main`/`master` 由 hook 地板拦，需 human 显式放行 `CLAUDE_ALLOW_PUSH_MAIN=1`
> 或 `CODEX_ALLOW_PUSH_MAIN=1`（单次），见 `.agent/autonomous-window.md`。开 PR / merge /
> release / 建远端 repo 仍是完整门禁。

## 门禁形态

- 机器层：`.claude/settings.json` 与 `.codex/rules/default.rules` 里对应 `ask` / `deny` / `prompt`；
  `PreToolUse(Bash|Edit|Write|apply_patch)` hook。
- 流程层：`.github/pull_request_template.md` + `CODEOWNERS` review。
- 记录层：批准与理由落到 `human/decisions/`。

## 提示格式

请求门禁时，agent 给出：动作、影响半径、可逆性、已做准备、期望批准范围（一次性 / 本 session / 持久）。批准仅在被授予的范围内有效，不自动延伸到下一个上下文。
