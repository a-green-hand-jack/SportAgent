# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

**Fitness Agent** is an AI-powered personalized fitness planning system. Users answer a Q&A, and the system generates a customized weekly training plan + daily nutrition scheme using LLM (Claude, GPT, DeepSeek, Gemini, or Qwen).

**Core Architecture Principle**: Knowledge base handles deterministic logic (exercise filtering, safety rules, calorie calculations); LLM handles creative composition (plan arrangement, personalization, natural language).

## Development Environment

### Setup
```bash
# Clone and install (auto-creates virtual env)
git clone <repo-url> SportAgent
cd SportAgent
uv sync
```

### Configuration
```bash
# Copy and configure API keys
cp .env.example .env
# Edit .env to fill in at least one LLM provider's API key
```

### Python & uv Requirements
- **Python 3.12+** required
- Always use `uv run` to execute Python scripts (not bare `python`)
- Always use `uv add`/`uv remove` for dependencies (not `pip install`)
- Dependencies are defined in `pyproject.toml` with optional dev group

## Common Commands

### Running the Application
```bash
# Generate a training plan (full interactive Q&A)
uv run fitness-agent plan

# Generate a plan with specific LLM provider
uv run fitness-agent plan --provider deepseek --model deepseek-chat
uv run fitness-agent plan --provider openai --model gpt-4o
uv run fitness-agent plan --provider gemini --model gemini-2.0-flash

# Load existing user profile (skip Q&A)
uv run fitness-agent plan --profile data/processed/profile.json

# Generate and save to custom location
uv run fitness-agent plan --output outputs/my_plan.json

# Show version
uv run fitness-agent version
```

### Testing
```bash
# Run all tests with coverage
uv run pytest

# Run specific test file
uv run pytest tests/planner/test_agent.py

# Run single test
uv run pytest tests/planner/test_agent.py::test_plan_generation

# Run with verbose output
uv run pytest -v

# Run only tests matching a pattern
uv run pytest -k "test_contraindications"
```

### Linting & Code Quality
```bash
# Format code
uv run black src tests

# Lint with ruff
uv run ruff check src tests

# Type check with mypy
uv run mypy src

# All checks together
uv run black --check src tests && uv run ruff check src tests && uv run mypy src
```

## Project Structure

```
src/fitness_agent/
├── knowledge_base/     # Deterministic filtering & data
│   ├── loader.py       # Loads JSON KB files (exercises, nutrition, rules, etc.)
│   ├── models.py       # Pydantic models for KB data structures
│   └── __init__.py
├── planner/            # AI planning agent
│   ├── agent.py        # PlannerAgent: orchestrates KB + LLM to generate plans
│   ├── models.py       # WeeklyPlan, TrainingDay, Exercise output models
│   ├── prompt.py       # System prompt & user message builder
│   └── __init__.py
├── user/               # User onboarding & profile
│   ├── onboarding.py   # run_onboarding(): interactive Q&A flow
│   ├── models.py       # UserProfile: stores user data (name, goals, injuries, etc.)
│   ├── calculator.py   # BMR/TDEE calculation (deterministic)
│   └── __init__.py
├── utils/              # Shared utilities
│   ├── llm_client.py   # Unified LLM client (Anthropic, OpenAI, DeepSeek, Gemini, Qwen)
│   ├── config.py       # Environment variable loading (LLM_PROVIDER, API keys, etc.)
│   ├── logging.py      # Logging setup
│   ├── text_parser.py  # JSON extraction from LLM responses
│   └── __init__.py
└── cli.py             # Typer CLI entry point

data/
├── raw/               # Knowledge base JSON files (tracked in git)
│   ├── exercises.json
│   ├── nutrition.json
│   ├── rules.json
│   ├── anatomy.json
│   ├── nutrition_principles.json
│   ├── warmup_templates.json
│   └── injury_profiles.json
└── processed/         # Generated outputs (not tracked in git)
    ├── profile.json   # Auto-saved user profiles
    └── plan.json      # Generated training plans

tests/
├── conftest.py        # Pytest fixtures & test dir setup
├── test_smoke.py      # Basic import tests
├── knowledge_base/    # KB loader & models tests
├── planner/           # Agent & prompt tests
├── user/              # Onboarding & calculator tests
├── utils/             # LLM client & text parser tests
├── data/              # Test fixture JSON files (tracked in git)
└── outputs/           # Temporary test outputs (cleaned between tests)
```

## Key Architecture Patterns

### 1. Separation of Concerns: KB vs LLM
- **Knowledge Base** (deterministic): `KnowledgeBase` class filters exercises by contraindications + equipment, provides nutrition rules, validates training volume
- **LLM** (creative): `PlannerAgent` builds a prompt with the KB data, sends it to the LLM, and parses the response

### 2. Unified LLM Client
- `BaseLLMClient` abstract class with concrete implementations for each provider
- Single `build_client()` / `build_client_from_config()` interface hides provider differences
- All providers return consistent `LLMResponse` with `.content`, `.provider`, `.model`, token counts

### 3. Data Models with Pydantic
- All structured data (User, Exercise, WeeklyPlan, etc.) use `Pydantic BaseModel`
- Enables validation, serialization (JSON), and type hints
- Output models in `planner/models.py` match LLM JSON schema

### 4. Absolute Imports
- Always use `from fitness_agent.X import Y` (not relative imports)
- Package is installed in editable mode (`uv sync` handles this)

### 5. Stateless Planning
- Each `generate_plan()` call is independent (no session history)
- LLM retry logic is built in (validate volume, retry if below target)

## Testing Strategies

### Test Data Isolation
- Test fixtures go in `tests/data/` (e.g., `tests/data/sample_profile.json`)
- Test outputs go in `tests/outputs/` (auto-cleaned by `conftest.py`)
- **Never** use main project directories (`data/processed/`, `outputs/`) for tests

### Pytest Fixtures (conftest.py)
- `test_data_dir`: Returns `Path` to `tests/data/`
- `test_outputs_dir`: Returns `Path` to `tests/outputs/`
- `clean_test_outputs`: Auto-runs before each test, cleans temp outputs

### Coverage & CI
- Pytest config in `pyproject.toml` runs with `--cov=src/fitness_agent --cov-report=term-missing`
- All source modules should have corresponding tests in `tests/` mirror (e.g., `src/fitness_agent/user/calculator.py` → `tests/user/test_calculator.py`)

## Module Responsibilities

### knowledge_base/loader.py
- Loads all KB JSON files on init
- Provides query methods: `get_safe_exercises()`, `get_foods_for_goal()`, etc.
- Filters exercises by contraindications (injuries) and equipment availability

### planner/agent.py
- `PlannerAgent.generate_plan(profile)`: Main public method
- Step 1: Parse injuries → contraindication tags
- Step 2: Get safe exercise pool from KB
- Step 3: Build LLM prompt with filtered exercises + user context
- Step 4: Call LLM, parse JSON response into `WeeklyPlan`
- Step 5: Validate weekly training volume; retry if below target (up to `max_retries`)

### user/onboarding.py
- `run_onboarding()`: Interactive Q&A loop for collecting user data
- Returns fully enriched `UserProfile` with BMR/TDEE calculated
- `load_profile()` / `save_profile()` helpers for JSON persistence

### user/calculator.py
- `calculate_bmr()`: Mifflin-St Jeor formula
- `calculate_tdee()`: BMR × activity multiplier
- `calculate_calorie_target()`: TDEE ± adjustment for goal

### utils/llm_client.py
- `BaseLLMClient`: Abstract base class
- Concrete implementations: `AnthropicClient`, `OpenAIClient`, `DeepSeekClient`, `GeminiClient`, `QwenClient`
- `build_client(provider, model)`: Factory to instantiate the right client
- All responses return `LLMResponse(content, provider, model, input_tokens, output_tokens)`

### utils/text_parser.py
- `extract_json_from_text()`: Robust JSON extraction from LLM responses (handles markdown code blocks, etc.)

### cli.py
- Typer CLI with two commands: `plan` and `version`
- `plan`: Orchestrates onboarding → KB filtering → LLM generation → display + save (JSON + Markdown)
- Uses Rich for pretty terminal output (tables, panels, colors)

## Common Workflows

### Adding a New Exercise
1. Add JSON entry to `data/raw/exercises.json` with full structure (name, aliases, muscle groups, equipment, contraindications, etc.)
2. Test with `tests/knowledge_base/test_loader.py` to verify loading and filtering

### Changing the LLM Prompt
1. Edit `src/fitness_agent/planner/prompt.py` (PLANNER_SYSTEM, build_user_message)
2. Update `tests/planner/test_prompt.py` if expected prompt structure changes
3. Test end-to-end with `uv run pytest tests/planner/test_agent.py`

### Adding a New LLM Provider
1. Create new client class in `utils/llm_client.py` implementing `BaseLLMClient`
2. Add environment variable and API key handling in `utils/config.py`
3. Update `build_client()` factory to instantiate the new provider
4. Add tests in `tests/utils/test_llm_client.py`
5. Document in README.md and CLI help

### Modifying Output Format
1. Change `WeeklyPlan` or related models in `planner/models.py`
2. Update the LLM system prompt in `planner/prompt.py` to match
3. Update CLI display in `cli.py` (_display_plan, _plan_to_markdown)
4. Test with `uv run pytest tests/planner/test_models.py`

## Important Details

### Injury Profile & Contraindication Handling
- User provides free-text injury description → LLM parses into `ContraindicationTag` enum
- `ContraindicationTag` values map to exercise contraindications
- Knowledge base has pre-defined tags on each exercise
- Agent filters: if user's tags ∩ exercise's tags ≠ ∅, exercise is excluded

### Volume Validation & Retry
- `PlannerAgent` counts sets/reps per muscle group in generated plan
- Compares against target (from `TrainingRule`)
- If below target, retries LLM up to `max_retries` times with correction message
- Logs warnings if volume compliance fails after retries

### File Output
- Plan JSON saved to `data/processed/plan.json` (or `--output` path)
- Markdown version auto-generated: `plan.md`
- Profile JSON auto-saved to `data/processed/profile.json` after onboarding

### Environment Variables
```
ANTHROPIC_API_KEY      # Claude
OPENAI_API_KEY         # GPT
DEEPSEEK_API_KEY       # DeepSeek
QWEN_API_KEY           # Qwen
GOOGLE_API_KEY         # Gemini
LLM_PROVIDER           # Default: "anthropic"
LLM_MODEL              # Default: "claude-opus-4-6"
DATA_DIR               # Default: "./data"
```

## Type Annotations & Code Quality

- All public functions must have type hints (enforced by mypy: `disallow_untyped_defs = true`)
- Pydantic models used for all structured data
- Black formatting: 100 character line length
- Ruff linting: E, F, I, N, W rules
