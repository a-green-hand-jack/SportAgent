---
description: Analyse code changes since the last docs update and refresh the docs/src/ documentation files.
---

# Update Docs Workflow (SportAgent)

This is the project-specific version of the `/update-docs` workflow. It builds on the global workflow with SportAgent-specific doc locations and change-to-doc mappings.

The **global version** at `~/.agent/workflows/update-docs.md` handles the general flow. This file adds project-specific context.

---

## Step 1 — Orient

// turbo

```bash
ROOT=$(git -C /Users/jieke/Projects/SportAgent rev-parse --show-toplevel)
git -C $ROOT log --oneline -5
git -C $ROOT branch --show-current
```

**Documentation lives at**: `$ROOT/docs/src/`

| File                      | Covers                                                            |
| ------------------------- | ----------------------------------------------------------------- |
| `agent-implementation.md` | `PlannerAgent`, `CookingAgent` internals, retry loops, LLM client |
| `knowledge-storage.md`    | KB JSON files, `KnowledgeBase` query API, profile persistence     |
| `information-flow.md`     | End-to-end flow: CLI → Onboarding → Agents → output               |
| `dependencies.md`         | Module dependency diagram and table                               |

---

## Step 2 — Find the baseline commit

// turbo

```bash
git -C /Users/jieke/Projects/SportAgent log --oneline --all -- docs/src/ | head -5
```

Note the first hash — call it `<baseline>`. If no doc commit exists, use the initial commit.

---

## Step 3 — Diff source code since the baseline

// turbo

```bash
git -C /Users/jieke/Projects/SportAgent diff <baseline> HEAD --stat -- src/ tests/ scripts/ data/
```

For the full diff:

```bash
git -C /Users/jieke/Projects/SportAgent diff <baseline> HEAD -- src/ tests/ scripts/ data/
```

---

## Step 4 — Map changes to affected docs

Use this project-specific mapping:

| Changed source path                          | Affected doc(s)                                                         |
| -------------------------------------------- | ----------------------------------------------------------------------- |
| `src/fitness_agent/planner/agent.py`         | `agent-implementation.md` (PlannerAgent section), `information-flow.md` |
| `src/fitness_agent/planner/models.py`        | `information-flow.md` (WeeklyPlan structure)                            |
| `src/fitness_agent/planner/prompt.py`        | `agent-implementation.md` (Prompt section)                              |
| `src/fitness_agent/cooking/agent.py`         | `agent-implementation.md` (CookingAgent section), `information-flow.md` |
| `src/fitness_agent/cooking/models.py`        | `information-flow.md`                                                   |
| `src/fitness_agent/cooking/prompt.py`        | `agent-implementation.md` (Prompt section)                              |
| `src/fitness_agent/knowledge_base/loader.py` | `knowledge-storage.md` (KnowledgeBase API)                              |
| `src/fitness_agent/knowledge_base/models.py` | `knowledge-storage.md` (Data models section)                            |
| `src/fitness_agent/user/onboarding.py`       | `information-flow.md` (Onboarding section)                              |
| `src/fitness_agent/user/models.py`           | `knowledge-storage.md` (UserProfile), `information-flow.md`             |
| `src/fitness_agent/user/calculator.py`       | `information-flow.md` (enrich_profile step)                             |
| `src/fitness_agent/utils/llm_client.py`      | `agent-implementation.md` (LLM client section)                          |
| `src/fitness_agent/utils/config.py`          | `agent-implementation.md` (Provider table)                              |
| `src/fitness_agent/utils/text_parser.py`     | `information-flow.md` (injury parsing step)                             |
| `src/fitness_agent/cli.py`                   | `information-flow.md` (CLI section), `dependencies.md`                  |
| `data/raw/*.json` (new or changed file)      | `knowledge-storage.md` (Knowledge files table)                          |
| New module under `src/fitness_agent/`        | `dependencies.md` (diagram + table) + relevant content doc              |
| Module deleted                               | `dependencies.md` + remove from relevant content doc                    |

---

## Step 5 — Make surgical edits

Update only the sections that are out of date. Maintain the existing style: Chinese headings where used, ASCII flow diagrams, code blocks for method signatures, markdown tables for structured data.

---

## Step 6 — Summarise and optionally commit

Display which files and sections were changed, then ask: **"文档已更新。是否要提交这些改动？"**

If yes:
// turbo

```bash
git -C /Users/jieke/Projects/SportAgent add docs/src/ && \
git -C /Users/jieke/Projects/SportAgent commit -m "docs: update docs/src/ to reflect changes since <baseline>"
```
