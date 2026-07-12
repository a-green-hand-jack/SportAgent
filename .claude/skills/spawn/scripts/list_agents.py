#!/usr/bin/env python3
"""spawn skill 的「发现」步：列出本 repo 所有 canonical subagent 及其一句话用途。

读 `.claude/agents/*.md` 的 frontmatter（name/description/tools/model），
输出一张表——解决「不知道有哪些 agent 能派」。只读、无第三方依赖、失败不 raise。

用法：
    python3 .claude/skills/spawn/scripts/list_agents.py            # markdown 表
    python3 .claude/skills/spawn/scripts/list_agents.py --json     # JSON
"""
import json
import sys
from pathlib import Path

# .claude/skills/spawn/scripts/list_agents.py → repo 根上溯 4 层
REPO_ROOT = Path(__file__).resolve().parents[4]
AGENTS_DIR = REPO_ROOT / ".claude" / "agents"

FIELDS = ("name", "description", "tools", "model")


def _parse_frontmatter(text: str) -> dict:
    """极简 YAML frontmatter 解析：取 `---` 块内的**单行** `key: value`（够用即可，不引 yaml）。

    假设：agent frontmatter 用扁平单行值（本 repo 16 个 agent 均如此）。折叠标量（`key: >`）
    或块列表（`tools:` 后跟 `- Read`）不会被展开——那种 agent 该表会显示截断值（非致命）。
    """
    lines = text.splitlines()
    if not lines or lines[0].strip() != "---":
        return {}
    fm: dict[str, str] = {}
    for ln in lines[1:]:
        if ln.strip() == "---":
            break
        if ":" not in ln:
            continue
        key, _, val = ln.partition(":")
        key = key.strip()
        if key in FIELDS:
            fm[key] = val.strip()
    return fm


def collect() -> list[dict]:
    if not AGENTS_DIR.is_dir():
        return []
    rows = []
    for f in sorted(AGENTS_DIR.glob("*.md")):
        try:
            fm = _parse_frontmatter(f.read_text(encoding="utf-8", errors="ignore"))
        except OSError:
            continue
        if not fm.get("name"):
            fm["name"] = f.stem
        rows.append({k: fm.get(k, "") for k in FIELDS})
    return rows


def _cell(s: str) -> str:
    return (s or "").replace("|", "\\|").replace("\n", " ").strip() or "-"


def main() -> int:
    rows = collect()
    if "--json" in sys.argv[1:]:
        print(json.dumps(rows, ensure_ascii=False, indent=2))
        return 0
    if not rows:
        print(f"(未找到 subagent：{AGENTS_DIR} 为空或不存在)")
        return 0
    print("| name | 一句话用途 | tools | model |")
    print("| --- | --- | --- | --- |")
    for r in rows:
        print(f"| {_cell(r['name'])} | {_cell(r['description'])} | {_cell(r['tools'])} | {_cell(r['model'])} |")
    print(f"\n共 {len(rows)} 个 subagent。命名/派发见 `.agent/agent-identity.md` 与 `spawn` skill。")
    return 0


if __name__ == "__main__":
    sys.exit(main())
