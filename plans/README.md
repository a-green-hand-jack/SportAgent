# plans/

交互式中文 plan doc 的家。这是 human 与 Claude Code 的协商界面（比纯聊天 plan 更可恢复、可 review）。

- 命名：`<YYYYMMDD>-<topic>.zh.md`
- 模板：`.agent/templates/plan-doc.zh.md`
- 由 `interactive-plan-writer` subagent / `interactive-plan-doc` skill 维护。

操作流：Claude 写初稿 → human 在文件里批注 → Claude 读 git diff、收敛计划 → 每次采纳的修订做一个小 commit（若项目要求可追溯）。实现只在 scope / forbidden paths / verification 清楚后开始。

plan doc 是当前 session 的锚点：防止 Claude 漂移到额外动作，也防止 human 只凭记忆追踪「刚才到底决定了什么」。
