#!/usr/bin/env python3
"""检查 ANATOMY.md 的引用漂移（防止 citation rot）。

对每个名为 `ANATOMY.md` 的文件：
1. frontmatter `related_files:` 列出的路径必须存在（相对该 ANATOMY 所在目录解析）。
2. 正文里的 line-addressed citation `path/to/file.py:42` 或 `:42-90`：
   - 被引文件必须存在（相对 repo 根 或 相对该目录解析）。
   - 行号必须在文件行数范围内。
3. 行数不超过硬上限（见 .agent/anatomy-protocol.md：目标 ~80，硬上限 120）。
   写不短通常是代码边界不清，不是文档该加长——把口头阈值升级成运行时防线。

只校验「看起来像真实 repo 文件」的引用；占位符（含 `<...>`、`example`、模板示例）跳过。
这是结构性检查：只能挡 missing file / out-of-range line；语义正确性仍需人打开代码验证。

无第三方依赖。退出码 0 = 通过，1 = 有漂移。
用法：python scripts/check-anatomy-drift.py
"""
from __future__ import annotations

import re
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
SKIP_DIRS = {".git", ".venv", "__pycache__", ".reference-docs", "node_modules"}
ANATOMY_LINE_LIMIT = 120  # 硬上限，见 .agent/anatomy-protocol.md

# 形如 `path/seg.ext:12` 或 `path/seg.ext:12-90`，允许被反引号包裹。
CITATION_RE = re.compile(
    r"`?([A-Za-z0-9_./-]+\.[A-Za-z0-9_]+):(\d+)(?:-(\d+))?`?"
)
# 占位/示例信号（用于 related_files 逐条判断）。
PLACEHOLDER_HINTS = ("<", ">", "example", "path/to", "foo.", "bar.")
# 能出现在 citation ref 内部的占位信号（逐个匹配判断，不整行跳过）。
PLACEHOLDER_REF_HINTS = ("example", "path/to", "foo.", "bar.")

errors: list[str] = []


def iter_anatomy_files():
    for p in REPO.rglob("ANATOMY.md"):
        if any(part in SKIP_DIRS for part in p.relative_to(REPO).parts):
            continue
        yield p


def resolve(ref: str, anatomy: Path) -> Path | None:
    """把引用解析成实际路径：优先相对 ANATOMY 目录，其次相对 repo 根。"""
    cand1 = (anatomy.parent / ref).resolve()
    if cand1.exists():
        return cand1
    cand2 = (REPO / ref).resolve()
    if cand2.exists():
        return cand2
    return None


def check_related_files(anatomy: Path, text: str) -> None:
    m = re.search(r"^---\s*\n(.*?)\n---", text, re.DOTALL)
    if not m:
        return
    fm = m.group(1)
    block = re.search(r"related_files:\s*\n((?:\s*-\s*.+\n?)+)", fm)
    if not block:
        return
    for line in block.group(1).splitlines():
        ref = line.strip().lstrip("-").strip().strip('"').strip("'")
        if not ref or any(h in ref for h in PLACEHOLDER_HINTS):
            continue
        if resolve(ref, anatomy) is None:
            errors.append(
                f"{anatomy.relative_to(REPO)}: related_files 引用不存在 -> {ref}"
            )


def _is_placeholder_citation(line: str, m: re.Match) -> bool:
    """逐个匹配判断是否占位/示例（不再整行跳过，避免漏检同行的真实 citation）。"""
    ref = m.group(1)
    if any(h in ref for h in PLACEHOLDER_REF_HINTS):
        return True
    # 被尖括号包裹的示例，如 `<示例：a.py:42>`：ref 本身不含 <>，看上下文。
    if "<" in line[: m.start()] and ">" in line[m.end() :]:
        return True
    return False


def check_citations(anatomy: Path, text: str) -> None:
    # 去掉 frontmatter 再扫正文。
    body = re.sub(r"^---\s*\n.*?\n---\s*\n", "", text, count=1, flags=re.DOTALL)
    for line in body.splitlines():
        for m in CITATION_RE.finditer(line):
            if _is_placeholder_citation(line, m):
                continue
            ref, start, end = m.group(1), int(m.group(2)), m.group(3)
            # 只关心带路径分隔符或已知代码后缀的引用，避免误判 "3.10" 之类。
            if "/" not in ref and not ref.endswith(
                (".py", ".md", ".yaml", ".yml", ".json", ".toml", ".js", ".ts", ".sh")
            ):
                continue
            target = resolve(ref, anatomy)
            if target is None:
                errors.append(
                    f"{anatomy.relative_to(REPO)}: 引用文件不存在 -> {ref}:{start}"
                )
                continue
            try:
                n_lines = sum(1 for _ in target.open("r", encoding="utf-8", errors="replace"))
            except OSError:
                continue
            hi = int(end) if end else start
            if start < 1 or hi > n_lines:
                errors.append(
                    f"{anatomy.relative_to(REPO)}: 行号越界 -> {ref}:{start}"
                    f"{'-' + end if end else ''}（文件共 {n_lines} 行）"
                )


def check_line_budget(anatomy: Path, text: str) -> None:
    n = text.count("\n") + (0 if text.endswith("\n") or not text else 1)
    if n > ANATOMY_LINE_LIMIT:
        errors.append(
            f"{anatomy.relative_to(REPO)}: 超过硬上限 {ANATOMY_LINE_LIMIT} 行"
            f"（当前 {n} 行）——拆分边界，别加长文档"
        )


def main() -> int:
    files = list(iter_anatomy_files())
    for anatomy in files:
        text = anatomy.read_text(encoding="utf-8", errors="replace")
        check_related_files(anatomy, text)
        check_citations(anatomy, text)
        check_line_budget(anatomy, text)

    for e in errors:
        print(f"ERROR {e}")
    status = "FAIL" if errors else "OK"
    print(f"[check-anatomy-drift] {status} — 扫描 {len(files)} 个 ANATOMY.md，{len(errors)} 处漂移")
    return 1 if errors else 0


if __name__ == "__main__":
    sys.exit(main())
