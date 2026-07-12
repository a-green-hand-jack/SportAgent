#!/usr/bin/env python3
"""Context usage helper —— 从 transcript 算「精确」上下文占用，并对本会话的**窗口大小**有感知。

单一真源：块 1（statusline 仪表盘）与块 2（阈值提醒 hook）共用本模块，避免两处各写一套
估算逻辑而漂移。

精确来源（已由探测确认，见 plans/20260711-context-orchestration.zh.md）：
transcript JSONL 最后一条带 usage 的 message 的 `message.usage`：
    context_tokens = input_tokens + cache_read_input_tokens + cache_creation_input_tokens

窗口感知（关键：hook stdin 无 model，transcript 又只存 base id 不带 `[1m]`）——按优先级：
  1. 显式 --window / window 参数
  2. 环境 CLAUDE_CTX_WINDOW
  3. 本会话窗口缓存（statusline 从 `.model.id` 认出 `[1m]`→写缓存；hook 据 session_id 读）
  4. model id 推断（`[1m]`→1M；否则 base 表，默认 200k）
  5. 证据推断（transcript 观测到的最大上下文 > 某档 → 窗口至少那么大，snap 到已知档）
statusline 有 `.model.id`（含 `[1m]`）能即时认出并写缓存，让**无 model 信息的 hook** 也据此感知；
缓存缺失时用证据兜底；证据不足才落回 200k（安全方向：宁早提醒不漏）。

无第三方依赖。可 import，也可 CLI：
    python3 context_usage.py --tokens     <transcript>
    python3 context_usage.py --percent    <transcript> [--window N|--model ID|--session SID]
    python3 context_usage.py --statusline <transcript> [--window N|--model ID|--session SID]
所有失败路径静默降级（打印空 / 返回 None）+ exit 0，绝不抛异常冒泡、绝不阻断调用方。
"""
import argparse
import json
import os
import sys
import tempfile

DEFAULT_WINDOW = 200_000
KNOWN_WINDOWS = (200_000, 1_000_000)  # 已知窗口档，证据推断 snap 到这些档
YELLOW_AT = 65  # ≥ 黄
RED_AT = 80     # ≥ 红


def window_for_model(model_id: str | None) -> int:
    """按 model id 推窗口。识别 1M 上下文（如 opus-4-8[1m]）；否则默认 200k。

    注意：transcript 存 base id（`claude-opus-4-8`，无 `[1m]`）→ 从 transcript 认不出 1M；
    只有 statusline 的 `.model.id` 带 `[1m]` 标记，故 1M 感知主要靠 statusline + 缓存 + 证据。
    """
    if not model_id:
        return DEFAULT_WINDOW
    mid = model_id.lower()
    if "[1m]" in mid or "-1m" in mid or "_1m" in mid or "1m]" in mid:
        return 1_000_000
    return DEFAULT_WINDOW


def _snap_up(tokens: int) -> int:
    """把观测 token 数向上 snap 到最小的已知窗口档；超过所有档则用 token 本身。"""
    for w in KNOWN_WINDOWS:
        if tokens <= w:
            return w
    return tokens


def _window_cache_path(session_id: str | None) -> str | None:
    if not session_id:
        return None
    safe = "".join(c for c in session_id if c.isalnum() or c in "-_")
    if not safe:
        return None
    return os.path.join(tempfile.gettempdir(), f"claude_ctx_window_{safe}")


def read_window_cache(session_id: str | None) -> int | None:
    path = _window_cache_path(session_id)
    if not path:
        return None
    try:
        v = int(open(path).read().strip())
        return v if v > 0 else None
    except (OSError, ValueError):
        return None


def write_window_cache(session_id: str | None, window: int) -> None:
    path = _window_cache_path(session_id)
    if not path or window <= 0:
        return
    # 原子写：写临时文件后 rename，避免高频写与 hook 读之间读到半写入脏值。
    tmp = f"{path}.{os.getpid()}.tmp"
    try:
        with open(tmp, "w") as fh:
            fh.write(str(window))
        os.replace(tmp, path)
    except OSError:
        try:
            os.unlink(tmp)
        except OSError:
            pass
        # 缓存是尽力而为，写不了不致命


def resolve_window(
    window: int | None = None,
    model_id: str | None = None,
    session_id: str | None = None,
    observed_tokens: int | None = None,
) -> int:
    """按优先级解析本会话有效窗口（见模块 docstring）。"""
    if window and window > 0:
        return window
    env = os.environ.get("CLAUDE_CTX_WINDOW", "").strip()
    if env:
        try:
            v = int(env)
            if v > 0:
                return v
        except ValueError:
            pass
    cached = read_window_cache(session_id)
    if cached:
        return cached
    base = window_for_model(model_id)
    # 证据兜底：若观测到的上下文已超过 base，窗口显然更大 → snap 到能容纳它的已知档
    if observed_tokens and observed_tokens > base:
        base = _snap_up(observed_tokens)
    return base


def _int(v: object) -> int:
    return v if isinstance(v, int) and v >= 0 else 0


def _usage_sum(usage: dict) -> int:
    return (
        _int(usage.get("input_tokens"))
        + _int(usage.get("cache_read_input_tokens"))
        + _int(usage.get("cache_creation_input_tokens"))
    )


def _scan_transcript(transcript_path: str | None) -> tuple[int | None, str | None, int]:
    """单次遍历 transcript，返回 (当前上下文 token, 最后 model id, 历史观测最大上下文 token)。

    单遍是刻意的：percent 默认路径既要 token 又要 model / 证据，合并成一次读避免大 transcript
    （接近满时可达数十 MB、每轮 UserPromptSubmit 触发）被反复读。
    对非 dict 行（半写入/畸形产出的合法标量，如 `42`、`"x"`）显式跳过，确保「绝不抛异常
    冒泡」的契约不被 obj.get 破坏。找不到/读不了 → (None, model 或 None, 0)。
    """
    if not transcript_path or not os.path.isfile(transcript_path):
        return (None, None, 0)
    last_usage = None
    last_model = None
    max_tokens = 0
    try:
        with open(transcript_path, encoding="utf-8") as fh:
            for line in fh:
                line = line.strip()
                if not line:
                    continue
                try:
                    obj = json.loads(line)
                except (ValueError, TypeError):
                    continue
                if not isinstance(obj, dict):
                    continue  # 合法但非对象的行不能 .get，跳过
                msg = obj.get("message")
                if not isinstance(msg, dict):
                    continue
                usage = msg.get("usage")
                if isinstance(usage, dict) and any(
                    k in usage
                    for k in ("input_tokens", "cache_read_input_tokens", "cache_creation_input_tokens")
                ):
                    last_usage = usage  # 取最后一条 —— 最贴近当前上下文
                    max_tokens = max(max_tokens, _usage_sum(usage))
                model = msg.get("model")
                if isinstance(model, str):
                    last_model = model
    except OSError:
        return (None, last_model, max_tokens)
    tokens = None if last_usage is None else _usage_sum(last_usage)
    return (tokens, last_model, max_tokens)


def context_tokens(transcript_path: str | None) -> int | None:
    """读 transcript 求当前上下文精确 token（找不到/无 usage → None）。"""
    return _scan_transcript(transcript_path)[0]


def model_from_transcript(transcript_path: str | None) -> str | None:
    """从 transcript 取最后 model id（见 _scan_transcript）。"""
    return _scan_transcript(transcript_path)[1]


def percent(
    transcript_path: str | None,
    window: int | None = None,
    model_id: str | None = None,
    session_id: str | None = None,
) -> int | None:
    tokens, transcript_model, max_tokens = _scan_transcript(transcript_path)  # 单遍拿齐
    if tokens is None:
        return None
    win = resolve_window(window, model_id or transcript_model, session_id, max_tokens)
    if win <= 0:
        return None
    return min(999, round(100 * tokens / win))


def _colorize(text: str, pct: int) -> str:
    """按阈值着色；NO_COLOR 环境变量置位时不加 ANSI（statusline 期望输出 ANSI，故不判 tty）。"""
    if os.environ.get("NO_COLOR"):
        return text
    if pct >= RED_AT:
        return f"\033[31m{text}\033[0m"   # 红
    if pct >= YELLOW_AT:
        return f"\033[33m{text}\033[0m"   # 黄
    return text


def statusline_segment(
    transcript_path: str | None,
    window: int | None = None,
    model_id: str | None = None,
    session_id: str | None = None,
) -> str:
    tokens, transcript_model, max_tokens = _scan_transcript(transcript_path)
    if tokens is None:
        return ""  # 无数据 → 不展示这段（降级，不报错）
    mid = model_id or transcript_model
    # statusline 是权威源（持 `.model.id` 含 `[1m]`）：解析时**绕过缓存**（session_id=None），
    # 以本帧 model 为准，避免会话中途换 model 时被陈旧缓存挟持（粘滞误报）；再用新值刷新缓存。
    win = resolve_window(window, mid, None, max_tokens)
    if session_id:
        write_window_cache(session_id, win)  # 刷新缓存供无 model 的 hook 读
    if win <= 0:
        return ""
    pct = min(999, round(100 * tokens / win))
    return _colorize(f"🧠 {pct}%", pct)


def _cli() -> int:
    ap = argparse.ArgumentParser(add_help=True)
    ap.add_argument("transcript", nargs="?", default=None)
    ap.add_argument("--tokens", action="store_true")
    ap.add_argument("--percent", action="store_true")
    ap.add_argument("--statusline", action="store_true")
    ap.add_argument("--window", type=int, default=None)
    ap.add_argument("--model", type=str, default=None)
    ap.add_argument("--session", type=str, default=None)
    args = ap.parse_args()
    try:
        if args.tokens:
            t = context_tokens(args.transcript)
            print("" if t is None else t)
        elif args.statusline:
            print(statusline_segment(args.transcript, args.window, args.model, args.session))
        else:  # 默认 --percent
            p = percent(args.transcript, args.window, args.model, args.session)
            print("" if p is None else p)
    except Exception:  # 兜底：绝不让调用方因本模块崩溃
        print("")
    return 0


if __name__ == "__main__":
    sys.exit(_cli())
