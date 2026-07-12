# .agents/ — AGENTS

This directory contains generated Codex skill adapters.

## Allowed

- Regenerate `skills/` with `python scripts/sync-codex-adapters.py`.
- Update this navigation if the adapter layout changes.

## Forbidden

- Do not hand-edit `skills/*/SKILL.md`; edit `.claude/skills/` or `.claude/commands/` and regenerate.
- Do not install project skills into user-global locations to make this template work.

## Required

- After regeneration, run `python scripts/sync-codex-adapters.py --check`.
- For structural changes, update `.agents/ANATOMY.md`, root `ANATOMY.md`, and the validator in the same change.
