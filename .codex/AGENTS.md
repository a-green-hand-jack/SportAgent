# .codex/ — AGENTS

This directory is a Codex adapter plane, not the canonical doctrine plane.

## Allowed

- Edit `config.toml` and `rules/default.rules` when Codex runtime behavior changes.
- Regenerate `agents/*.toml` with `python scripts/sync-codex-adapters.py`.

## Required

- Do not hand-edit generated `agents/*.toml`; edit `.claude/agents/*.md` and regenerate.
- Keep provider/auth/telemetry secrets out of project `.codex/config.toml`; those belong in user or admin Codex config.
- If hooks, rules, or permissions change, update `.agent/action-boundary.md`, `lab/infra/permissions/`, and the relevant ANATOMY files in the same change.
- Verify with `python scripts/sync-codex-adapters.py --check` and `python scripts/validate-governance.py`.

## Forbidden

- Do not use `.codex/` to bypass `.agent/human-gates.md`.
- Do not weaken protected-path or push-to-main safeguards without explicit human approval and a recorded rationale.
