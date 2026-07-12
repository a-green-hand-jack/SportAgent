#!/usr/bin/env bash
# repo-local statusline：把 model / 目录 / git 分支 / worktree / cost 变成可见仪表盘。
# 对齐 .agent/principles.md「没有仪表盘就别开长途」。
#
# Claude Code 通过 stdin 传入 JSON（model / workspace / cost 等字段随版本可能变化）。
# 本脚本防御式解析：无 jq 或字段缺失时优雅降级为最小行，绝不报错、绝不阻断。
# adopter 可直接删除 settings.json 的 statusLine 段以回退到全局 statusline。

input="$(cat)"

# --- 取字段：有 jq 用 jq，否则留空降级 ---
model=""; cur_dir=""; cost=""; transcript=""; model_id=""; session_id=""
if command -v jq >/dev/null 2>&1; then
  model="$(printf '%s' "$input"  | jq -r '.model.display_name // empty' 2>/dev/null)"
  cur_dir="$(printf '%s' "$input" | jq -r '.workspace.current_dir // .cwd // empty' 2>/dev/null)"
  cost="$(printf '%s' "$input"    | jq -r '(.cost.total_cost_usd // empty) | select(. != null)' 2>/dev/null)"
  transcript="$(printf '%s' "$input" | jq -r '.transcript_path // empty' 2>/dev/null)"
  model_id="$(printf '%s' "$input"   | jq -r '.model.id // empty' 2>/dev/null)"
  session_id="$(printf '%s' "$input" | jq -r '.session_id // empty' 2>/dev/null)"
fi

# 目录：优先 JSON，退回 $PWD
[ -z "$cur_dir" ] && cur_dir="$PWD"
dir_name="$(basename "$cur_dir" 2>/dev/null)"

# git 分支 + worktree 名（best-effort，非 git 仓库则留空）
branch=""; worktree=""
if git -C "$cur_dir" rev-parse --is-inside-work-tree >/dev/null 2>&1; then
  branch="$(git -C "$cur_dir" branch --show-current 2>/dev/null)"
  [ -z "$branch" ] && branch="$(git -C "$cur_dir" rev-parse --short HEAD 2>/dev/null)"
  top="$(git -C "$cur_dir" rev-parse --show-toplevel 2>/dev/null)"
  [ -n "$top" ] && worktree="$(basename "$top")"
fi

# agent 身份（🤖 <name>）：多 agent 并行时一眼分清每个 tab 在做什么。
# 委托 agent_identity.py 解析（AGENT_NAME env / .agent-identity 文件）。无名则空串降级。
idseg=""
idhelper="$(dirname "$0")/hooks/agent_identity.py"
[ -f "$idhelper" ] && idseg="$(python3 "$idhelper" --statusline 2>/dev/null)"

# context 占用表（🧠 NN%，≥65% 黄/≥80% 红）：委托共用 helper 读 transcript usage
# 求精确 token%。无 transcript / 无 python / helper 失败 → 空串降级，绝不阻断。
ctx=""
if [ -n "$transcript" ]; then
  helper="$(dirname "$0")/hooks/context_usage.py"
  # 传 --session：statusline 从 model.id 认出窗口后写会话缓存，让无 model 信息的 hook 也感知
  [ -f "$helper" ] && ctx="$(python3 "$helper" --statusline "$transcript" --model "$model_id" --session "$session_id" 2>/dev/null)"
fi

# --- 拼装：只展示拿到的字段 ---
parts=()
[ -n "$idseg" ]    && parts+=("$idseg")   # agent 名放最左，最易一眼扫到
[ -n "$model" ]    && parts+=("$model")
[ -n "$dir_name" ] && parts+=("📁 $dir_name")
[ -n "$branch" ]   && parts+=("⎇ $branch")
[ -n "$worktree" ] && [ "$worktree" != "$dir_name" ] && parts+=("wt:$worktree")
[ -n "$ctx" ]      && parts+=("$ctx")
if [ -n "$cost" ]; then
  printf -v cost_fmt '$%.4f' "$cost" 2>/dev/null && parts+=("$cost_fmt")
fi

# 用 " | " 连接
out=""
for p in "${parts[@]}"; do
  [ -z "$out" ] && out="$p" || out="$out | $p"
done
[ -z "$out" ] && out="claude-code"
printf '%s' "$out"
