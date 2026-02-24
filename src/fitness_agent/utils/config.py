"""Configuration management: load .env and provide app settings."""
import os
from pathlib import Path
from dotenv import load_dotenv

load_dotenv()

# Project root
PROJECT_ROOT = Path(__file__).parent.parent.parent.parent
DATA_DIR = Path(os.getenv("DATA_DIR", str(PROJECT_ROOT / "data")))
OUTPUTS_DIR = Path(os.getenv("OUTPUTS_DIR", str(PROJECT_ROOT / "outputs")))

# LLM settings
LLM_PROVIDER: str = os.getenv("LLM_PROVIDER", "anthropic")
LLM_MODEL: str = os.getenv("LLM_MODEL", "claude-opus-4-6")

ANTHROPIC_API_KEY: str | None = os.getenv("ANTHROPIC_API_KEY")
OPENAI_API_KEY: str | None = os.getenv("OPENAI_API_KEY")
