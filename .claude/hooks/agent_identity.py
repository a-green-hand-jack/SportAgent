#!/usr/bin/env python3
"""Agent identity resolver —— 解析当前 agent 的名字（`<persona>·<动作字>·<focus>`）。

doctrine 见 `.agent/agent-identity.md`。供 statusline `🤖 <name>` 段调用。

解析优先级（**快、无 subprocess**——statusline 高频渲染，不每帧 shell out 到 paseo）：
1. `AGENT_NAME` 环境变量（launcher / human 显式设）。
2. worktree 根的 `.agent-identity` 文件首行（Phase 2 自命名会写这里；也可手动写）。
3. 都没有 → None（statusline 不显示该段）。

Paseo 自命名（`PASEO_AGENT_ID` + `paseo rename/whoami`、写回 `.agent-identity`、入 roster）
留 Phase 2；本模块只负责「读」。无第三方依赖，失败静默降级。

CLI：
    python3 agent_identity.py --name        -> 打印名字或空
    python3 agent_identity.py --statusline  -> 打印 "🤖 <name>" 或空
"""
import os
import re
import sys
from pathlib import Path

# ANSI SGR 颜色序列（含 ESC 被 isprintable 剥掉后残留的可见片段 `[31m`/`[0m`）——防止名字里的
# 转义残渣进 statusline 变成垃圾字符或串色。只吃以 `m` 结尾的 SGR（真正的串色向量），
# 故 `[wip]auth` 这类含方括号的 focus 不误伤（`[0-9;]*` 后必须紧跟 `m`）。
_CSI = re.compile(r"\x1b?\[[0-9;]*m")

# 本文件在 .claude/hooks/ 下，parent 链多取一级到 worktree 根（与其它 hook 一致）。
REPO_ROOT = Path(__file__).resolve().parent.parent.parent
IDENTITY_FILE = REPO_ROOT / ".agent-identity"
MAX_LEN = 60  # 防御：过长名字截断，避免撑爆 statusline


def _clean(raw: str | None) -> str | None:
    if not raw:
        return None
    lines = raw.splitlines()
    name = lines[0].strip() if lines else ""
    name = _CSI.sub("", name)                                    # 剥 ANSI/CSI（含残片）
    name = "".join(ch for ch in name if ch.isprintable())        # 再剔其余非 printable
    name = name.strip()
    if not name:
        return None
    return name[:MAX_LEN]


def identity_name() -> str | None:
    """按优先级解析当前 agent 名字；无则 None。"""
    env = _clean(os.environ.get("AGENT_NAME"))
    if env:
        return env
    try:
        if IDENTITY_FILE.is_file():
            # errors="ignore"：非 UTF-8 文件（中文名字在 GBK/GB18030 编辑器写的）不抛
            # UnicodeDecodeError（它是 ValueError 非 OSError）——守住「绝不抛异常冒泡」契约。
            return _clean(IDENTITY_FILE.read_text(encoding="utf-8", errors="ignore"))
    except (OSError, ValueError):
        pass
    return None


def statusline_segment() -> str:
    name = identity_name()
    return f"🤖 {name}" if name else ""


def _cli() -> int:
    mode = sys.argv[1] if len(sys.argv) > 1 else "--name"
    try:
        if mode == "--statusline":
            print(statusline_segment())
        else:  # --name
            n = identity_name()
            print(n if n else "")
    except Exception:  # 兜底：绝不让调用方因本模块崩溃
        print("")
    return 0


if __name__ == "__main__":
    sys.exit(_cli())
