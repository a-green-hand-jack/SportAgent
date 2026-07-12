# Agent-R1 adoption replay report

Date: 2026-07-09

## Case

- Source repo: `https://github.com/AgentR1/Agent-R1`
- Replay clone: `/tmp/agent-r1-adoption-replay/Agent-R1`
- Source commit tested: `85e0099` (shallow clone)
- Template branch tested: `worktree-adopt-existing-repo`
- Template feature commit: `93fabae`
- Persisted case branch: `worktree-case+agent-r1-adoption-replay`
- Persisted case commit: `5c8850f`
- Feature under test: `scripts/adopt-existing-repo.py` + `scripts/check-adoption-integrity.py`

Agent-R1 is an agent-RL / ML-research codebase with Python package code, recipes,
examples, MkDocs documentation, images, and GitHub workflow config. It is a good
first non-template replay because it is close to the template's intended ML
research domain while still having a different root layout.

## Commands

```bash
rm -rf /tmp/agent-r1-adoption-replay
mkdir -p /tmp/agent-r1-adoption-replay
git clone --depth 1 https://github.com/AgentR1/Agent-R1.git \
  /tmp/agent-r1-adoption-replay/Agent-R1
git -C /tmp/agent-r1-adoption-replay/Agent-R1 rev-parse --short HEAD

python scripts/adopt-existing-repo.py /tmp/agent-r1-adoption-replay/Agent-R1 \
  --phase all \
  --policy conservative \
  --project-name agent-r1

python scripts/check-adoption-integrity.py /tmp/agent-r1-adoption-replay/Agent-R1
python /tmp/agent-r1-adoption-replay/Agent-R1/scripts/validate-governance.py --strict
```

## Results

`adopt-existing-repo.py --phase all` completed:

| Phase | Result |
| --- | --- |
| discover | `root_entries=12`, `conflicts=3` |
| baseline | `tracked_files=178` |
| scaffold | `copied=216`, `same=0`, `skipped=0` |
| normalize | `moved=9`, `blockers=0` |
| prove | `integrity=ok`, `governance_rc=0` |

Integrity checker:

```text
[check-adoption-integrity] OK -- present 178/178
```

Target template governance:

```text
[validate-governance] OK — 0 error(s), 0 warning(s)
```

Generated target report:

```text
lab/docs/audits/template-adoption-report.md
```

The migrated case content is also preserved as a template repo branch:

```text
branch: worktree-case+agent-r1-adoption-replay
worktree: .claude/worktrees/case+agent-r1-adoption-replay
commit: 5c8850f
```

Key target report facts:

- `baseline_files_present`: `178/178`
- `moved_root_entries`: `9`
- `normalize_blockers`: `0`
- `remaining_root_pollution`: `0`
- `original_test_returncode`: `None`

No native test command was detected. Agent-R1's root `pyproject.toml` has ruff/mypy
configuration, but no obvious `tests/`, `pytest.ini`, or `Makefile test` entry.

## Normalized Layout

The original Agent-R1 root content was moved under:

```text
lab/code/imported/agent-r1/
```

Moved root entries:

- `.pre-commit-config.yaml`
- `LICENSE`
- `agent_r1`
- `docs`
- `examples`
- `image`
- `mkdocs.yml`
- `pyproject.toml`
- `recipes`

Conflicting root files were preserved before template files were copied:

- `human/imported/adoption-conflicts/.gitignore`
- `human/imported/adoption-conflicts/README.md`

Existing `.github/workflows/docs.yml` remained alongside template governance files:

- `.github/workflows/docs.yml`
- `.github/workflows/governance.yml`

## Findings

### A1: The migration path works for a real agent-RL repo

Agent-R1 successfully adopted the complete template control plane and passed
template governance after root normalization. This validates that the template is
not limited to empty new projects and can carry an ML/agent-RL codebase as
imported research code.

### A2: Hash integrity is the right proof surface

Before staging, `git status` naturally shows many original paths as deleted and
new imported paths as untracked. After staging, Git's rename heuristics may still
pair empty files in surprising ways. The reliable invariant is therefore the
baseline hash check: all 178 tracked files remained present by content hash.

The adoption report was improved during this replay to explicitly show moved
root entries, blocker count, remaining root pollution, baseline presence, and a
note explaining move-based Git status.

### A3: v1 is structurally complete but semantically coarse

The template shape is complete (`remaining_root_pollution=0`), but v1 keeps the
old repo as one imported unit. For Agent-R1 this means docs, images, examples,
and recipes all live under `lab/code/imported/agent-r1/`. That is safe and
reversible, but a future v2 may want optional semantic classification:

- docs -> `lab/docs/reference/` or `human/imported/`
- images -> artifact or documentation assets
- examples/recipes -> `lab/code/experiments/` or repo-specific recipe space
- package code -> `lab/code/src/`

### A4: Native behavior proof depends on target repo test surface

Agent-R1 did not expose a lightweight native test command. The replay therefore
proves byte preservation and template governance, but not runtime correctness of
Agent-R1's training or evaluation code. This is acceptable for v1 because the
tool should not invent expensive ML tests, but the report must show
`original_test_returncode=None`.

## Follow-ups

- Add a `--stage-check` or report section that summarizes how Git will look after
  `git add -A`, while still explaining that rename detection is heuristic.
- Consider optional semantic normalize policies after conservative v1:
  `--normalize-policy imported-unit` (current), `python-package`, `docs-aware`.
- Add a fixture with existing `.github/workflows/*` to lock in merge behavior for
  workflow directories.
- Add a fixture with no native test command to assert report clarity around
  `original_test_returncode=None`.
