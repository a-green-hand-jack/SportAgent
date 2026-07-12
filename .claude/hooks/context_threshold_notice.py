#!/usr/bin/env python3
"""UserPromptSubmit advisory hook —— 上下文过半时把「该 checkpoint / 考虑压缩」
注入上下文，把主动压缩从「靠主 agent 自觉」变成「信号驱动」。

这是本模板缺的那半边（见 plans/20260711-context-orchestration.zh.md 诊断）：
statusline 只是让人看见占用；本 hook 让主 agent 在每轮开头「读到」建议。

硬边界（对齐 Codex 复核）：hook 只发信号，不 block、不自动 compact——真正按下
/compact 仍由宿主 CLI + 主 agent 在任务边界判断。因此本 hook 永远 exit 0。

阈值 65 / 80（human 定）。去重：同一 session 每档只提醒一次（marker 记已达最高档）。
token 精度来自共用 context_usage 模块（读 transcript usage 精确值）。

UserPromptSubmit 的 stdout（exit 0）会被并入本轮上下文——这正是注入建议的通道。
无第三方依赖。解析失败保守放行（静默 exit 0）。
"""
import json
import sys
import tempfile
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import context_usage  # noqa: E402  同目录共用 helper

YELLOW_AT = context_usage.YELLOW_AT  # 65
RED_AT = context_usage.RED_AT        # 80


def _marker_path(session_id: str) -> Path:
    safe = "".join(c for c in (session_id or "unknown") if c.isalnum() or c in "-_")
    return Path(tempfile.gettempdir()) / f"claude_ctx_notice_{safe or 'unknown'}"


def _already_notified_tier(marker: Path) -> int:
    try:
        return int(marker.read_text().strip())
    except (OSError, ValueError):
        return 0


def _record_tier(marker: Path, tier: int) -> None:
    try:
        marker.write_text(str(tier))
    except OSError:
        pass  # 去重是尽力而为；写不了顶多多提醒一次，不致命


def main() -> None:
    try:
        payload = json.load(sys.stdin)
    except (ValueError, TypeError):
        sys.exit(0)  # 读不了 stdin → 保守放行
    if not isinstance(payload, dict):
        sys.exit(0)  # 合法但非对象的 stdin（如 `42`）不能 .get —— 守住「绝不抛异常」契约

    transcript = payload.get("transcript_path")
    session_id = payload.get("session_id", "")
    # 传 session_id：让 percent 读 statusline 写下的本会话窗口缓存，从而对 1M 等窗口有感知
    pct = context_usage.percent(transcript, session_id=session_id)
    if pct is None:
        sys.exit(0)  # 无数据 → 不打扰

    tier = RED_AT if pct >= RED_AT else (YELLOW_AT if pct >= YELLOW_AT else 0)
    if tier == 0:
        sys.exit(0)

    marker = _marker_path(session_id)
    if _already_notified_tier(marker) >= tier:
        sys.exit(0)  # 该档（或更高档）已提醒过 —— 不刷屏
    _record_tier(marker, tier)

    if tier >= RED_AT:
        msg = (
            f"[context] 已用 ~{pct}%（≥{RED_AT}%）。现在就落盘并压缩："
            "先用 checkpoint-writer 更新 memory/current-status.md（objective/决策/改动文件/下一步），"
            "然后在最近的任务边界 /compact 或 /clear。参考 .agent/checklists/session-boundary.md。"
        )
    else:
        msg = (
            f"[context] 已用 ~{pct}%（≥{YELLOW_AT}%）。建议：派 checkpoint-writer 落盘 "
            "memory/current-status.md；接近任务边界可考虑 /compact。避免拖到过满再压缩。"
        )
    print(msg)  # stdout → 并入本轮上下文
    sys.exit(0)


if __name__ == "__main__":
    main()
