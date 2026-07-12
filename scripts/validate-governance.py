#!/usr/bin/env python3
"""总治理门禁。聚合 harness 检查、anatomy 漂移检查与若干治理规则。

治理规则：
1. .gitignore 保护危险路径（data/runs/models bytes、checkpoints、wandb、private、.env）。
2. lab/{research,artifacts,data,models}/*.yaml 可解析（有 PyYAML 时深检，否则做轻量结构检查）。
3. 大 bytes 未被误加进 Git（有 git 时检查 tracked 文件不含受保护 bytes 路径）。
4. 证据链一致：claims↔evidence 引用可解析，且 claim 强度 ≤ 最强证据（overclaim 拦截）。
5. 发布闸门 / 回归矩阵一致：release-gates.yaml 与 regression-matrix.yaml 的枚举字段合法，
   且一旦离开占位默认状态（gate_status/last_status 不再是 open/unknown），其 claim 引用
   必须指向 claims.yaml 中真实存在的 claim（防止「已判定放行/已判定回归通过」却引用空主张）。
6. merge 哨兵：template-manifest.toml 标为 merge 的文件必须有成对 template:begin/end 块，
   否则 template-sync 会整体跳过它、模板更新传不到下游（见 template-versioning-policy.md）。

先跑子检查（作为独立进程，便于单独调用），再跑本文件治理规则。
无第三方依赖（PyYAML 可选）。退出码 0 = 全通过，非 0 = 有失败。
用法：python scripts/validate-governance.py [--strict]
"""
from __future__ import annotations

import subprocess
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
PY = sys.executable

PROTECTED_GITIGNORE_TOKENS = [
    "lab/runs", "lab/data", "lab/models", "checkpoints",
    "wandb", "lab/infra/private", ".env",
]

errors: list[str] = []
warnings: list[str] = []


def run_subcheck(script: str, strict: bool) -> None:
    args = [PY, str(REPO / "scripts" / script)]
    if strict:
        args.append("--strict")
    print(f"\n=== {script} ===", flush=True)
    result = subprocess.run(args, cwd=REPO)
    if result.returncode != 0:
        errors.append(f"{script} 失败（exit {result.returncode}）")


def check_gitignore() -> None:
    gi = REPO / ".gitignore"
    if not gi.exists():
        errors.append("缺少 .gitignore")
        return
    text = gi.read_text(encoding="utf-8")
    for token in PROTECTED_GITIGNORE_TOKENS:
        if token not in text:
            errors.append(f".gitignore 未提及受保护路径：{token}")


def check_yaml() -> None:
    # 核心索引/ledger 目录（见 .agent/artifact-policy.md）。
    yaml_files = (
        list((REPO / "lab" / "research").glob("*.yaml"))
        + list((REPO / "lab" / "artifacts").glob("*.yaml"))
        + list((REPO / "lab" / "data").glob("*.yaml"))
        + list((REPO / "lab" / "models").glob("*.yaml"))
    )
    try:
        import yaml  # type: ignore
        loader = lambda t: yaml.safe_load(t)  # noqa: E731
        deep = True
    except ImportError:
        loader = None
        deep = False
        warnings.append("未安装 PyYAML：跳过 YAML 深度解析，仅做轻量检查")
    for f in yaml_files:
        text = f.read_text(encoding="utf-8")
        if "\t" in text:
            errors.append(f"YAML 含制表符（应用空格）：{f.relative_to(REPO)}")
        if deep and loader is not None:
            try:
                loader(text)
            except Exception as e:  # noqa: BLE001
                errors.append(f"YAML 解析失败：{f.relative_to(REPO)}: {e}")


def check_evidence_chain() -> None:
    """证据链一致性 + overclaim 拦截（见 lab/research/ANATOMY.md、.agent/principles.md）。

    只在有 PyYAML 时运行（需解析结构）；否则跳过并告警。
    规则：
    - 引用完整：claim.evidence[] 里的 ev id 必须存在；evidence.supports_claim 必须指向已知 claim。
    - overclaim：证据分层 log<metric<table<figure<paper-claim。
        · status=supported 需 ≥1 条证据，且最强证据 ≥ metric。
        · status=partial 需 ≥1 条证据。
        · verified_by_fresh_reviewer=true（paper-grade）需 ≥1 条 grade=paper-claim
          且该证据自身 verified_by_fresh_reviewer=true。
    模板占位（claim status=proposed、evidence=[]）天然通过，不误伤。
    """
    research = REPO / "lab" / "research"
    claims_f, ev_f = research / "claims.yaml", research / "evidence.yaml"
    if not (claims_f.exists() and ev_f.exists()):
        return
    try:
        import yaml  # type: ignore
    except ImportError:
        warnings.append("未安装 PyYAML：跳过证据链一致性检查")
        return
    try:
        claims = (yaml.safe_load(claims_f.read_text(encoding="utf-8")) or {}).get("claims") or []
        evlist = (yaml.safe_load(ev_f.read_text(encoding="utf-8")) or {}).get("evidence") or []
    except Exception as e:  # noqa: BLE001
        errors.append(f"证据链解析失败：{e}")
        return

    grade_rank = {"log": 1, "metric": 2, "table": 3, "figure": 4, "paper-claim": 5}
    ev_by_id = {e.get("id"): e for e in evlist if isinstance(e, dict)}
    claim_ids = {c.get("id") for c in claims if isinstance(c, dict)}

    for e in evlist:
        if isinstance(e, dict) and e.get("supports_claim") not in claim_ids:
            errors.append(f"evidence {e.get('id')} 的 supports_claim 指向未知 claim：{e.get('supports_claim')}")

    for c in claims:
        if not isinstance(c, dict):
            continue
        cid, status = c.get("id"), c.get("status")
        refs = c.get("evidence") or []
        linked = [ev_by_id[r] for r in refs if r in ev_by_id]
        for r in refs:
            if r not in ev_by_id:
                errors.append(f"claim {cid} 引用未知 evidence：{r}")
        strongest = max((grade_rank.get(e.get("grade"), 0) for e in linked), default=0)
        if status in ("partial", "supported") and not linked:
            errors.append(f"overclaim：claim {cid} status={status} 但无 evidence 支撑")
        if status == "supported" and strongest < grade_rank["metric"]:
            errors.append(f"overclaim：claim {cid} status=supported 但最强证据低于 metric")
        if c.get("verified_by_fresh_reviewer") is True:
            paper = [e for e in linked if e.get("grade") == "paper-claim"
                     and e.get("verified_by_fresh_reviewer") is True]
            if not paper:
                errors.append(
                    f"overclaim：claim {cid} 标记 paper-grade（fresh reviewer）"
                    "但缺少经 fresh reviewer 的 paper-claim 级证据"
                )


def _load_claim_ids(research: Path):
    """读 lab/research/claims.yaml，返回真实 claim id 集合；解析失败返回 None。"""
    import yaml  # type: ignore

    claims_f = research / "claims.yaml"
    if not claims_f.exists():
        return set()
    try:
        claims = (yaml.safe_load(claims_f.read_text(encoding="utf-8")) or {}).get("claims") or []
    except Exception:  # noqa: BLE001
        return None
    return {c.get("id") for c in claims if isinstance(c, dict)}


def _is_placeholder(value) -> bool:
    return isinstance(value, str) and value.strip().startswith("<")


def check_release_gates() -> None:
    """发布闸门一致性（见 lab/research/ANATOMY.md）。

    只在有 PyYAML 时运行；否则跳过并告警。
    规则：
    - gate_status 必须 ∈ {open, passed, blocked}。
    - 只有 gate_status != open 时才校验 for_claim：占位符（`<...>`）或引用未知 claim 均报错。
    模板占位（gate_status=open、for_claim=claim-000 未必真实存在）天然通过，不误伤。
    """
    research = REPO / "lab" / "research"
    gates_f = research / "release-gates.yaml"
    if not gates_f.exists():
        return
    try:
        import yaml  # type: ignore
    except ImportError:
        warnings.append("未安装 PyYAML：跳过发布闸门一致性检查")
        return
    try:
        gates = (yaml.safe_load(gates_f.read_text(encoding="utf-8")) or {}).get("gates") or []
    except Exception as e:  # noqa: BLE001
        errors.append(f"release-gates.yaml 解析失败：{e}")
        return
    claim_ids = _load_claim_ids(research)
    if claim_ids is None:
        errors.append("claims.yaml 解析失败，无法校验 release-gates.yaml 的 for_claim 引用")
        return

    valid_status = {"open", "passed", "blocked"}
    for g in gates:
        if not isinstance(g, dict):
            continue
        gid, status = g.get("id"), g.get("gate_status")
        if status not in valid_status:
            errors.append(f"gate {gid} 的 gate_status 非法：{status}")
            continue
        if status == "open":
            continue
        for_claim = g.get("for_claim")
        if _is_placeholder(for_claim):
            errors.append(f"gate {gid} 状态为 {status} 但 for_claim 仍是未填占位符")
        elif for_claim not in claim_ids:
            errors.append(f"gate {gid} 的 for_claim 引用未知 claim：{for_claim}")


def check_regression_matrix() -> None:
    """回归矩阵一致性（见 lab/research/ANATOMY.md）。

    只在有 PyYAML 时运行；否则跳过并告警。
    规则：
    - check_kind 必须 ∈ {test, smoke, metric-threshold, numerical-equivalence}。
    - last_status 必须 ∈ {unknown, pass, fail}。
    - 只有 last_status != unknown 时才校验 guards_claim：占位符或引用未知 claim 均报错。
    模板占位（last_status=unknown、guards_claim=claim-000 未必真实存在）天然通过，不误伤。
    """
    research = REPO / "lab" / "research"
    reg_f = research / "regression-matrix.yaml"
    if not reg_f.exists():
        return
    try:
        import yaml  # type: ignore
    except ImportError:
        warnings.append("未安装 PyYAML：跳过回归矩阵一致性检查")
        return
    try:
        regs = (yaml.safe_load(reg_f.read_text(encoding="utf-8")) or {}).get("regressions") or []
    except Exception as e:  # noqa: BLE001
        errors.append(f"regression-matrix.yaml 解析失败：{e}")
        return
    claim_ids = _load_claim_ids(research)
    if claim_ids is None:
        errors.append("claims.yaml 解析失败，无法校验 regression-matrix.yaml 的 guards_claim 引用")
        return

    valid_kind = {"test", "smoke", "metric-threshold", "numerical-equivalence"}
    valid_status = {"unknown", "pass", "fail"}
    for r in regs:
        if not isinstance(r, dict):
            continue
        rid, kind, status = r.get("id"), r.get("check_kind"), r.get("last_status")
        if kind not in valid_kind:
            errors.append(f"regression {rid} 的 check_kind 非法：{kind}")
        if status not in valid_status:
            errors.append(f"regression {rid} 的 last_status 非法：{status}")
            continue
        if status == "unknown":
            continue
        guards_claim = r.get("guards_claim")
        if _is_placeholder(guards_claim):
            errors.append(f"regression {rid} 状态为 {status} 但 guards_claim 仍是未填占位符")
        elif guards_claim not in claim_ids:
            errors.append(f"regression {rid} 的 guards_claim 引用未知 claim：{guards_claim}")


def _classify(path: str, rules: list) -> str | None:
    """按 template-manifest.toml 规则顺序，返回 path 的第一条匹配 kind。"""
    import fnmatch
    for rule in rules:
        glob = rule.get("glob", "")
        if glob.endswith("/**"):
            pre = glob[:-3]
            hit = path == pre or path.startswith(pre + "/")
        else:
            hit = fnmatch.fnmatch(path, glob)
        if hit:
            return rule.get("kind")
    return None


def check_merge_sentinels() -> None:
    """merge 类文件必须有成对 template:begin/end 哨兵块（见 .agent/template-versioning-policy.md）。

    template-sync 只替换块内内容；merge 文件缺哨兵会被整体跳过，模板更新传不到下游。
    分类唯一源是 template-manifest.toml。只校验实际存在的 tracked 文件。
    """
    manifest = REPO / "template-manifest.toml"
    if not manifest.exists():
        return
    try:
        import tomllib
    except ImportError:  # Python < 3.11
        warnings.append("无 tomllib（Python<3.11）：跳过 merge 哨兵检查")
        return
    try:
        rules = tomllib.loads(manifest.read_text(encoding="utf-8")).get("rule", [])
    except Exception as e:  # noqa: BLE001
        errors.append(f"template-manifest.toml 解析失败：{e}")
        return

    try:
        out = subprocess.run(
            ["git", "ls-files"], cwd=REPO, capture_output=True, text=True, check=True
        ).stdout
        files = [ln for ln in out.splitlines() if ln]
    except (subprocess.CalledProcessError, FileNotFoundError):
        files = [
            p.relative_to(REPO).as_posix()
            for p in REPO.rglob("*")
            if p.is_file() and ".git" not in p.relative_to(REPO).parts
        ]

    begin, end = "<!-- template:begin -->", "<!-- template:end -->"
    for rel in files:
        if _classify(rel, rules) != "merge":
            continue
        f = REPO / rel
        if not f.exists():
            continue
        text = f.read_text(encoding="utf-8", errors="replace")
        i, j = text.find(begin), text.find(end)
        if i == -1 or j == -1:
            errors.append(f"merge 文件缺 template:begin/end 哨兵块：{rel}")
        elif j < i:
            errors.append(f"merge 文件哨兵顺序错误（end 在 begin 前）：{rel}")
        elif text.count(begin) != 1 or text.count(end) != 1:
            # 重复哨兵对会让 template-sync 的块定位/替换有歧义（见 template-sync.sentinel_block）。
            errors.append(f"merge 文件哨兵不唯一（begin/end 应各恰好一次）：{rel}")


def check_tracked_bytes() -> None:
    git_dir = REPO / ".git"
    if not git_dir.exists():
        warnings.append("尚未 git init：跳过 tracked bytes 检查")
        return
    try:
        out = subprocess.run(
            ["git", "ls-files"], cwd=REPO, capture_output=True, text=True, check=True
        ).stdout
    except (subprocess.CalledProcessError, FileNotFoundError):
        warnings.append("无法运行 git ls-files：跳过 tracked bytes 检查")
        return
    bad_suffixes = (".ckpt", ".pt", ".pth", ".safetensors")
    bad_prefixes = ("lab/runs/", "wandb/", "lab/infra/private/")
    for line in out.splitlines():
        if line.endswith(bad_suffixes):
            errors.append(f"权重 bytes 被误加进 Git：{line}")
        if any(line.startswith(p) for p in bad_prefixes) and not line.endswith(
            (".gitkeep", "README.md", "AGENTS.md", "CLAUDE.md", "ANATOMY.md")
        ):
            errors.append(f"受保护目录 bytes 被误加进 Git：{line}")


def main() -> int:
    strict = "--strict" in sys.argv
    run_subcheck("check-agent-harness.py", strict)
    run_subcheck("check-anatomy-drift.py", strict)

    print("\n=== governance ===", flush=True)
    check_gitignore()
    check_yaml()
    check_evidence_chain()
    check_release_gates()
    check_regression_matrix()
    check_merge_sentinels()
    check_tracked_bytes()
    for w in warnings:
        print(f"WARN  {w}")
    for e in errors:
        print(f"ERROR {e}")

    n_e, n_w = len(errors), len(warnings)
    ok = not n_e and not (strict and n_w)
    print(f"\n[validate-governance] {'OK' if ok else 'FAIL'} — {n_e} error(s), {n_w} warning(s)")
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main())
