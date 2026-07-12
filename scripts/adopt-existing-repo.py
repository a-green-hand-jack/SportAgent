#!/usr/bin/env python3
"""Adopt an existing Git repo into this template shape.

The script is intentionally conservative:
- no deletes;
- no overwrites without first preserving the original file;
- no protected data/model/checkpoint byte moves;
- state is written into lab/docs/audits/template-adoption/state.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
import re
import shutil
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

TEMPLATE_ROOT = Path(__file__).resolve().parent.parent

STATE_DIR = Path("lab/docs/audits/template-adoption/state")
REPORT_PATH = Path("lab/docs/audits/template-adoption-report.md")
PLAN_FILE = "adoption-plan.json"
BASELINE_FILE = "baseline.json"
LOG_FILE = "phase-log.jsonl"

CONTROL_ITEMS = [
    "AGENTS.md",
    "CLAUDE.md",
    "ANATOMY.md",
    "PROJECT.md",
    "DESIGN.md",
    "DECISIONS.md",
    "README.md",
    ".gitignore",
    ".githooks",
    ".github",
    ".reference-docs",
    ".agent",
    ".claude",
    "human",
    "lab",
    "memory",
    "deliverables",
    "scripts",
    "plans",
]

ROOT_WHITELIST = {
    "README.md",
    "PROJECT.md",
    "DECISIONS.md",
    "DESIGN.md",
    "AGENTS.md",
    "CLAUDE.md",
    "ANATOMY.md",
    ".gitignore",
    ".github",
    ".githooks",
    ".agent",
    ".claude",
    "human",
    "lab",
    "memory",
    "deliverables",
    "scripts",
    "plans",
    ".reference-docs",
    "LICENSE",
    "pyproject.toml",
    "uv.lock",
    ".python-version",
    ".pre-commit-config.yaml",
    "Makefile",
}

PROTECTED_PARTS = {
    ".env",
    "checkpoints",
    "wandb",
}
PROTECTED_PREFIXES = (
    ("lab", "data"),
    ("lab", "runs"),
    ("lab", "models"),
    ("lab", "infra", "private"),
)
LARGE_HASH_LIMIT = 25 * 1024 * 1024

EXCLUDE_DIR_NAMES = {
    ".git",
    ".venv",
    "__pycache__",
    ".pytest_cache",
    ".ruff_cache",
    ".mypy_cache",
}
EXCLUDE_REL_PREFIXES = (
    ".claude/worktrees",
    "lab/docs/audits/template-adoption/state",
)


def now_iso() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat()


def rel_posix(path: Path, root: Path) -> str:
    return path.relative_to(root).as_posix()


def state_root(target: Path) -> Path:
    return target / STATE_DIR


def state_path(target: Path, name: str) -> Path:
    return state_root(target) / name


def read_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def write_json(path: Path, data: dict[str, Any], dry_run: bool = False) -> None:
    if dry_run:
        print(f"DRY-RUN write {path}")
        return
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def append_log(target: Path, phase: str, status: str, details: dict[str, Any], dry_run: bool) -> None:
    row = {"time": now_iso(), "phase": phase, "status": status, "details": details}
    if dry_run:
        print(f"DRY-RUN log {row}")
        return
    path = state_path(target, LOG_FILE)
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("a", encoding="utf-8") as f:
        f.write(json.dumps(row, sort_keys=True) + "\n")


def run(
    cmd: list[str] | str,
    cwd: Path,
    *,
    shell: bool = False,
    timeout: int = 120,
) -> dict[str, Any]:
    try:
        proc = subprocess.run(
            cmd,
            cwd=cwd,
            shell=shell,
            text=True,
            capture_output=True,
            timeout=timeout,
            check=False,
        )
        return {
            "command": cmd if isinstance(cmd, str) else " ".join(cmd),
            "returncode": proc.returncode,
            "stdout": proc.stdout[-8000:],
            "stderr": proc.stderr[-8000:],
            "timeout": False,
        }
    except subprocess.TimeoutExpired as e:
        return {
            "command": cmd if isinstance(cmd, str) else " ".join(cmd),
            "returncode": 124,
            "stdout": (e.stdout or "")[-8000:] if isinstance(e.stdout, str) else "",
            "stderr": (e.stderr or "")[-8000:] if isinstance(e.stderr, str) else "",
            "timeout": True,
        }


def require_git_repo(target: Path) -> None:
    if not target.exists() or not target.is_dir():
        raise SystemExit(f"target is not a directory: {target}")
    if not (target / ".git").exists():
        raise SystemExit(f"target is not a Git repo: {target}")
    if target.resolve() == TEMPLATE_ROOT.resolve():
        raise SystemExit("refusing to adopt the template repo into itself")


def sha256_file(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def protected_path(rel: str) -> bool:
    parts = tuple(Path(rel).parts)
    if any(part in PROTECTED_PARTS for part in parts):
        return True
    return any(parts[: len(prefix)] == prefix for prefix in PROTECTED_PREFIXES)


def template_excluded(rel: str, path: Path) -> bool:
    if any(rel == prefix or rel.startswith(prefix + "/") for prefix in EXCLUDE_REL_PREFIXES):
        return True
    return path.name in EXCLUDE_DIR_NAMES


def list_root_entries(target: Path) -> list[dict[str, Any]]:
    entries: list[dict[str, Any]] = []
    for entry in sorted(target.iterdir(), key=lambda p: p.name):
        if entry.name == ".git":
            continue
        rel = entry.name
        kind = "dir" if entry.is_dir() else "file" if entry.is_file() else "other"
        entries.append(
            {
                "path": rel,
                "kind": kind,
                "allowed_root": rel in ROOT_WHITELIST,
                "template_control_item": rel in CONTROL_ITEMS,
                "protected": protected_path(rel),
            }
        )
    return entries


def project_slug(target: Path, explicit: str | None) -> str:
    base = explicit or target.name
    slug = re.sub(r"[^A-Za-z0-9._-]+", "-", base.strip()).strip("-._")
    return slug or "imported-project"


def detect_test_command(target: Path, requested: str | None) -> str | None:
    if requested == "none":
        return None
    if requested and requested != "auto":
        return requested
    if (target / "pytest.ini").exists() or (target / "tests").is_dir():
        return "python -m pytest"
    if (target / "Makefile").exists():
        text = (target / "Makefile").read_text(encoding="utf-8", errors="replace")
        if re.search(r"^test:", text, re.MULTILINE):
            return "make test"
    return None


def git_ls_files(target: Path) -> list[str]:
    proc = subprocess.run(
        ["git", "ls-files", "-z"],
        cwd=target,
        text=False,
        capture_output=True,
        check=False,
    )
    if proc.returncode != 0:
        raise SystemExit(proc.stderr.decode("utf-8", errors="replace"))
    return [p.decode("utf-8", errors="replace") for p in proc.stdout.split(b"\0") if p]


def discover(args: argparse.Namespace) -> dict[str, Any]:
    target = args.target.resolve()
    require_git_repo(target)
    slug = project_slug(target, args.project_name)
    root_entries = list_root_entries(target)
    protected_roots = [e["path"] for e in root_entries if e["protected"]]
    root_pollution = [
        e["path"]
        for e in root_entries
        if not e["allowed_root"] and not e["protected"] and not e["template_control_item"]
    ]
    conflicts = [
        e["path"]
        for e in root_entries
        if e["template_control_item"] and (TEMPLATE_ROOT / e["path"]).exists()
    ]
    plan = {
        "schema": "template-adoption-plan-v1",
        "created_at": now_iso(),
        "target": str(target),
        "template_root": str(TEMPLATE_ROOT),
        "policy": args.policy,
        "project_slug": slug,
        "state_dir": STATE_DIR.as_posix(),
        "report_path": REPORT_PATH.as_posix(),
        "test_command": detect_test_command(target, args.test_command),
        "root_entries": root_entries,
        "protected_roots": protected_roots,
        "root_pollution": root_pollution,
        "template_conflicts": conflicts,
        "import_root": f"lab/code/imported/{slug}",
        "normalize_blockers": [
            f"protected root path requires manual policy or future protected-move support: {p}"
            for p in protected_roots
        ],
    }
    write_json(state_path(target, PLAN_FILE), plan, args.dry_run)
    append_log(target, "discover", "ok", {"root_entries": len(root_entries)}, args.dry_run)
    print(f"[discover] root_entries={len(root_entries)} conflicts={len(conflicts)}")
    return plan


def baseline(args: argparse.Namespace) -> dict[str, Any]:
    target = args.target.resolve()
    require_git_repo(target)
    plan_path = state_path(target, PLAN_FILE)
    plan = read_json(plan_path) if plan_path.exists() else discover(args)
    tracked: list[dict[str, Any]] = []
    for rel in git_ls_files(target):
        path = target / rel
        if not path.is_file():
            continue
        size = path.stat().st_size
        row: dict[str, Any] = {"path": rel, "size": size, "protected": protected_path(rel)}
        if size <= LARGE_HASH_LIMIT:
            row["sha256"] = sha256_file(path)
        else:
            row["sha256"] = None
            row["hash_skipped_reason"] = f"size>{LARGE_HASH_LIMIT}"
        tracked.append(row)
    test_result = None
    if plan.get("test_command"):
        test_result = run(plan["test_command"], target, shell=True, timeout=args.test_timeout)
    data = {
        "schema": "template-adoption-baseline-v1",
        "created_at": now_iso(),
        "target": str(target),
        "git_status": run(["git", "status", "--short"], target),
        "git_head": run(["git", "rev-parse", "--verify", "HEAD"], target),
        "root_entries": list_root_entries(target),
        "tracked_files": tracked,
        "test_command": plan.get("test_command"),
        "test_result": test_result,
    }
    write_json(state_path(target, BASELINE_FILE), data, args.dry_run)
    append_log(target, "baseline", "ok", {"tracked_files": len(tracked)}, args.dry_run)
    print(f"[baseline] tracked_files={len(tracked)}")
    return data


def unique_preserve_path(target: Path, rel: str) -> Path:
    base = target / "human" / "imported" / "adoption-conflicts" / rel
    if not base.exists():
        return base
    stem = base.name
    parent = base.parent
    for i in range(1, 1000):
        candidate = parent / f"{stem}.conflict-{i}"
        if not candidate.exists():
            return candidate
    raise RuntimeError(f"could not allocate conflict path for {rel}")


def preserve_existing(target: Path, rel: str, dry_run: bool) -> Path:
    src = target / rel
    dst = unique_preserve_path(target, rel)
    if dry_run:
        print(f"DRY-RUN preserve {src} -> {dst}")
        return dst
    dst.parent.mkdir(parents=True, exist_ok=True)
    shutil.move(str(src), str(dst))
    return dst


def copy_file_preserving(src: Path, dst: Path, rel: str, target: Path, dry_run: bool) -> str:
    if dst.exists():
        if dst.is_file() and sha256_file(src) == sha256_file(dst):
            return "same"
        preserve_existing(target, rel, dry_run)
    if dry_run:
        print(f"DRY-RUN copy {src} -> {dst}")
        return "copy"
    dst.parent.mkdir(parents=True, exist_ok=True)
    shutil.copy2(src, dst)
    return "copy"


def copy_template_tree(src_root: Path, dst_root: Path, target: Path, dry_run: bool) -> dict[str, int]:
    counts = {"copy": 0, "same": 0, "skip": 0}
    for root, dirnames, filenames in os.walk(src_root):
        root_path = Path(root)
        rel_root = root_path.relative_to(TEMPLATE_ROOT).as_posix()
        dirnames[:] = [
            d for d in dirnames if not template_excluded(f"{rel_root}/{d}".strip("./"), root_path / d)
        ]
        for filename in filenames:
            src = root_path / filename
            rel = src.relative_to(TEMPLATE_ROOT).as_posix()
            if template_excluded(rel, src):
                counts["skip"] += 1
                continue
            dst = target / rel
            status = copy_file_preserving(src, dst, rel, target, dry_run)
            counts[status] += 1
    return counts


def scaffold(args: argparse.Namespace) -> dict[str, Any]:
    target = args.target.resolve()
    require_git_repo(target)
    if not state_path(target, BASELINE_FILE).exists():
        baseline(args)
    counts = {"copy": 0, "same": 0, "skip": 0}
    for item in CONTROL_ITEMS:
        src = TEMPLATE_ROOT / item
        if not src.exists():
            continue
        if src.is_file():
            status = copy_file_preserving(src, target / item, item, target, args.dry_run)
            counts[status] += 1
        elif src.is_dir():
            sub = copy_template_tree(src, target / item, target, args.dry_run)
            counts = {k: counts[k] + sub[k] for k in counts}
    append_log(target, "scaffold", "ok", counts, args.dry_run)
    print(f"[scaffold] copied={counts['copy']} same={counts['same']} skipped={counts['skip']}")
    return counts


def path_hash(path: Path) -> str | None:
    return sha256_file(path) if path.is_file() and path.stat().st_size <= LARGE_HASH_LIMIT else None


def normalize(args: argparse.Namespace) -> dict[str, Any]:
    target = args.target.resolve()
    require_git_repo(target)
    plan = read_json(state_path(target, PLAN_FILE))
    baseline_data = read_json(state_path(target, BASELINE_FILE))
    baseline_root = {e["path"]: e for e in baseline_data["root_entries"]}
    file_hashes = {
        row["path"]: row.get("sha256")
        for row in baseline_data["tracked_files"]
        if row.get("sha256")
    }
    import_root = target / plan["import_root"]
    moved: list[dict[str, str]] = []
    blockers: list[str] = []
    for name, entry in sorted(baseline_root.items()):
        if name == ".git":
            continue
        src = target / name
        if not src.exists():
            continue
        if entry.get("protected") or protected_path(name):
            blockers.append(name)
            continue
        if name in CONTROL_ITEMS:
            current_hash = path_hash(src)
            original_hash = file_hashes.get(name)
            if original_hash is None or current_hash != original_hash:
                continue
        dst = import_root / name
        if dst.exists():
            blockers.append(f"destination exists: {dst.relative_to(target).as_posix()}")
            continue
        if args.dry_run:
            print(f"DRY-RUN move {src} -> {dst}")
        else:
            dst.parent.mkdir(parents=True, exist_ok=True)
            shutil.move(str(src), str(dst))
        moved.append({"from": name, "to": dst.relative_to(target).as_posix()})
    status = "blocked" if blockers else "ok"
    append_log(target, "normalize", status, {"moved": moved, "blockers": blockers}, args.dry_run)
    print(f"[normalize] moved={len(moved)} blockers={len(blockers)}")
    if blockers and not args.allow_blocked_normalize:
        raise SystemExit("normalize blocked by protected/conflicting paths: " + ", ".join(blockers))
    return {"moved": moved, "blockers": blockers}


def current_hash_index(target: Path) -> dict[str, list[str]]:
    index: dict[str, list[str]] = {}
    for root, dirnames, filenames in os.walk(target):
        root_path = Path(root)
        dirnames[:] = [d for d in dirnames if d not in EXCLUDE_DIR_NAMES]
        if ".git" in root_path.parts:
            continue
        for filename in filenames:
            path = root_path / filename
            if path.stat().st_size > LARGE_HASH_LIMIT:
                continue
            digest = sha256_file(path)
            index.setdefault(digest, []).append(rel_posix(path, target))
    return index


def integrity_result(target: Path) -> dict[str, Any]:
    baseline_path = state_path(target, BASELINE_FILE)
    if not baseline_path.exists():
        raise SystemExit(f"missing baseline: {baseline_path}")
    baseline_data = read_json(baseline_path)
    index = current_hash_index(target)
    missing: list[dict[str, Any]] = []
    present = 0
    for row in baseline_data["tracked_files"]:
        digest = row.get("sha256")
        if not digest:
            original = target / row["path"]
            if original.exists() and original.stat().st_size == row["size"]:
                present += 1
            else:
                missing.append(row)
            continue
        if digest in index:
            present += 1
        else:
            missing.append(row)
    return {
        "schema": "template-adoption-integrity-v1",
        "checked_at": now_iso(),
        "baseline_files": len(baseline_data["tracked_files"]),
        "present": present,
        "missing": missing,
        "ok": not missing,
    }


def prove(args: argparse.Namespace) -> dict[str, Any]:
    target = args.target.resolve()
    require_git_repo(target)
    plan = read_json(state_path(target, PLAN_FILE))
    integrity = integrity_result(target)
    governance = None
    if (target / "scripts" / "validate-governance.py").exists():
        governance = run([sys.executable, "scripts/validate-governance.py", "--strict"], target, timeout=180)
    original_test = None
    if plan.get("test_command"):
        cwd = target / plan["import_root"]
        if not cwd.exists():
            cwd = target
        original_test = run(plan["test_command"], cwd, shell=True, timeout=args.test_timeout)
    report = {
        "schema": "template-adoption-proof-v1",
        "created_at": now_iso(),
        "target": str(target),
        "integrity": integrity,
        "governance": governance,
        "original_test": original_test,
    }
    if not args.dry_run:
        write_report(target, plan, report)
    append_log(target, "prove", "ok" if integrity["ok"] else "failed", report, args.dry_run)
    print(
        "[prove] integrity="
        + ("ok" if integrity["ok"] else "failed")
        + f" governance_rc={None if governance is None else governance['returncode']}"
    )
    return report


def write_report(target: Path, plan: dict[str, Any], proof: dict[str, Any]) -> None:
    governance = proof.get("governance")
    original_test = proof.get("original_test")
    phase_rows = read_phase_log(target)
    normalize_rows = [r for r in phase_rows if r.get("phase") == "normalize"]
    normalize = normalize_rows[-1].get("details", {}) if normalize_rows else {}
    moved = normalize.get("moved", [])
    blockers = normalize.get("blockers", [])
    current_pollution = [
        e["path"]
        for e in list_root_entries(target)
        if not e["allowed_root"] and not e["protected"] and not e["template_control_item"]
    ]
    lines = [
        "# Template Adoption Report",
        "",
        f"- created_at: `{proof['created_at']}`",
        f"- target: `{proof['target']}`",
        f"- policy: `{plan.get('policy')}`",
        f"- import_root: `{plan.get('import_root')}`",
        f"- integrity: `{'ok' if proof['integrity']['ok'] else 'failed'}`",
        f"- governance_returncode: `{None if governance is None else governance['returncode']}`",
        f"- original_test_returncode: `{None if original_test is None else original_test['returncode']}`",
        f"- baseline_files_present: `{proof['integrity']['present']}/{proof['integrity']['baseline_files']}`",
        f"- moved_root_entries: `{len(moved)}`",
        f"- normalize_blockers: `{len(blockers)}`",
        f"- remaining_root_pollution: `{len(current_pollution)}`",
        "",
        "## Notes",
        "",
        "- This report is generated by `scripts/adopt-existing-repo.py`.",
        "- Original tracked files are checked by content hash, not by path.",
        "- Before staging, Git may show original paths as deleted and imported paths as untracked; "
        "that is expected for a move-based migration. Use `check-adoption-integrity.py` to verify bytes.",
        "- Protected bytes are not moved by the conservative policy.",
        "",
        "## Normalize",
        "",
    ]
    if moved:
        lines.extend(["Moved root entries:", ""])
        lines.extend(f"- `{row['from']}` -> `{row['to']}`" for row in moved)
        lines.append("")
    else:
        lines.extend(["No root entries were moved.", ""])
    if blockers:
        lines.extend(["Blockers:", ""])
        lines.extend(f"- `{b}`" for b in blockers)
        lines.append("")
    if current_pollution:
        lines.extend(["Remaining root pollution:", ""])
        lines.extend(f"- `{p}`" for p in current_pollution)
        lines.append("")
    else:
        lines.extend(["Remaining root pollution: `0`", ""])
    path = target / REPORT_PATH
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("\n".join(lines), encoding="utf-8")


def read_phase_log(target: Path) -> list[dict[str, Any]]:
    path = state_path(target, LOG_FILE)
    if not path.exists():
        return []
    rows: list[dict[str, Any]] = []
    for line in path.read_text(encoding="utf-8").splitlines():
        if not line.strip():
            continue
        rows.append(json.loads(line))
    return rows


def parse_args(argv: list[str]) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("target", type=Path)
    parser.add_argument(
        "--phase",
        choices=["discover", "baseline", "scaffold", "normalize", "prove", "all"],
        default="discover",
    )
    parser.add_argument("--policy", choices=["conservative"], default="conservative")
    parser.add_argument("--project-name")
    parser.add_argument("--test-command", default="auto")
    parser.add_argument("--test-timeout", type=int, default=120)
    parser.add_argument("--dry-run", action="store_true")
    parser.add_argument(
        "--allow-blocked-normalize",
        action="store_true",
        help="record normalize blockers but continue; useful for partial reports",
    )
    return parser.parse_args(argv)


def main(argv: list[str]) -> int:
    args = parse_args(argv)
    phases = ["discover", "baseline", "scaffold", "normalize", "prove"]
    if args.phase != "all":
        phases = [args.phase]
    for phase in phases:
        {
            "discover": discover,
            "baseline": baseline,
            "scaffold": scaffold,
            "normalize": normalize,
            "prove": prove,
        }[phase](args)
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
