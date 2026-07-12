---
name: spawn
description: 当要唤起一个 subagent（in-session 跑完汇报，或起一个持久可交互的 Paseo 标签页 agent）时用；串起「发现有哪些 agent → 选型/packet → 人+主 agent 两层交代 → 出生即好名并入 roster」，替代凭直觉直接开 general-purpose worker。
---

> Codex adapter: generated from `.claude/skills/spawn/SKILL.md`. Do not edit this copy by hand; run `python scripts/sync-codex-adapters.py`.

# spawn —— 唤起 subagent（发现 + 选型 + 两层交代 + 命名）

把「派 subagent」从零散多步收敛成一条流程，并与 agent 身份 doctrine（`.agent/agent-identity.md`）打通：
子 agent **出生即有好名**（`persona·动作·focus`）、登记进花名册，而不是事后补 rename。

> keystone：launcher 是「易唤起」与「好命名」的交汇点——起 agent 时顺手 `--title` 好名 + 建 worktree +
> 选 profile + 入 roster，一次做对。

## 适用边界

- 适用：有一段可界定的子任务要交出去——搜索/实现/审查/监控/规划等。
- 不适用：scope 还没拆清（先 `interactive-plan-doc` 写 plan）；主 agent 顺手一步能做完；需要人类副作用（走 human gate）。

## 两种 spawn（先选一种）

| 模式 | 何时用 | 载体 | 命名 |
| --- | --- | --- | --- |
| **in-session 子 agent** | 一次性、跑完把结果汇报回主线程（如一轮 review、一次搜索） | `Task`/`Agent` 工具 | 主 agent 在交代里给它一个 doctrine 名（便于报告署名）；不占 Paseo 标签 |
| **Paseo-tab launcher（keystone）** | 需要**持久、可与 human 交互**的并行 agent（一个标签页一个 agent） | `paseo run` | **出生即命名**：`--title` + `--env AGENT_NAME=` 双表面命名 + 入 roster |

## 流程

### 1. 发现（有哪些 agent 能派）
```
python3 .claude/skills/spawn/scripts/list_agents.py         # name / 一句话用途 / tools / model
```
据「一句话用途」挑最贴合的 canonical agent（`.claude/agents/*.md`）。不确定就先看这张表，别默认 general-purpose。

### 2. 选型 + packet
走 `subagent-routing` skill：按 `.agent/model-routing-policy.md` 定 tier，读 quota 证据，选 provider/model/effort、收紧 tools、写清 scope/forbidden/验收/停止条件，产出 launch packet（模板 `.agent/templates/launch-packet.md`）。**派发前先路由**。

### 3. 两层交代（合成 launch prompt）
- **第一层 human brief**：human 启动本 skill 时给的意图（「去调查 X」「实现 Y」）。
- **第二层 main-agent brief**：主 agent 补齐 human 没说但子 agent 必需的——相关文件、scope、forbidden 路径、验收标准、回报格式、停止条件（多来自第 2 步 packet）。
- 两层拼成最终 launch prompt。保留人与主 agent 各自的意图注入，是本 skill 做成 skill（而非一键 command）的原因。

### 4. 命名（出生即好名）
据 `.agent/agent-identity.md` 的 `<persona·动作字·focus>`，按**子任务**选名：
- 调查→`斥候·查·<focus>`、实现→`干将·改·<focus>`、审查→`师爷·审·<focus>`、规划→`都督·统·<focus>`、
  文档→`主簿·记·<focus>`、测试→`巡检·测·<focus>`、实验→`博士·验·<focus>`、设计→`画师·设·<focus>`、git/整合→`校书·并·<focus>`。
- 唯一性靠 focus 区分；仍冲突加短 id。

### 5. 启动

**A. in-session 子 agent**：用 `Task`/`Agent` 工具，`subagent_type` = 第 1 步选的 agent，prompt = 第 3 步 launch prompt（开头点明「你是 `<第4步名>`，据此署名回报」）。跑完把摘要收回主线程，长报告落 `.claude/agent-reports/`。

**B. Paseo-tab launcher**：出生即双表面命名 + 入 roster。
```bash
NAME="师爷·审·窗口感知"            # 第 4 步选的名
SLUG="review-window"              # worktree 短名（kebab）
# --detach：持久并行 agent 必须后台起，否则 paseo run 会阻塞主 agent（还会把流式输出灌进 json.load）
# --title 命名 Paseo 标签；--env AGENT_NAME 让子 agent 的 statusline/身份 hook 认得自己
CHILD=$(paseo run --json --detach \
  --title "$NAME" \
  --env "AGENT_NAME=$NAME" \
  --worktree "$SLUG" \
  --provider claude \
  "<第3步的最终 launch prompt>" \
  | python3 -c 'import json,sys; d=json.load(sys.stdin); print(d.get("id") or d.get("agent",{}).get("id","")) if isinstance(d,dict) else print("")')
# 若 $CHILD 为空说明没取到 id（run --json 形状异常/未起成功）——先排查，别拿空 id 登记
if [ -z "$CHILD" ]; then echo "paseo run 未返回 agent id，检查 daemon/输出"; fi
# 把子 agent 登记进花名册（子 agent 已出生即命名，故只登记、不 rename）
python3 .claude/hooks/agent_name_set.py "$NAME" --register --paseo-id "$CHILD" --worktree "$SLUG"
```
- `--detach` 让 `paseo run` 立即返回子 agent 元数据（含 `id`）而不阻塞；id 提取对
  `{"id":…}` 与 `{"agent":{"id":…}}` 两种形状都稳。
- `--env AGENT_NAME=` 让子 agent 的 `agent_identity.py` 立刻解析到名字 → statusline 显示 `🤖 <name>`、
  身份 hook 认为「已命名」而**不再**注入自命名指令（与 Phase 2 一致）。
- 需要主 agent 等子 agent 跑完可用 `--wait-timeout <dur>`（那属于「同步子任务」，多数场景用 in-session 模式更合适）。
- runtime-agnostic：非 Paseo 表面就只用 in-session 模式；命名仍靠 `AGENT_NAME`/`.agent-identity`。

### 6. 收尾
- agent↔agent 通信：用花名册（`memory/agents-roster.md`）把 name 解析成 paseo-id，再 `paseo send <id> "<消息>"`（`send` 认 id 不认 name）。
- 子 agent 结束/归档：在 roster 该行标 done（不立即删，留痕）。

## 允许修改的路径

- `memory/agents-roster.md`（登记/更新活 agent 行——经 `agent_name_set.py` 维护）。
- `memory/branches/<slug>.md`（第 2 步 launch packet 引用）。
- 派发现场 issue/PR 文本、新建的 worktree。其余只读。

## 验证命令

```
python3 .claude/skills/spawn/scripts/list_agents.py           # 发现表能列全 16 个 agent
python3 .claude/hooks/agent_name_set.py "斥候·查·smoke" --register --paseo-id demo-id --worktree "b (wt)"
grep "demo-id" memory/agents-roster.md                        # 确认已登记该行
python scripts/validate-governance.py
```

## 失败时的 handoff

- 选不定 agent / tier 边界模糊：回 `subagent-routing` 的 handoff（升级人类定预算）。
- scope 无法界定：停止派发，转 `interactive-plan-doc` 先收敛。
- `paseo run` 不可用（非 Paseo 表面或 daemon 未起）：退回 in-session 模式，命名仍生效。
