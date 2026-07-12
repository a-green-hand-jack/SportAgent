#!/usr/bin/env python3
"""Agent identity hook —— 让「自命名」默认发生、并在压缩/续接后重申身份。

两个事件（同一脚本，按 hook_event_name 分支）：
- **UserPromptSubmit**：若本 agent 还没名字 → 注入「按 doctrine 自命名」指令（每 session 一次）。
  之所以放首个 prompt 而非启动：此刻任务已知，agent 才能选出有意义的 focus。
- **SessionStart**：若已有名字 → 注入「你是 <name>」自知（compact/clear/resume 后不失忆）。

自命名默认开启（human 定 = 选项 A）：指令默认注入；真正 `paseo rename` 由 agent 调
`agent_name_set.py` 执行，`AGENT_NO_AUTORENAME=1` 可关掉 rename 那步。

注入通道：UserPromptSubmit / SessionStart 的 stdout（exit 0）并入上下文。永远 exit 0、不 raise。
"""
import json
import sys
import tempfile
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import agent_identity  # noqa: E402

DOCTRINE = ".agent/agent-identity.md"
SETTER = ".claude/hooks/agent_name_set.py"


def _prompt_marker(session_id: str) -> Path:
    safe = "".join(c for c in (session_id or "unknown") if c.isalnum() or c in "-_")
    return Path(tempfile.gettempdir()) / f"claude_agent_named_{safe or 'unknown'}"


def _naming_directive() -> str:
    return (
        "[identity] 本 agent 还没身份名。请按 " + DOCTRINE + " 的 `<persona·动作字·focus>` 规则，"
        "据当前任务选一个名（persona=角色人格，动作字=在做什么，focus=话题），然后运行："
        f"\n    python3 {SETTER} \"<你选的名>\"\n"
        "它会写 .agent-identity + 自动 paseo rename（清理垃圾 tab 名）+ 登记 memory/agents-roster.md。"
        "例：调查类→`斥候·查·xxx`，改代码→`干将·改·xxx`，审查→`师爷·审·xxx`。"
    )


def main() -> None:
    try:
        payload = json.load(sys.stdin)
    except (ValueError, TypeError):
        sys.exit(0)
    if not isinstance(payload, dict):
        sys.exit(0)

    event = payload.get("hook_event_name", "")
    name = agent_identity.identity_name()

    if event == "SessionStart":
        # 已命名 → 重申身份；未命名 → 交给首个 UserPromptSubmit（此刻任务未知）
        if name:
            print(f"[identity] 你是 **{name}**。据此身份工作、与其它 agent 交流。")
        sys.exit(0)

    # 默认视作 UserPromptSubmit
    if name:
        sys.exit(0)  # 已有名字，不打扰
    session_id = payload.get("session_id", "")
    marker = _prompt_marker(session_id)
    if marker.exists():
        sys.exit(0)  # 本 session 已提示过一次
    try:
        marker.write_text("1")
    except OSError:
        pass  # 去重尽力而为
    print(_naming_directive())
    sys.exit(0)


if __name__ == "__main__":
    main()
