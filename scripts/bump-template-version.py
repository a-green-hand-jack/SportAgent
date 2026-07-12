#!/usr/bin/env python3
"""模板版本 bump：判级由 agent 决定，本脚本负责机械落地。

流程（见 .agent/template-versioning-policy.md）：
  1. 读 VERSION（形如 v1.2.3），按 --level 递增。
  2. 写回 VERSION，在 CHANGELOG.md 顶部插入一节（含 --note 与 --closes）。
  3. 打本地 annotated git tag vX.Y.Z（除非 --no-tag）。push tag / release 走 human gate。

无第三方依赖。退出码 0 = 成功，非 0 = 失败。
用法：
  python scripts/bump-template-version.py --level minor --note "新增 template-feedback skill" --closes 12,15
  python scripts/bump-template-version.py --level patch --note "修 hook 路径 bug" --no-tag
"""
from __future__ import annotations

import argparse
import re
import subprocess
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
VERSION_FILE = REPO / "VERSION"
CHANGELOG = REPO / "CHANGELOG.md"
SEMVER_RE = re.compile(r"^v?(\d+)\.(\d+)\.(\d+)$")


def read_version() -> tuple[int, int, int]:
    if not VERSION_FILE.exists():
        raise SystemExit("ERROR 缺少 VERSION 文件")
    raw = VERSION_FILE.read_text(encoding="utf-8").strip()
    m = SEMVER_RE.match(raw)
    if not m:
        raise SystemExit(f"ERROR VERSION 不是合法 semver：{raw!r}")
    return int(m.group(1)), int(m.group(2)), int(m.group(3))


def bump(v: tuple[int, int, int], level: str) -> tuple[int, int, int]:
    major, minor, patch = v
    if level == "major":
        return major + 1, 0, 0
    if level == "minor":
        return major, minor + 1, 0
    if level == "patch":
        return major, minor, patch + 1
    raise SystemExit(f"ERROR 未知 level：{level}")


def fmt(v: tuple[int, int, int]) -> str:
    return f"v{v[0]}.{v[1]}.{v[2]}"


def update_changelog(new: str, level: str, note: str, closes: list[str], date: str) -> None:
    header = "# CHANGELOG\n\n> 模板框架层的版本历史。判级规则见 `.agent/template-versioning-policy.md`。\n"
    closes_str = ""
    if closes:
        closes_str = "  Closes " + ", ".join(f"#{c}" for c in closes) + "\n"
    date_str = f" — {date}" if date else ""
    section = (
        f"## {new} ({level.upper()}){date_str}\n\n"
        f"- {note or '(未填 note)'}\n"
        f"{closes_str}\n"
    )
    if CHANGELOG.exists():
        text = CHANGELOG.read_text(encoding="utf-8")
        # 在第一个 "## " 之前插入新节；没有则接在 header 后。
        idx = text.find("\n## ")
        if idx == -1:
            CHANGELOG.write_text(text.rstrip() + "\n\n" + section, encoding="utf-8")
        else:
            CHANGELOG.write_text(text[: idx + 1] + section + text[idx + 1 :], encoding="utf-8")
    else:
        CHANGELOG.write_text(header + "\n" + section, encoding="utf-8")


def git_tag(tag: str, note: str) -> None:
    if not (REPO / ".git").exists():
        print("WARN 尚未 git init：跳过打 tag")
        return
    existing = subprocess.run(
        ["git", "tag", "--list", tag], cwd=REPO, capture_output=True, text=True
    ).stdout.split()
    if tag in existing:
        raise SystemExit(f"ERROR tag 已存在：{tag}（版本冲突，请核对 VERSION）")
    subprocess.run(
        ["git", "tag", "-a", tag, "-m", note or f"template {tag}"], cwd=REPO, check=True
    )
    print(f"[bump] 已打本地 tag {tag}（push tag / release 走 human gate）")


def main() -> int:
    p = argparse.ArgumentParser()
    p.add_argument("--level", required=True, choices=["major", "minor", "patch"])
    p.add_argument("--note", default="", help="本次发布摘要，写进 CHANGELOG")
    p.add_argument("--closes", default="", help="逗号分隔的 issue 号，如 12,15")
    p.add_argument("--date", default="", help="发布日期 YYYY-MM-DD（可选，脚本不取系统时钟）")
    p.add_argument("--no-tag", action="store_true", help="只写 VERSION/CHANGELOG，不打 tag")
    args = p.parse_args()

    old = read_version()
    new = bump(old, args.level)
    new_str, old_str = fmt(new), fmt(old)
    closes = [c.strip() for c in args.closes.split(",") if c.strip()]

    VERSION_FILE.write_text(new_str + "\n", encoding="utf-8")
    update_changelog(new_str, args.level, args.note, closes, args.date)
    print(f"[bump] VERSION {old_str} -> {new_str}（{args.level.upper()}）")
    if not args.no_tag:
        git_tag(new_str, args.note)
    return 0


if __name__ == "__main__":
    sys.exit(main())
