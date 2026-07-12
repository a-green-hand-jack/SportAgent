"""Smoke tests: verify project is importable and CLI is functional."""


def test_import_package() -> None:
    import fitness_agent
    assert fitness_agent.__version__ == "0.1.0"


def test_import_modules() -> None:
    from fitness_agent.utils.config import LLM_PROVIDER
    from fitness_agent.utils.logging import get_logger
    assert LLM_PROVIDER in ("anthropic", "openai")
    logger = get_logger("test")
    assert logger is not None
