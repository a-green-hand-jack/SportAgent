#!/usr/bin/env python3
"""SubagentStop advisory hook。

在 subagent 结束时，向 `.claude/agent-reports/index.md` 追加一行索引，
把「主线程只接摘要、长报告落盘」的约定（见 .agent/behavior-contract.md）
变成可自动维护的痕迹，而不是靠 human 记忆。

这是 advisory：永远 exit 0，解析失败也不阻断工作流。它只记录发生了一次
subagent 结束，帮助 fresh session / branch-reporter 知道去哪里找报告。

无第三方依赖。
"""
import datetime
import json
import os
import sys
from pathlib import Path

# 锚定到仓库根，不假设 cwd == 仓库根（cwd 漂移进嵌套仓库时，裸相对路径会在
# 错误位置创建目录/写文件）。本文件在 `.claude/hooks/` 下，parent 链需比
# `scripts/*.py` 的锚定多取一级。
REPO_ROOT = Path(__file__).resolve().parent.parent.parent
REPORTS_DIR = str(REPO_ROOT / ".claude" / "agent-reports")
INDEX_FILE = os.path.join(REPORTS_DIR, "index.md")
HEADER = (
    "# agent-reports 索引\n\n"
    "> 自动维护（`subagent_report_index.py`）。每行 = 一次 subagent 结束。\n"
    "> 长报告本体由 subagent 写成本目录下的 `<task>.md`；本文件只记时间线。\n\n"
    "| 时间 (UTC) | agent | session |\n"
    "| --- | --- | --- |\n"
)


def main() -> None:
    raw = sys.stdin.read()
    event: dict = {}
    if raw.strip():
        try:
            event = json.loads(raw)
        except json.JSONDecodeError:
            event = {}

    # 字段名随 Claude Code 版本可能不同——全部做保守取值。
    agent = (
        event.get("subagent_type")
        or event.get("agent_type")
        or event.get("agent")
        or "unknown"
    )
    session = event.get("session_id") or event.get("session") or "-"
    ts = datetime.datetime.now(datetime.timezone.utc).strftime("%Y-%m-%d %H:%M")

    try:
        os.makedirs(REPORTS_DIR, exist_ok=True)
        if not os.path.exists(INDEX_FILE):
            with open(INDEX_FILE, "w", encoding="utf-8") as f:
                f.write(HEADER)
        with open(INDEX_FILE, "a", encoding="utf-8") as f:
            f.write(f"| {ts} | {agent} | {session} |\n")
    except OSError:
        pass  # advisory：写不了也不阻断

    sys.exit(0)


if __name__ == "__main__":
    main()
