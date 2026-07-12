#!/usr/bin/env python3
"""same-commit rule 检查：结构改动必须与对应 ANATOMY.md 在同一变更集。

见 `.agent/anatomy-protocol.md`。把「结构改了、地图没跟上」这个**动作**挡在
commit / PR 粒度，而不是等 citation rot 后由 check-anatomy-drift 事后发现。

判定（保守、低误报）：
- 结构改动 = 在「拥有自己 ANATOMY.md 的目录」里 **新增 / 删除 / 重命名** 文件
  （git 状态 A / D / R / C）。这类改动必须在同一变更集里更新该目录的 ANATOMY.md。
- 纯内容修改（M）**不触发** —— doctrine 明确：改函数内部实现不需要动 anatomy。
- 目录若没有自己的 ANATOMY.md（简单 leaf / 静态资源），不要求 —— 与
  「只有复杂目录才有 anatomy」一致，避免为普通文件强逼地图。

模式（互斥）：
  --staged            检查已 staged 改动（pre-commit hook 用；缺省即此）
  --against <ref>     检查 <ref>..HEAD（CI 对 PR base / push before 用）
  --commit <sha>      检查某个 commit（<sha>^..<sha>）

退出码 0 = 通过 / 无结构改动 / 非 git 仓库；1 = 违规。
逃生：`SAME_COMMIT_SKIP=1` 或 `git commit --no-verify`
（本规则是文档卫生，不是安全地板；红线由 .claude/hooks/pre_tool_guard.py 守）。

无第三方依赖。
"""
from __future__ import annotations

import os
import subprocess
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
ANATOMY = "ANATOMY.md"
STRUCTURAL_STATUS = ("A", "D", "R", "C")  # add / delete / rename / copy


def _git(args: list[str]) -> str | None:
    try:
        out = subprocess.run(
            ["git", *args], cwd=REPO, capture_output=True, text=True, check=True
        )
    except (subprocess.CalledProcessError, FileNotFoundError):
        return None
    return out.stdout


def _diff_args(argv: list[str]) -> list[str] | None:
    """把命令行模式翻译成 `git diff --name-status -M` 的参数。None = 无法确定。"""
    if "--against" in argv:
        ref = argv[argv.index("--against") + 1]
        return ["diff", "--name-status", "-M", ref, "HEAD"]
    if "--commit" in argv:
        sha = argv[argv.index("--commit") + 1]
        return ["diff", "--name-status", "-M", f"{sha}^", sha]
    # 默认 / --staged
    return ["diff", "--cached", "--name-status", "-M"]


def _parse(out: str) -> list[tuple[str, list[str]]]:
    """解析 name-status 行 -> (status_letter, [paths])。重命名/复制含 old+new 两路径。"""
    entries: list[tuple[str, list[str]]] = []
    for line in out.splitlines():
        if not line.strip():
            continue
        parts = line.split("\t")
        status = parts[0].strip()
        paths = [p for p in parts[1:] if p]
        if not paths:
            continue
        entries.append((status[0], paths))
    return entries


def _owning_anatomy(path: str) -> str | None:
    """path 所在目录若有自己的 ANATOMY.md，返回其 repo-relative posix 路径，否则 None。"""
    d = os.path.dirname(path)
    rel = f"{d}/{ANATOMY}" if d else ANATOMY
    return rel if (REPO / rel).exists() else None


def main(argv: list[str]) -> int:
    if os.environ.get("SAME_COMMIT_SKIP") == "1":
        print("[same-commit] SAME_COMMIT_SKIP=1 —— 跳过")
        return 0
    if not (REPO / ".git").exists() and _git(["rev-parse", "--git-dir"]) is None:
        print("[same-commit] 非 git 仓库 —— 跳过")
        return 0

    diff_args = _diff_args(argv)
    if diff_args is None:
        print("[same-commit] 无法确定 diff 范围 —— 跳过")
        return 0
    out = _git(diff_args)
    if out is None:
        print("[same-commit] git diff 不可用 —— 跳过")
        return 0

    entries = _parse(out)
    required: dict[str, str] = {}   # anatomy_path -> 触发它的样例文件
    touched_anatomy: set[str] = set()

    for status, paths in entries:
        for p in paths:
            if os.path.basename(p) == ANATOMY:
                touched_anatomy.add(p)
        if status not in STRUCTURAL_STATUS:
            continue
        for p in paths:
            if os.path.basename(p) == ANATOMY:
                continue  # 动 anatomy 本身不算「需另一张地图跟进」的结构码改动
            anat = _owning_anatomy(p)
            if anat and anat not in required:
                required[anat] = p

    violations = {a: eg for a, eg in required.items() if a not in touched_anatomy}
    if not violations:
        n = sum(1 for s, _ in entries if s in STRUCTURAL_STATUS)
        print(f"[same-commit] OK —— {n} 处结构改动，对应 anatomy 已同变更集更新")
        return 0

    print("[same-commit] FAIL —— 结构改动未同步更新对应 ANATOMY.md：")
    for anat, example in sorted(violations.items()):
        print(f"  · 改了 {example}（等结构文件），但同变更集未更新 {anat}")
    print(
        "\n修复：在同一 commit 里更新上述 ANATOMY.md（组件表/调用关系/状态/citation）。\n"
        "见 .agent/anatomy-protocol.md 的 same-commit rule。\n"
        "确属误报或本次无关结构语义：SAME_COMMIT_SKIP=1 或 git commit --no-verify。"
    )
    return 1


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
