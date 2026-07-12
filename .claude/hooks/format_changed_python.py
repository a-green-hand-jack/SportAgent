#!/usr/bin/env python3
"""PostToolUse advisory formatter for changed Python files.

Claude Code can pass changed files through `CLAUDE_FILE_PATHS`; Codex hook input
for `apply_patch` carries the patch text instead. This hook supports both shapes
and runs `ruff format` only when it can identify in-repo `.py` files. Missing
ruff or formatting failures never block the agentic loop.
"""
from __future__ import annotations

import json
import os
import shutil
import subprocess
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent.parent


def _patch_paths(patch_text: str) -> list[str]:
    paths: list[str] = []
    for line in patch_text.splitlines():
        for prefix in ("*** Add File: ", "*** Update File: ", "*** Move to: "):
            if line.startswith(prefix):
                paths.append(line[len(prefix) :].strip())
                break
    return paths


def _candidate_paths(event: dict) -> list[str]:
    paths: list[str] = []
    env_paths = os.environ.get("CLAUDE_FILE_PATHS", "")
    if env_paths:
        paths.extend(p for p in env_paths.split() if p)

    tool_input = event.get("tool_input", {}) or {}
    for key in ("file_path", "notebook_path"):
        value = tool_input.get(key)
        if value:
            paths.append(str(value))

    if event.get("tool_name") == "apply_patch":
        paths.extend(_patch_paths(tool_input.get("command", "") or ""))

    return paths


def _repo_python_files(paths: list[str]) -> list[str]:
    result: list[str] = []
    seen: set[Path] = set()
    for raw in paths:
        path = Path(raw)
        if not path.is_absolute():
            path = REPO_ROOT / path
        try:
            resolved = path.resolve()
            resolved.relative_to(REPO_ROOT)
        except (OSError, ValueError):
            continue
        if resolved.suffix != ".py" or not resolved.exists() or resolved in seen:
            continue
        seen.add(resolved)
        result.append(str(resolved))
    return result


def main() -> None:
    if shutil.which("ruff") is None:
        sys.exit(0)

    raw = sys.stdin.read()
    event: dict = {}
    if raw.strip():
        try:
            event = json.loads(raw)
        except json.JSONDecodeError:
            event = {}

    paths = _repo_python_files(_candidate_paths(event))
    if not paths:
        sys.exit(0)

    try:
        proc = subprocess.run(
            ["ruff", "format", *paths],
            cwd=str(REPO_ROOT),
            text=True,
            capture_output=True,
            timeout=30,
        )
    except Exception as exc:  # noqa: BLE001 advisory hook
        print(f"[format_changed_python] ruff format skipped: {exc}", file=sys.stderr)
        sys.exit(0)

    if proc.returncode != 0:
        detail = (proc.stderr or proc.stdout).strip()
        print(f"[format_changed_python] ruff format failed: {detail}", file=sys.stderr)

    sys.exit(0)


if __name__ == "__main__":
    main()
