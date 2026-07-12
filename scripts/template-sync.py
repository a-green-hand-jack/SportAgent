#!/usr/bin/env python3
"""下游追平：把上游 template 的框架层同步进本（下游）repo。

四站闭环的第④站，见 .agent/template-versioning-policy.md。本脚本**在下游 repo 内**运行：
  1. 读下游 .template.toml（origin + 当前 version）与上游 VERSION（目标 version）。
  2. 若跨了 MAJOR 且未加 --allow-major → 停下让 human reconcile（MAJOR 定义上不可全自动）。
  3. 读上游 template-manifest.toml，逐个上游文件按 kind 处理：
       framework 覆盖 / generated 跳过(稍后重建) / project 不碰 / scaffold 缺才建 / merge 只换哨兵块。
  4. 跑下游 scripts/sync-codex-adapters.py 重建 .codex/.agents 适配。
  5. 写回下游 .template.toml 的 version。
  6. 跑 validate-governance.py 验收（除非 --no-verify）。
  7. 反查上游「你上报的 from-downstream issue」这次关了哪些（best-effort，无 gh/网络则跳过）。

无第三方硬依赖（tomllib 读；.template.toml 手写）。退出码 0 = 成功，非 0 = 失败或需人工介入。
用法：
  python scripts/template-sync.py --from /path/to/upstream/template-checkout
  python scripts/template-sync.py --from ... --allow-major     # 明确接受破坏性追平
  python scripts/template-sync.py --from ... --dry-run          # 只报告不落地
"""
from __future__ import annotations

import argparse
import fnmatch
import json
import re
import subprocess
import sys
import tomllib
from pathlib import Path

DOWNSTREAM = Path(__file__).resolve().parent.parent
SEMVER_RE = re.compile(r"^v?(\d+)\.(\d+)\.(\d+)$")
SENTINEL_BEGIN = "<!-- template:begin -->"
SENTINEL_END = "<!-- template:end -->"


def parse_semver(raw: str) -> tuple[int, int, int]:
    m = SEMVER_RE.match(raw.strip())
    if not m:
        raise SystemExit(f"ERROR 非法 semver：{raw!r}")
    return int(m.group(1)), int(m.group(2)), int(m.group(3))


def cross_level(old: tuple[int, int, int], new: tuple[int, int, int]) -> str | None:
    if new < old:
        raise SystemExit(f"ERROR 上游版本 {new} 低于下游 {old}，拒绝降级")
    if new == old:
        return None
    if new[0] != old[0]:
        return "major"
    if new[1] != old[1]:
        return "minor"
    return "patch"


def match_glob(path: str, glob: str) -> bool:
    if glob.endswith("/**"):
        prefix = glob[:-3]
        return path == prefix or path.startswith(prefix + "/")
    return fnmatch.fnmatch(path, glob)


def classify(path: str, rules: list[dict]) -> str | None:
    for rule in rules:
        if match_glob(path, rule.get("glob", "")):
            return rule.get("kind")
    return None


def upstream_files(upstream: Path) -> list[str]:
    if (upstream / ".git").exists():
        out = subprocess.run(
            ["git", "ls-files"], cwd=upstream, capture_output=True, text=True, check=True
        ).stdout
        return [ln for ln in out.splitlines() if ln]
    # 无 git：rglob，排除常见产物目录。
    skip = {".git", ".venv", "__pycache__", ".ruff_cache", ".mypy_cache", ".pytest_cache"}
    files = []
    for p in upstream.rglob("*"):
        if p.is_file() and not any(part in skip for part in p.relative_to(upstream).parts):
            files.append(p.relative_to(upstream).as_posix())
    return files


def sentinel_block(text: str) -> str | None:
    i = text.find(SENTINEL_BEGIN)
    j = text.find(SENTINEL_END)
    if i == -1 or j == -1 or j < i:
        return None
    return text[i : j + len(SENTINEL_END)]


class Report:
    def __init__(self) -> None:
        self.updated: list[str] = []
        self.created: list[str] = []
        self.skipped_project: int = 0
        self.scaffold_kept: list[str] = []
        self.merge_warn: list[str] = []
        self.unclassified: list[str] = []


def sync_files(upstream: Path, rules: list[dict], dry: bool) -> Report:
    rep = Report()
    for rel in upstream_files(upstream):
        kind = classify(rel, rules)
        src = upstream / rel
        dst = DOWNSTREAM / rel
        if kind in (None,):
            rep.unclassified.append(rel)
            continue
        if kind in ("generated", "project"):
            if kind == "project":
                rep.skipped_project += 1
            continue
        src_bytes = src.read_bytes()
        exists = dst.exists()
        if kind == "framework":
            if not exists or dst.read_bytes() != src_bytes:
                if not dry:
                    dst.parent.mkdir(parents=True, exist_ok=True)
                    dst.write_bytes(src_bytes)
                (rep.created if not exists else rep.updated).append(rel)
        elif kind == "scaffold":
            if not exists:
                if not dry:
                    dst.parent.mkdir(parents=True, exist_ok=True)
                    dst.write_bytes(src_bytes)
                rep.created.append(rel)
            else:
                rep.scaffold_kept.append(rel)
        elif kind == "merge":
            up_block = sentinel_block(src.read_text(encoding="utf-8", errors="replace"))
            if up_block is None:
                rep.merge_warn.append(f"{rel}（上游无哨兵块，跳过；需人工 reconcile）")
                continue
            if not exists:
                if not dry:
                    dst.parent.mkdir(parents=True, exist_ok=True)
                    dst.write_bytes(src_bytes)
                rep.created.append(rel)
                continue
            down_text = dst.read_text(encoding="utf-8", errors="replace")
            down_block = sentinel_block(down_text)
            if down_block is None:
                rep.merge_warn.append(f"{rel}（下游无哨兵块，跳过；需人工 reconcile）")
                continue
            if down_block != up_block:
                if not dry:
                    # 只替换定位到的那一块（count=1），避免子串在文件他处重复时误伤。
                    dst.write_text(down_text.replace(down_block, up_block, 1), encoding="utf-8")
                rep.updated.append(rel)
    return rep


def read_template_toml() -> dict:
    f = DOWNSTREAM / ".template.toml"
    if not f.exists():
        raise SystemExit(
            "ERROR 缺少 .template.toml —— 这看起来不是本模板的下游 repo。"
            "首次采用请走 adopt-existing-repo。"
        )
    return tomllib.loads(f.read_text(encoding="utf-8")).get("template", {})


def write_template_version(origin: str, version: str, extra: dict) -> None:
    # 用 json.dumps 生成带正确转义的 TOML basic string（引号/反斜杠安全）。
    lines = ["[template]", f"origin = {json.dumps(origin, ensure_ascii=False)}",
             f"version = {json.dumps(version, ensure_ascii=False)}"]
    for k, v in extra.items():
        if k in ("origin", "version"):
            continue
        lines.append(f"{k} = {json.dumps(str(v), ensure_ascii=False)}")
    (DOWNSTREAM / ".template.toml").write_text("\n".join(lines) + "\n", encoding="utf-8")


def closed_downstream_issues(origin: str) -> None:
    try:
        out = subprocess.run(
            ["gh", "issue", "list", "--repo", origin, "--label", "from-downstream",
             "--state", "closed", "--limit", "20", "--json", "number,title"],
            capture_output=True, text=True, timeout=20,
        )
        if out.returncode != 0 or not out.stdout.strip():
            return
        issues = json.loads(out.stdout)
        if issues:
            print("\n闭环回执 —— 上游已关闭的 from-downstream issue（核对你上报的是否已随本次追平进来）：")
            for it in issues[:20]:
                print(f"  #{it['number']} {it['title']}")
    except Exception:  # noqa: BLE001  best-effort，无 gh/网络就静默
        return


def run_validator(dry: bool) -> int:
    if dry:
        print("\n[dry-run] 跳过 validate-governance")
        return 0
    print("\n=== validate-governance（追平后验收）===", flush=True)
    return subprocess.run(
        [sys.executable, str(DOWNSTREAM / "scripts" / "validate-governance.py")],
        cwd=DOWNSTREAM,
    ).returncode


def main() -> int:
    p = argparse.ArgumentParser()
    p.add_argument("--from", dest="upstream", required=True,
                   help="上游 template 的本地 checkout 路径")
    p.add_argument("--allow-major", action="store_true", help="接受 MAJOR 破坏性追平")
    p.add_argument("--dry-run", action="store_true", help="只报告不落地")
    p.add_argument("--no-verify", action="store_true", help="跳过 validate-governance")
    args = p.parse_args()

    upstream = Path(args.upstream).resolve()
    if not upstream.is_dir():
        raise SystemExit(f"ERROR 上游路径不存在：{upstream}")
    if upstream == DOWNSTREAM:
        raise SystemExit("ERROR --from 指向了当前 repo 自身")

    meta = read_template_toml()
    origin = meta.get("origin", "")
    cur_raw = meta.get("version", "v0.0.0")
    up_version_f = upstream / "VERSION"
    if not up_version_f.exists():
        raise SystemExit("ERROR 上游缺少 VERSION 文件")
    up_raw = up_version_f.read_text(encoding="utf-8").strip()

    old, new = parse_semver(cur_raw), parse_semver(up_raw)
    level = cross_level(old, new)
    print(f"[template-sync] 下游 {cur_raw} → 上游 {up_raw}"
          + (f"（跨 {level.upper()}）" if level else "（版本相同，仍会对齐文件）"))
    if level == "major" and not args.allow_major:
        print(
            "\nSTOP：这是 MAJOR 追平，定义上需人工 reconcile（见 template-versioning-policy）。\n"
            "先读上游 CHANGELOG.md，确认破坏性变更点，再加 --allow-major 重跑。"
        )
        return 2

    manifest_f = upstream / "template-manifest.toml"
    if not manifest_f.exists():
        raise SystemExit("ERROR 上游缺少 template-manifest.toml")
    rules = tomllib.loads(manifest_f.read_text(encoding="utf-8")).get("rule", [])

    rep = sync_files(upstream, rules, args.dry_run)

    print(f"\n覆盖(framework/merge 更新) {len(rep.updated)} · 新建 {len(rep.created)}"
          f" · 保护(project) {rep.skipped_project} · scaffold 保留 {len(rep.scaffold_kept)}")
    for f in rep.updated:
        print(f"  ~ {f}")
    for f in rep.created:
        print(f"  + {f}")
    for w in rep.merge_warn:
        print(f"  WARN merge: {w}")
    for u in rep.unclassified:
        print(f"  WARN 未分类(补 template-manifest.toml): {u}")

    # 生成层：覆盖完 canonical 后重建 codex 适配。
    codex_rc = 0
    if not args.dry_run:
        print("\n=== 重建 Codex 适配 ===", flush=True)
        codex_rc = subprocess.run(
            [sys.executable, str(DOWNSTREAM / "scripts" / "sync-codex-adapters.py")],
            cwd=DOWNSTREAM,
        ).returncode
        if codex_rc != 0:
            print(f"ERROR Codex 适配重建失败（exit {codex_rc}）：.codex/.agents 可能已 stale，"
                  "别信任本次同步。检查 scripts/sync-codex-adapters.py。")
        write_template_version(origin, up_raw, meta)
        print(f"[template-sync] .template.toml version → {up_raw}")

    rc = 0 if args.no_verify else run_validator(args.dry_run)
    if origin:
        closed_downstream_issues(origin)

    if rep.unclassified:
        print("\n提醒：有未分类文件，请在上游 template-manifest.toml 补规则后再发下一版。")
    ok = rc == 0 and codex_rc == 0
    print(f"\n[template-sync] {'OK' if ok else 'FAIL（codex 重建或 validator 未过，需修）'}")
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main())
