#!/usr/bin/env python3
"""Read local Codex and Claude Code quota snapshots without touching credentials."""
from __future__ import annotations

import argparse
import datetime as dt
import glob
import json
import sqlite3
import sys
from pathlib import Path
from typing import Any


UTC = dt.timezone.utc
ROLES = ("impl", "ui", "research", "planning", "audit")
DEFAULT_PASEO_PROVIDERS = {
    "impl": "codex/gpt-5.5",
    "ui": "claude/claude-opus-4-8",
    "research": "codex/gpt-5.6-terra",
    "planning": "codex/gpt-5.6-sol",
    "audit": "claude/claude-sonnet-5",
}


def now_utc() -> dt.datetime:
    return dt.datetime.now(UTC)


def parse_time(value: Any) -> dt.datetime | None:
    if value is None or value == "":
        return None
    if isinstance(value, (int, float)):
        # Codex JSONL stores reset times as epoch seconds.
        if value > 10_000_000_000:
            value = value / 1000
        return dt.datetime.fromtimestamp(value, UTC)
    if isinstance(value, str):
        text = value.strip()
        if not text:
            return None
        if text.endswith("Z"):
            text = text[:-1] + "+00:00"
        try:
            parsed = dt.datetime.fromisoformat(text)
        except ValueError:
            return None
        if parsed.tzinfo is None:
            parsed = parsed.replace(tzinfo=UTC)
        return parsed.astimezone(UTC)
    return None


def iso(value: dt.datetime | None) -> str | None:
    if value is None:
        return None
    return value.astimezone(UTC).isoformat().replace("+00:00", "Z")


def pct(value: Any) -> float | None:
    if value is None or value == "":
        return None
    try:
        return round(float(value), 2)
    except (TypeError, ValueError):
        return None


def remaining(used: float | None) -> float | None:
    if used is None:
        return None
    return round(max(0.0, 100.0 - used), 2)


def window(used: Any, reset_at: Any) -> dict[str, Any]:
    used_percent = pct(used)
    return {
        "used_percent": used_percent,
        "remaining_percent": remaining(used_percent),
        "reset_at": iso(parse_time(reset_at)),
    }


def provider_unavailable(provider: str, reason: str) -> dict[str, Any]:
    return {
        "provider": provider,
        "status": "unavailable",
        "source": None,
        "captured_at": None,
        "windows": {},
        "warnings": [reason],
    }


def usage_db_path() -> Path:
    return Path.home() / ".claude" / ".search-index" / "usage.db"


def latest_usage_rows(db_path: Path) -> tuple[sqlite3.Row | None, sqlite3.Row | None]:
    if not db_path.exists():
        return None, None
    con = sqlite3.connect(f"file:{db_path}?mode=ro", uri=True)
    con.row_factory = sqlite3.Row
    try:
        claude = con.execute(
            """
            select * from api_usage_snapshots
            where claude_five_hour_used is not null
               or claude_seven_day_used is not null
               or claude_limits_json is not null
            order by datetime(captured_at) desc, id desc
            limit 1
            """
        ).fetchone()
        codex = con.execute(
            """
            select * from api_usage_snapshots
            where codex_primary_reset is not null
               or codex_secondary_reset is not null
            order by datetime(captured_at) desc, id desc
            limit 1
            """
        ).fetchone()
    finally:
        con.close()
    return claude, codex


def recent_usage_velocity(db_path: Path, days: int = 7) -> dict[str, Any]:
    if not db_path.exists():
        return {}
    since = (now_utc().date() - dt.timedelta(days=days - 1)).isoformat()
    con = sqlite3.connect(f"file:{db_path}?mode=ro", uri=True)
    con.row_factory = sqlite3.Row
    try:
        rows = con.execute(
            """
            select source, date, sum(total_tokens) as tokens,
                   sum(message_count) as messages, sum(total_cost) as cost_proxy
            from daily_usage
            where date >= ?
            group by source, date
            """,
            (since,),
        ).fetchall()
    except sqlite3.Error:
        return {}
    finally:
        con.close()

    by_source: dict[str, list[sqlite3.Row]] = {}
    for row in rows:
        by_source.setdefault(row["source"], []).append(row)
    result: dict[str, Any] = {}
    today = now_utc().date().isoformat()
    for source, source_rows in by_source.items():
        tokens = [int(row["tokens"] or 0) for row in source_rows]
        messages = [int(row["messages"] or 0) for row in source_rows]
        costs = [float(row["cost_proxy"] or 0.0) for row in source_rows]
        today_row = next((row for row in source_rows if row["date"] == today), None)
        result[source] = {
            "window_days": days,
            "days_observed": len(source_rows),
            "today_tokens": int(today_row["tokens"] or 0) if today_row else 0,
            "avg_tokens_per_day": round(sum(tokens) / max(1, len(tokens)), 2),
            "today_messages": int(today_row["messages"] or 0) if today_row else 0,
            "avg_messages_per_day": round(sum(messages) / max(1, len(messages)), 2),
            "cost_proxy_note": "local usage DB estimate; subscription routing should treat this as burn proxy, not metered billing",
            "today_cost_proxy": round(float(today_row["cost_proxy"] or 0.0), 4) if today_row else 0.0,
            "avg_cost_proxy_per_day": round(sum(costs) / max(1, len(costs)), 4),
        }
    return result


def claude_from_row(row: sqlite3.Row | None, db_path: Path) -> dict[str, Any]:
    if row is None:
        return provider_unavailable("claude_code", f"no Claude usage snapshot in {db_path}")
    warnings: list[str] = []
    limits = []
    limits_raw = row["claude_limits_json"]
    if limits_raw:
        try:
            limits = json.loads(limits_raw)
        except json.JSONDecodeError:
            warnings.append("could not parse claude_limits_json")
    return {
        "provider": "claude_code",
        "status": "ok",
        "source": str(db_path),
        "captured_at": iso(parse_time(row["captured_at"])),
        "windows": {
            "current": window(row["claude_five_hour_used"], row["claude_five_hour_reset"]),
            "weekly": window(row["claude_seven_day_used"], row["claude_seven_day_reset"]),
        },
        "model_scoped_weekly": {
            "sonnet_used_percent": pct(row["claude_seven_day_sonnet_used"]),
            "opus_used_percent": pct(row["claude_seven_day_opus_used"]),
            "fable_used_percent": pct(row["claude_seven_day_fable_used"]),
            "fable_reset_at": iso(parse_time(row["claude_seven_day_fable_reset"])),
        },
        "limits": limits,
        "warnings": warnings,
    }


def codex_from_row(row: sqlite3.Row | None, db_path: Path) -> dict[str, Any] | None:
    if row is None:
        return None
    return {
        "provider": "codex",
        "status": "ok",
        "source": str(db_path),
        "captured_at": iso(parse_time(row["captured_at"])),
        "plan_type": row["codex_plan_type"],
        "windows": {
            "current": window(row["codex_primary_used"], row["codex_primary_reset"]),
            "weekly": window(row["codex_secondary_used"], row["codex_secondary_reset"]),
        },
        "warnings": [],
    }


def codex_jsonl_candidates(limit_files: int) -> list[Path]:
    roots = [
        Path.home() / ".codex" / "sessions",
        Path.home() / ".codex" / "archived_sessions",
    ]
    files: list[Path] = []
    for root in roots:
        if root.exists():
            files.extend(Path(p) for p in glob.glob(str(root / "**" / "*.jsonl"), recursive=True))
    return sorted(files, key=lambda p: p.stat().st_mtime, reverse=True)[:limit_files]


def codex_from_jsonl(limit_files: int) -> dict[str, Any] | None:
    best: tuple[dt.datetime, dict[str, Any]] | None = None
    for path in codex_jsonl_candidates(limit_files):
        try:
            lines = path.read_text(encoding="utf-8", errors="replace").splitlines()
        except OSError:
            continue
        for line in lines:
            try:
                event = json.loads(line)
            except json.JSONDecodeError:
                continue
            payload = event.get("payload") or {}
            limits = payload.get("rate_limits")
            if not isinstance(limits, dict):
                continue
            captured = parse_time(event.get("timestamp")) or dt.datetime.fromtimestamp(path.stat().st_mtime, UTC)
            primary = limits.get("primary") or {}
            secondary = limits.get("secondary") or {}
            snapshot = {
                "provider": "codex",
                "status": "ok",
                "source": str(path),
                "captured_at": iso(captured),
                "plan_type": limits.get("plan_type"),
                "windows": {
                    "current": window(primary.get("used_percent"), primary.get("resets_at")),
                    "weekly": window(secondary.get("used_percent"), secondary.get("resets_at")),
                },
                "warnings": [],
            }
            if best is None or captured > best[0]:
                best = (captured, snapshot)
    return best[1] if best else None


def freshness_warning(provider: dict[str, Any], max_age_minutes: int) -> None:
    captured = parse_time(provider.get("captured_at"))
    if captured is None:
        return
    age = (now_utc() - captured).total_seconds() / 60
    if age > max_age_minutes:
        provider.setdefault("warnings", []).append(
            f"snapshot is stale: {round(age, 1)} minutes old"
        )


def routing_hint(providers: dict[str, dict[str, Any]]) -> dict[str, Any]:
    codex = providers.get("codex", {})
    claude = providers.get("claude_code", {})
    notes: list[str] = []

    def rem(provider: dict[str, Any], name: str) -> float | None:
        return (
            provider.get("windows", {})
            .get(name, {})
            .get("remaining_percent")
        )

    codex_current = rem(codex, "current")
    claude_current = rem(claude, "current")
    codex_weekly = rem(codex, "weekly")
    claude_weekly = rem(claude, "weekly")

    preferred = "unknown"
    if codex_current is not None and claude_current is not None:
        if abs(codex_current - claude_current) >= 10:
            preferred = "codex" if codex_current > claude_current else "claude_code"
            notes.append("current-window remaining capacity differs by at least 10 percentage points")
        elif codex_weekly is not None and claude_weekly is not None:
            if abs(codex_weekly - claude_weekly) >= 10:
                preferred = "codex" if codex_weekly > claude_weekly else "claude_code"
                notes.append("current windows are close; weekly remaining capacity is the tiebreaker")
            else:
                preferred = "tie"
                notes.append("quota is close; choose by task fit and model capability")
    return {
        "preferred_for_capacity": preferred,
        "notes": notes,
    }


def paseo_preferences(path: Path) -> dict[str, Any]:
    if not path.exists():
        return {
            "status": "missing",
            "path": str(path),
            "providers": DEFAULT_PASEO_PROVIDERS,
            "preferences": [
                "defaulted because ~/.paseo/orchestration-preferences.json was not found"
            ],
        }
    try:
        raw = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        return {
            "status": "unreadable",
            "path": str(path),
            "providers": DEFAULT_PASEO_PROVIDERS,
            "preferences": [f"failed to read preferences: {exc}"],
        }
    providers = DEFAULT_PASEO_PROVIDERS | dict(raw.get("providers") or {})
    return {
        "status": "ok",
        "path": str(path),
        "providers": providers,
        "preferences": list(raw.get("preferences") or []),
    }


def provider_from_paseo(value: str) -> str:
    if value.startswith("codex/"):
        return "codex"
    if value.startswith("claude/"):
        return "claude_code"
    return "unknown"


def model_for(provider: str, role: str, tier: int) -> dict[str, str]:
    effort_by_tier = {0: "none", 1: "low", 2: "medium", 3: "high", 4: "xhigh"}
    effort = effort_by_tier.get(tier, "medium")
    if provider == "codex":
        if tier <= 1:
            model = "gpt-5.6-luna"
        elif tier == 2:
            model = "gpt-5.6-terra"
        elif role in {"planning", "audit"}:
            model = "gpt-5.6-sol"
        else:
            model = "gpt-5.5"
    elif provider == "claude_code":
        if tier <= 1:
            model = "claude-haiku-4-5"
            effort = "none"
        elif tier == 2:
            model = "claude-sonnet-5"
        elif role in {"ui", "audit"} or tier >= 4:
            model = "claude-opus-4-8"
        else:
            model = "claude-sonnet-5"
    else:
        model = "unknown"
    return {"model": model, "effort": effort}


def cap_remaining(provider: dict[str, Any], name: str) -> float | None:
    return provider.get("windows", {}).get(name, {}).get("remaining_percent")


def route_recommendation(
    role: str | None,
    tier: int | None,
    providers: dict[str, dict[str, Any]],
    preferences: dict[str, Any],
    usage_velocity: dict[str, Any],
) -> dict[str, Any] | None:
    if role is None and tier is None:
        return None
    role = role or "impl"
    tier = 2 if tier is None else tier
    preferred_value = preferences["providers"].get(role, DEFAULT_PASEO_PROVIDERS[role])
    preferred_provider = provider_from_paseo(preferred_value)
    capacity_hint = routing_hint(providers).get("preferred_for_capacity")
    candidates = ["codex", "claude_code"]

    def score(candidate: str) -> tuple[float, list[str]]:
        notes: list[str] = []
        provider = providers.get(candidate, {})
        if provider.get("status") != "ok":
            return -100.0, [f"{candidate} unavailable"]
        current = cap_remaining(provider, "current")
        weekly = cap_remaining(provider, "weekly")
        score_value = 0.0
        if current is not None:
            score_value += current * 0.45
            if current < 20:
                score_value -= 30
                notes.append("low current-window remaining capacity")
        if weekly is not None:
            score_value += weekly * 0.35
            if weekly < 25:
                score_value -= 25
                notes.append("low weekly remaining capacity")
        if candidate == preferred_provider:
            score_value += 18
            notes.append("matches role preference")
        if capacity_hint == candidate:
            score_value += 10
            notes.append("matches capacity tiebreaker")

        source = "codex" if candidate == "codex" else "claude"
        velocity = usage_velocity.get(source, {})
        avg_tokens = float(velocity.get("avg_tokens_per_day") or 0.0)
        today_tokens = float(velocity.get("today_tokens") or 0.0)
        if avg_tokens > 0 and today_tokens > avg_tokens * 1.5:
            score_value -= 8
            notes.append("today token burn is above recent average")
        if candidate == "claude_code" and role == "ui" and tier >= 2:
            score_value += 12
            notes.append("Claude favored for human-skill UI/copy/design work")
        if candidate == "codex" and role in {"impl", "research", "planning"}:
            score_value += 8
            notes.append("Codex favored for mechanical coding/research/planning work")
        return score_value, notes

    scored = {candidate: score(candidate) for candidate in candidates}
    chosen = max(scored.items(), key=lambda item: item[1][0])[0]
    model = model_for(chosen, role, tier)
    return {
        "role": role,
        "tier": tier,
        "preferred_from_paseo": preferred_value,
        "preferences_status": preferences.get("status"),
        "recommended_provider": chosen,
        "recommended_paseo_provider": f"{'codex' if chosen == 'codex' else 'claude'}/{model['model']}",
        "recommended_model": model["model"],
        "recommended_effort": model["effort"],
        "scores": {
            candidate: {"score": round(values[0], 2), "notes": values[1]}
            for candidate, values in scored.items()
        },
        "notes": scored[chosen][1],
    }


def collect(args: argparse.Namespace) -> dict[str, Any]:
    db = usage_db_path()
    claude_row, codex_row = latest_usage_rows(db)
    claude = claude_from_row(claude_row, db)
    codex_db = codex_from_row(codex_row, db)
    codex_jsonl = codex_from_jsonl(args.codex_jsonl_files)

    codex = codex_db or codex_jsonl
    if codex_db and codex_jsonl:
        db_time = parse_time(codex_db.get("captured_at")) or dt.datetime.min.replace(tzinfo=UTC)
        jsonl_time = parse_time(codex_jsonl.get("captured_at")) or dt.datetime.min.replace(tzinfo=UTC)
        codex = codex_jsonl if jsonl_time > db_time else codex_db
    if codex is None:
        codex = provider_unavailable("codex", "no Codex usage snapshot found")

    providers = {"codex": codex, "claude_code": claude}
    for provider in providers.values():
        freshness_warning(provider, args.max_age_minutes)
    usage_velocity = recent_usage_velocity(db)
    preferences = paseo_preferences(Path(args.paseo_preferences).expanduser())

    data = {
        "generated_at": iso(now_utc()),
        "max_age_minutes": args.max_age_minutes,
        "providers": providers,
        "usage_velocity": usage_velocity,
        "paseo_preferences": preferences,
        "routing_hint": routing_hint(providers),
    }
    recommendation = route_recommendation(
        args.role, args.tier, providers, preferences, usage_velocity
    )
    if recommendation:
        data["route_recommendation"] = recommendation
    return data


def table(data: dict[str, Any]) -> str:
    rows = [
        "| Provider | Current used | Current remaining | Current reset | Weekly used | Weekly remaining | Weekly reset | Source |",
        "|---|---:|---:|---|---:|---:|---|---|",
    ]
    for key, label in (("codex", "Codex"), ("claude_code", "Claude Code")):
        provider = data["providers"][key]
        windows = provider.get("windows", {})
        current = windows.get("current", {})
        weekly = windows.get("weekly", {})
        source = provider.get("source") or provider.get("status")
        rows.append(
            "| {label} | {cu} | {cr} | {crt} | {wu} | {wr} | {wrt} | {source} |".format(
                label=label,
                cu=fmt_pct(current.get("used_percent")),
                cr=fmt_pct(current.get("remaining_percent")),
                crt=current.get("reset_at") or "-",
                wu=fmt_pct(weekly.get("used_percent")),
                wr=fmt_pct(weekly.get("remaining_percent")),
                wrt=weekly.get("reset_at") or "-",
                source=source,
            )
        )
    hint = data.get("routing_hint", {})
    rows.append("")
    rows.append(f"Preferred for capacity: {hint.get('preferred_for_capacity', 'unknown')}")
    recommendation = data.get("route_recommendation")
    if recommendation:
        rows.append(
            "Recommended route: {provider} / {model} / {effort} "
            "(role={role}, tier={tier})".format(
                provider=recommendation["recommended_provider"],
                model=recommendation["recommended_model"],
                effort=recommendation["recommended_effort"],
                role=recommendation["role"],
                tier=recommendation["tier"],
            )
        )
        rows.append(
            "Paseo preference: {pref} ({status})".format(
                pref=recommendation["preferred_from_paseo"],
                status=recommendation["preferences_status"],
            )
        )
    notes = hint.get("notes") or []
    if recommendation:
        notes = notes + recommendation.get("notes", [])
    if notes:
        rows.append("Notes: " + "; ".join(notes))
    warnings = []
    for provider in data["providers"].values():
        for warning in provider.get("warnings", []):
            warnings.append(f"{provider['provider']}: {warning}")
    if warnings:
        rows.append("Warnings: " + "; ".join(warnings))
    return "\n".join(rows)


def fmt_pct(value: Any) -> str:
    if value is None:
        return "-"
    return f"{value:g}%"


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--format", choices=("json", "table"), default="json")
    parser.add_argument("--max-age-minutes", type=int, default=120)
    parser.add_argument("--role", choices=ROLES, help="task role for route recommendation")
    parser.add_argument("--tier", type=int, choices=range(0, 5), help="budget tier from model-routing-policy")
    parser.add_argument(
        "--paseo-preferences",
        default="~/.paseo/orchestration-preferences.json",
        help="Paseo role-to-provider preference file",
    )
    parser.add_argument(
        "--codex-jsonl-files",
        type=int,
        default=200,
        help="maximum recent Codex JSONL files to scan as fallback",
    )
    args = parser.parse_args()

    data = collect(args)
    if args.format == "json":
        print(json.dumps(data, ensure_ascii=False, indent=2, sort_keys=True))
    else:
        print(table(data))
    return 0


if __name__ == "__main__":
    sys.exit(main())
