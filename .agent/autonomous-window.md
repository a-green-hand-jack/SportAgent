# 自主窗口（Autonomous Window）

human 有时需要授权一段**无人值守**时间：出门、睡觉，但任务得继续跑。原则是：

> **human 明确 allow 之后，就不要在被授权的动作上反复打断。**
> 但"授权自主"不等于"拆掉护栏"——红线由 hook 地板守住，它不随 allow 消失。

## 两层，性质不同

| 层 | 谁 | 自主窗口时 |
| --- | --- | --- |
| permission（allow/ask/deny，Claude `settings.json`/`settings.local.json` 或 Codex rules/permission mode） | 可调 | 按 human 明确授权放宽 |
| hook 地板（`.claude/hooks/pre_tool_guard.py`） | **不可调** | 照常拦截，permission 放开也拦得住 |

把"绝对不能发生"下沉到 hook（破坏性删除、写/删数据·产物·checkpoint bytes、push `main`/`master`），
只把"有人在就确认一下"留在 `ask`。于是放开 `ask` 才安全——致命动作根本不在可放宽的这层。

## 协议

```
1. 定义窗口：objective / success criteria / allowed·forbidden paths / 停止条件 / 预计时长。
   写进 memory/current-status.md（+ session-tree.md 若有子任务）。
2. 睡前先过 human-gate：不可逆/贵的动作（启动训练、push main、merge、加依赖）
   由 human 现在手动触发或明确单次放行；不要留给自主段自动做。
3. 授权：Claude Code 可 `cp .claude/settings.local.json.example .claude/settings.local.json`；
   Codex 用本次 task 的 permission mode / approved rules。只保留 THIS TASK 真需要的 allow 条目（宁少勿多）。
   这就是"明确的 allow"。
4. 跑有界循环：agent 只做被授权 + allow 的低风险动作（监控、定向重跑、写 summary、
   checkpoint-writer、commit、push topic 分支）。持续把状态写进 current-status.md。
5. 地板照常：hook 拦下任何红线；push main 需命令带 `CLAUDE_ALLOW_PUSH_MAIN=1` 或
   `CODEX_ALLOW_PUSH_MAIN=1`（显式单次）。
6. human 返回：review current-status.md → rm .claude/settings.local.json 收回授权。
```

## push 的分支感知

- topic / 实验分支 push：`allow`，不打断。
- `main` / `master` push：hook 拦，需 human 明确放行——命令前加 `CLAUDE_ALLOW_PUSH_MAIN=1 `，
  或 session 内 `export CLAUDE_ALLOW_PUSH_MAIN=1` / `export CODEX_ALLOW_PUSH_MAIN=1`。这是**显式**动作，不会被自主窗口自动获得。

## 别放进自主档的（即使过夜）

`kill`/重启训练、`gh pr merge`、`uv add`/`uv sync`、删任何 bytes、push `main`。
这些留给睡前的 human-gate，或本就锁在 hook 地板里。

## fail-safe

明确 forbidden paths + 停止条件；worktree 隔离让 blast radius 有界；
状态持续落 `memory/current-status.md`（天亮能 review）。宁可任务停下等 human，不可越红线继续。
