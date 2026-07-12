#!/usr/bin/env python3
"""SessionStart continuity hook —— compact/clear 之后，把 memory/current-status.md
摘要回注新上下文，接续「我在干什么、下一步是什么」，不断档。

这是「优化短上下文连续性」那一点（human 提出）：PreCompact 提醒压缩前落盘，本 hook
负责压缩/清空后读回，一前一后闭环。

触发条件（跨表面）：
- Claude Code：SessionStart 且 source ∈ {compact, clear}。
- Codex：SessionStart 的 matcher 只含 startup|resume|clear（无 compact），compact 走独立的
  PostCompact 事件——故这里也认 hook_event_name == "PostCompact"。
startup/resume 是新开/续接，不回注。SessionStart/PostCompact 的 stdout（exit 0）并入新上下文
——这是回注通道。为避免回注本身又吃掉大量上下文，正文截断到上限。永远 exit 0。

无第三方依赖。锚定仓库根（不假设 cwd == 仓库根）。
"""
import json
import sys
import time
from pathlib import Path

# 本文件在 .claude/hooks/ 下，比 scripts/*.py 多一层，parent 链多取一级。
REPO_ROOT = Path(__file__).resolve().parent.parent.parent
STATUS_FILE = REPO_ROOT / "memory" / "current-status.md"
MAX_CHARS = 4000  # 回注上限，防止连续性本身再撑爆上下文
TRIGGER_SOURCES = {"compact", "clear"}


def main() -> None:
    try:
        payload = json.load(sys.stdin)
    except (ValueError, TypeError):
        sys.exit(0)
    if not isinstance(payload, dict):
        sys.exit(0)  # 合法但非对象的 stdin（如 `42`）不能 .get —— 守住「绝不抛异常」契约

    source = payload.get("source", "")
    event = payload.get("hook_event_name", "")
    # Claude: SessionStart(source=compact|clear)；Codex: 独立 PostCompact 事件 + SessionStart(clear)
    if source not in TRIGGER_SOURCES and event != "PostCompact":
        sys.exit(0)  # startup/resume 等不回注
    boundary = source if source in TRIGGER_SOURCES else "compact"

    if not STATUS_FILE.is_file():
        # 没有 status 文件也给个提示，让主 agent 知道该建
        print(
            f"[continuity] {boundary} 后未找到 {STATUS_FILE.name}。"
            "建议尽快用 checkpoint-writer 落盘当前状态，后续压缩才有连续性。"
        )
        sys.exit(0)

    try:
        text = STATUS_FILE.read_text(encoding="utf-8")
        age_min = int((time.time() - STATUS_FILE.stat().st_mtime) // 60)
    except OSError:
        sys.exit(0)

    truncated = text[:MAX_CHARS]
    tail = "\n…（已截断，完整见 memory/current-status.md）" if len(text) > MAX_CHARS else ""
    fresh = "新鲜" if age_min <= 30 else f"已 {age_min} 分钟未更新，可能滞后——请对照当前 git 状态"
    print(
        f"[continuity] {boundary} 后回注 memory/current-status.md（{fresh}）。"
        "以下为压缩/清空前的工作状态，据此接续，不要从零重建：\n\n"
        f"{truncated}{tail}"
    )
    sys.exit(0)


if __name__ == "__main__":
    main()
