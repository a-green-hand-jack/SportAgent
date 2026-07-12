#!/usr/bin/env python3
"""检查 agent harness 结构是否自洽（防漂移 / 防膨胀门禁）。

检查项：
1. 必需的顶层入口文件与目录存在。
2. 根污染：根目录只出现白名单条目（未知条目告警）。
3. 导航四件套：重要目录有 README/AGENTS/CLAUDE/ANATOMY。
4. 能力索引：.claude/agents/*.md 与 .claude/skills/*/SKILL.md 有 frontmatter（name/description）。
5. Claude/Codex 配置可解析、受保护路径有权限地板，且 hooks 引用的脚本存在。
6. Codex adapters 与 canonical .claude 能力同步。

无第三方依赖。退出码 0 = 通过（可含 warning），1 = 有 error。
用法：python scripts/check-agent-harness.py [--strict]
--strict 把 warning 也当作失败。
"""
from __future__ import annotations

import json
import re
import subprocess
import sys
import tomllib
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent

# 必需的顶层条目。
REQUIRED_TOP = [
    "README.md", "PROJECT.md", "AGENTS.md", "CLAUDE.md", "ANATOMY.md",
    ".agent", ".claude", ".codex", ".agents", "lab", "memory", "scripts",
]

# 根目录白名单（其余视为潜在污染 -> warning）。
ROOT_WHITELIST = {
    "README.md", "PROJECT.md", "DECISIONS.md", "DESIGN.md", "AGENTS.md", "CLAUDE.md",
    "ANATOMY.md", ".gitignore", ".github", ".githooks", ".agent", ".claude", ".codex",
    ".agents", "human", "lab", "memory", "deliverables", "scripts", "plans", ".reference-docs",
    # 模板版本 / 上下游同步锚点（见 .agent/template-versioning-policy.md）
    "VERSION", "CHANGELOG.md", "template-manifest.toml", ".template.toml",
    # 常见工程文件（允许存在，不算污染）
    "LICENSE", "pyproject.toml", "uv.lock", ".python-version",
    ".pre-commit-config.yaml", "Makefile",
}
# 工具 / VCS 产物：忽略，不告警。
ROOT_IGNORE = {
    ".git", ".venv", "__pycache__", ".DS_Store", ".ruff_cache",
    ".mypy_cache", ".pytest_cache", ".idea", ".vscode", ".env", ".omx",
}

# 需要完整四件套的目录。
QUARTET_DIRS = [
    "human", ".claude", ".codex", ".agents", "lab", "lab/code", "lab/code/src",
    "lab/infra", "lab/research", "lab/artifacts", "memory",
    "deliverables", "scripts",
]
QUARTET_FILES = ["README.md", "AGENTS.md", "CLAUDE.md", "ANATOMY.md"]

# settings.json deny 必须覆盖的受保护路径 token（见 .agent/action-boundary.md）。
PROTECTED_DENY_TOKENS = [
    "lab/data", "lab/runs", "lab/models", "lab/infra/private",
    "checkpoints", "wandb", ".env",
]

FRONTMATTER_RE = re.compile(r"^---\s*\n(.*?)\n---\s*\n", re.DOTALL)

errors: list[str] = []
warnings: list[str] = []


def err(msg: str) -> None:
    errors.append(msg)


def warn(msg: str) -> None:
    warnings.append(msg)


def check_required_top() -> None:
    for name in REQUIRED_TOP:
        if not (REPO / name).exists():
            err(f"缺少必需顶层条目：{name}")


def check_root_pollution() -> None:
    for entry in sorted(REPO.iterdir()):
        name = entry.name
        if name in ROOT_IGNORE or name in ROOT_WHITELIST:
            continue
        warn(f"根目录疑似污染（不在白名单）：{name} —— 长文/报告/实验记录不应堆在 root")


def check_quartets() -> None:
    for d in QUARTET_DIRS:
        base = REPO / d
        if not base.is_dir():
            err(f"四件套目录不存在：{d}/")
            continue
        for f in QUARTET_FILES:
            if not (base / f).exists():
                err(f"缺少导航文件：{d}/{f}")
    # .agent 用 AGENTS.md 作 doctrine 索引（不要求 ANATOMY）。
    if not (REPO / ".agent" / "AGENTS.md").exists():
        err("缺少 .agent/AGENTS.md（doctrine 索引）")


def _frontmatter(path: Path) -> dict[str, str] | None:
    m = FRONTMATTER_RE.search(path.read_text(encoding="utf-8", errors="replace"))
    if not m:
        return None
    fields: dict[str, str] = {}
    for line in m.group(1).splitlines():
        if ":" in line and not line.startswith((" ", "\t", "-")):
            k, _, v = line.partition(":")
            fields[k.strip()] = v.strip()
    return fields


def check_capabilities() -> None:
    agents_dir = REPO / ".claude" / "agents"
    if agents_dir.is_dir():
        agent_files = list(agents_dir.glob("*.md"))
        if not agent_files:
            warn(".claude/agents/ 为空：没有 repo-local subagent")
        for f in agent_files:
            fm = _frontmatter(f)
            if fm is None:
                err(f"subagent 缺少 frontmatter：{f.relative_to(REPO)}")
            elif "name" not in fm or "description" not in fm:
                err(f"subagent frontmatter 缺 name/description：{f.relative_to(REPO)}")
    skills_dir = REPO / ".claude" / "skills"
    if skills_dir.is_dir():
        for skill in sorted(p for p in skills_dir.iterdir() if p.is_dir()):
            sk = skill / "SKILL.md"
            if not sk.exists():
                err(f"skill 缺少 SKILL.md：{skill.relative_to(REPO)}/")
                continue
            fm = _frontmatter(sk)
            if fm is None or "name" not in fm or "description" not in fm:
                err(f"SKILL.md frontmatter 缺 name/description：{sk.relative_to(REPO)}")


def check_settings() -> None:
    settings = REPO / ".claude" / "settings.json"
    if not settings.exists():
        err("缺少 .claude/settings.json")
        return
    try:
        data = json.loads(settings.read_text(encoding="utf-8"))
    except json.JSONDecodeError as e:
        err(f".claude/settings.json 解析失败：{e}")
        return
    if "permissions" not in data:
        warn(".claude/settings.json 无 permissions 段")
    # 断言 deny 真的覆盖受保护路径（防有人删掉某条 deny 而无人察觉）。
    # hook 地板也拦这些，但 permission deny 是第一层——两层都要在。
    deny_text = " ".join(str(r) for r in (data.get("permissions") or {}).get("deny", []))
    for token in PROTECTED_DENY_TOKENS:
        if token not in deny_text:
            warn(
                f".claude/settings.json deny 未覆盖受保护路径：{token}"
                "（应有 Edit/Write deny；参见 .agent/action-boundary.md）"
            )
    for event, groups in (data.get("hooks") or {}).items():
        for group in groups:
            for hook in group.get("hooks", []):
                cmd = hook.get("command", "")
                m = re.search(r"\.claude/hooks/[\w./-]+\.py", cmd)
                if m and not (REPO / m.group(0)).exists():
                    err(f"hook 脚本不存在：{m.group(0)}（{event}）")


def check_codex_config() -> None:
    config = REPO / ".codex" / "config.toml"
    if not config.exists():
        err("缺少 .codex/config.toml")
        return
    try:
        data = tomllib.loads(config.read_text(encoding="utf-8"))
    except tomllib.TOMLDecodeError as e:
        err(f".codex/config.toml 解析失败：{e}")
        return

    hooks = data.get("hooks") or {}
    pre_tool = hooks.get("PreToolUse") or []
    pre_tool_text = json.dumps(pre_tool, ensure_ascii=False)
    if "pre_tool_guard.py" not in pre_tool_text:
        warn(".codex/config.toml PreToolUse 未接入 pre_tool_guard.py")

    for event, groups in hooks.items():
        if not isinstance(groups, list):
            continue
        for group in groups:
            for hook in group.get("hooks", []):
                cmd = hook.get("command", "")
                m = re.search(r"\.claude/hooks/[\w./-]+\.py", cmd)
                if m and not (REPO / m.group(0)).exists():
                    err(f"Codex hook 脚本不存在：{m.group(0)}（{event}）")

    rules = REPO / ".codex" / "rules" / "default.rules"
    if not rules.exists():
        warn("缺少 .codex/rules/default.rules（Codex execpolicy prompt/deny 层）")
    elif "pip" not in rules.read_text(encoding="utf-8", errors="replace"):
        warn(".codex/rules/default.rules 未见 pip install 禁止规则")


def check_codex_adapters() -> None:
    sync_script = REPO / "scripts" / "sync-codex-adapters.py"
    if not sync_script.exists():
        err("缺少 scripts/sync-codex-adapters.py")
        return
    proc = subprocess.run(
        [sys.executable, str(sync_script), "--check"],
        cwd=str(REPO),
        text=True,
        capture_output=True,
        timeout=30,
    )
    if proc.returncode != 0:
        detail = (proc.stdout + proc.stderr).strip()
        err(f"Codex adapters 与 .claude canonical 源不同步：{detail}")

    for path in sorted((REPO / ".codex" / "agents").glob("*.toml")):
        try:
            data = tomllib.loads(path.read_text(encoding="utf-8"))
        except tomllib.TOMLDecodeError as e:
            err(f"Codex agent TOML 解析失败：{path.relative_to(REPO)}：{e}")
            continue
        for key in ("name", "description", "developer_instructions"):
            if key not in data:
                err(f"Codex agent 缺 {key}：{path.relative_to(REPO)}")

    skills_dir = REPO / ".agents" / "skills"
    if not skills_dir.is_dir():
        err("缺少 .agents/skills/")
        return
    for skill in sorted(p for p in skills_dir.iterdir() if p.is_dir()):
        sk = skill / "SKILL.md"
        if not sk.exists():
            err(f"Codex skill 缺少 SKILL.md：{skill.relative_to(REPO)}/")
            continue
        fm = _frontmatter(sk)
        if fm is None or "name" not in fm or "description" not in fm:
            err(f"Codex SKILL.md frontmatter 缺 name/description：{sk.relative_to(REPO)}")


def check_design_inventory() -> None:
    """若存在 DESIGN.md，校验其 §10 能力清单表里的数量与实际一致（防手记漂移）。
    对应 doctrine：`.agent/repo-documentation-topology.md`。DESIGN.md 可选：不存在则跳过；
    表格式变动导致匹配不到时也跳过（不误报）。"""
    design = REPO / "DESIGN.md"
    if not design.exists():
        return
    text = design.read_text(encoding="utf-8", errors="replace")
    skills_dir = REPO / ".claude" / "skills"
    actual = {
        "agents": len(list((REPO / ".claude" / "agents").glob("*.md"))),
        "skills": len([d for d in skills_dir.iterdir() if (d / "SKILL.md").exists()])
        if skills_dir.is_dir() else 0,
        "commands": len(list((REPO / ".claude" / "commands").glob("*.md"))),
        "hooks": len(list((REPO / ".claude" / "hooks").glob("*.py"))),
    }
    for key in ("agents", "skills", "commands", "hooks"):
        m = re.search(rf"\.claude/{key}/`?\s*\|\s*(\d+)", text)
        if not m:
            continue  # 表格式变了：跳过，不误报
        stated = int(m.group(1))
        if stated != actual[key]:
            warn(
                f"DESIGN.md 能力清单过时：{key} 写 {stated}，实际 {actual[key]}。"
                "更新 DESIGN.md §10 清单表（repo-doc-steward 职责）。"
            )


def main() -> int:
    strict = "--strict" in sys.argv
    check_required_top()
    check_root_pollution()
    check_quartets()
    check_capabilities()
    check_settings()
    check_codex_config()
    check_codex_adapters()
    check_design_inventory()

    for w in warnings:
        print(f"WARN  {w}")
    for e in errors:
        print(f"ERROR {e}")
    n_e, n_w = len(errors), len(warnings)
    status = "FAIL" if (n_e or (strict and n_w)) else "OK"
    print(f"[check-agent-harness] {status} — {n_e} error(s), {n_w} warning(s)")
    return 1 if status == "FAIL" else 0


if __name__ == "__main__":
    sys.exit(main())
