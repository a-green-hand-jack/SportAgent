#!/usr/bin/env python3
"""PostToolUse advisory hook（Track 0 方案 B："中文审阅安全网"）。

背景：`.agent/behavior-contract.md` "文档默认语言" 一节要求书面文档默认使用中文，
但历史上已发生过至少一次疏漏（PR #1 的标题/正文忘了用中文）。本 hook 是廉价的
第一道提醒：当 `Write`/`Edit` 命中"预期默认中文"的几类路径时，对写入内容做便宜的
字符统计式启发检查（数中日韩表意文字字符占比），怀疑忘了用中文时提醒一句。

这不是翻译判断——hook 是纯脚本，不能调用 LLM。真正的翻译/语言判断交给
`zh-review-gate` subagent（见 `.claude/agents/zh-review-gate.md`）；本 hook 只负责
用最低成本发现"疑似忘了用中文"的信号，然后建议派发那个 subagent 复核。

这是 advisory：永远 exit 0，只把提醒写到 stderr（会显示给 Claude），不阻断工作流。
解析失败 / 文件不存在 / 路径不匹配一律静默放行。

无第三方依赖。
"""
import fnmatch
import json
import os
import re
import sys
from pathlib import Path

# 锚定到仓库根，不假设 cwd == 仓库根（同类锚定见 pre_compact_memory_check.py /
# subagent_report_index.py 的修复说明）。本文件在 `.claude/hooks/` 下。
REPO_ROOT = Path(__file__).resolve().parent.parent.parent

# "预期默认中文"的路径模式（相对仓库根，fnmatch 风格）。
CHINESE_BY_DEFAULT_PATTERNS = (
    "human/reviews/**",
    "human/decisions/**",
    "lab/docs/audits/**",
    "DECISIONS.md",
)

# 启发式阈值：字符统计意义上的经验值，不追求精确——只用来发现"几乎没有中文"这种
# 明显信号。正文太短时噪声大，不检查；中日韩表意文字占比低于阈值时才提醒。
MIN_LENGTH_TO_CHECK = 200
CJK_RATIO_THRESHOLD = 0.05

CJK_RE = re.compile(
    r"[一-鿿㐀-䶿豈-﫿]"  # CJK 统一表意文字 + 扩展 A + 兼容表意文字
)


def _matches_chinese_by_default(rel_path: str) -> bool:
    rel_path = rel_path.replace(os.sep, "/")
    for pattern in CHINESE_BY_DEFAULT_PATTERNS:
        if fnmatch.fnmatch(rel_path, pattern):
            return True
    return False


def _patch_paths(patch_text: str) -> list[str]:
    paths: list[str] = []
    for line in patch_text.splitlines():
        for prefix in ("*** Add File: ", "*** Update File: ", "*** Move to: "):
            if line.startswith(prefix):
                paths.append(line[len(prefix) :].strip())
                break
    return paths


def _candidate_paths(event: dict) -> list[str]:
    tool_input = event.get("tool_input", {}) or {}
    paths: list[str] = []
    for key in ("file_path", "notebook_path"):
        value = tool_input.get(key)
        if value:
            paths.append(str(value))
    if event.get("tool_name") == "apply_patch":
        paths.extend(_patch_paths(tool_input.get("command", "") or ""))
    return paths


def _check_path(path: str) -> None:
    if not path:
        return
    try:
        abs_path = Path(path)
        if not abs_path.is_absolute():
            abs_path = REPO_ROOT / abs_path
        abs_path = abs_path.resolve()
        rel_path = str(abs_path.relative_to(REPO_ROOT))
    except (ValueError, OSError):
        return  # 不在仓库内 / 解析失败：不是本 hook 关心的路径

    if not _matches_chinese_by_default(rel_path):
        return

    try:
        text = abs_path.read_text(encoding="utf-8", errors="replace")
    except OSError:
        return

    stripped = text.strip()
    if len(stripped) < MIN_LENGTH_TO_CHECK:
        return  # 太短，噪声大，不判断

    cjk_count = len(CJK_RE.findall(text))
    ratio = cjk_count / len(text) if text else 0.0

    if ratio < CJK_RATIO_THRESHOLD:
        print(
            f"[zh_review_advisory] 提醒：{rel_path} 属于预期默认中文的路径，"
            f"但中日韩表意文字占比仅 {ratio:.1%}（阈值 {CJK_RATIO_THRESHOLD:.0%}），"
            "疑似忘了用中文（见 .agent/behavior-contract.md「文档默认语言」）。"
            "这只是便宜的字符统计启发，不是语言判断——建议派发 zh-review-gate "
            "subagent 复核并按需翻译改写；若这个文件本来就有理由用非中文，可忽略本提醒。",
            file=sys.stderr,
        )


def main() -> None:
    raw = sys.stdin.read()
    if not raw.strip():
        sys.exit(0)
    try:
        event = json.loads(raw)
    except json.JSONDecodeError:
        sys.exit(0)  # 保守放行

    for path in _candidate_paths(event):
        _check_path(path)

    sys.exit(0)


if __name__ == "__main__":
    main()
