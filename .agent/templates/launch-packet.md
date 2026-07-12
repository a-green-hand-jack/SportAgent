# Subagent Launch Packet 模板

派发 child agent 前由 main / `subagent-router-agent` 生成。见 `.agent/model-routing-policy.md`。

```
agent_type:          <repo-researcher | feature-worker | test-runner | ...>
task:                <一句话可收敛任务>
role:                <impl | ui | research | planning | audit>
budget tier:         <0-4>
recommended provider:<codex | claude_code | paseo provider string>
recommended model:   <fast | standard | strong>
recommended effort:  <low | medium | high>
quota snapshot:      <current/weekly remaining + reset for Codex and Claude Code>
usage velocity:      <recent token/message burn proxy>
paseo preference:    <role default provider or missing/defaulted>
allowed paths:       <可读/可写路径>
forbidden paths:     <绝对不碰>
tools:               <允许工具>
context budget:      <如 read-only / <200 lines log>
evidence required:   <返回什么算完成>
stop condition:      <何时停>
escalate condition:  <何时上报 main / 升 tier>
self-check:          <每次写操作（Edit/Write/git）前先 pwd + git rev-parse --show-toplevel 核对所在 worktree，不要只在任务开头 cd 一次就假设之后都对>
report path:         <.claude/agent-reports/<task>.md>
```
