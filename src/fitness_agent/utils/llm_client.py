"""
Unified LLM client: wraps Anthropic, OpenAI-compatible (OpenAI, DeepSeek, Qwen),
and Google Gemini behind a single interface.

Usage:
    from fitness_agent.utils.llm_client import LLMClient, Message

    client = LLMClient.from_config()   # reads LLM_PROVIDER / LLM_MODEL from .env
    response = client.chat(
        system="You are a fitness coach.",
        messages=[Message(role="user", content="Design a push day.")]
    )
    print(response.content)
"""
from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Literal

from fitness_agent.utils.logging import get_logger

logger = get_logger(__name__)

# ---------------------------------------------------------------------------
# Data types
# ---------------------------------------------------------------------------

Role = Literal["user", "assistant"]


@dataclass
class Message:
    role: Role
    content: str


@dataclass
class LLMResponse:
    content: str
    provider: str
    model: str
    input_tokens: int = 0
    output_tokens: int = 0

    @property
    def total_tokens(self) -> int:
        return self.input_tokens + self.output_tokens


# ---------------------------------------------------------------------------
# Provider configuration registry
# ---------------------------------------------------------------------------

# OpenAI-compatible providers: (base_url, env_key_name, default_model)
_OPENAI_COMPAT_PROVIDERS: dict[str, tuple[str, str, str]] = {
    "openai": (
        "https://api.openai.com/v1",
        "OPENAI_API_KEY",
        "gpt-4o-mini",
    ),
    "deepseek": (
        "https://api.deepseek.com/v1",
        "DEEPSEEK_API_KEY",
        "deepseek-chat",
    ),
    "qwen": (
        "https://dashscope.aliyuncs.com/compatible-mode/v1",
        "QWEN_API_KEY",
        "qwen-plus",
    ),
}

_DEFAULT_MODELS: dict[str, str] = {
    "anthropic": "claude-haiku-4-6",
    "gemini":    "gemini-2.0-flash",
    **{name: cfg[2] for name, cfg in _OPENAI_COMPAT_PROVIDERS.items()},
}


# ---------------------------------------------------------------------------
# Abstract base
# ---------------------------------------------------------------------------

class BaseLLMClient(ABC):
    def __init__(self, model: str, provider: str) -> None:
        self.model = model
        self.provider = provider

    @abstractmethod
    def chat(
        self,
        messages: list[Message],
        *,
        system: str = "",
        max_tokens: int = 4096,
        temperature: float = 0.7,
    ) -> LLMResponse:
        """Send a chat request and return the assistant response."""

    def __repr__(self) -> str:
        return f"{self.__class__.__name__}(provider={self.provider!r}, model={self.model!r})"


# ---------------------------------------------------------------------------
# Anthropic client
# ---------------------------------------------------------------------------

class AnthropicClient(BaseLLMClient):
    def __init__(self, api_key: str, model: str) -> None:
        super().__init__(model=model, provider="anthropic")
        import anthropic as _anthropic
        self._client = _anthropic.Anthropic(api_key=api_key)

    def chat(
        self,
        messages: list[Message],
        *,
        system: str = "",
        max_tokens: int = 4096,
        temperature: float = 0.7,
    ) -> LLMResponse:
        sdk_messages = [{"role": m.role, "content": m.content} for m in messages]

        kwargs: dict = dict(
            model=self.model,
            max_tokens=max_tokens,
            messages=sdk_messages,
        )
        if system:
            kwargs["system"] = system

        resp = self._client.messages.create(**kwargs)
        logger.debug(f"[anthropic] {resp.usage}")
        return LLMResponse(
            content=resp.content[0].text,
            provider=self.provider,
            model=self.model,
            input_tokens=resp.usage.input_tokens,
            output_tokens=resp.usage.output_tokens,
        )


# ---------------------------------------------------------------------------
# OpenAI-compatible client (OpenAI / DeepSeek / Qwen)
# ---------------------------------------------------------------------------

class OpenAICompatClient(BaseLLMClient):
    def __init__(self, api_key: str, model: str, base_url: str, provider: str) -> None:
        super().__init__(model=model, provider=provider)
        from openai import OpenAI
        self._client = OpenAI(api_key=api_key, base_url=base_url)

    def chat(
        self,
        messages: list[Message],
        *,
        system: str = "",
        max_tokens: int = 4096,
        temperature: float = 0.7,
    ) -> LLMResponse:
        sdk_messages = []
        if system:
            sdk_messages.append({"role": "system", "content": system})
        sdk_messages.extend({"role": m.role, "content": m.content} for m in messages)

        resp = self._client.chat.completions.create(
            model=self.model,
            messages=sdk_messages,
            max_tokens=max_tokens,
            temperature=temperature,
        )
        usage = resp.usage
        logger.debug(f"[{self.provider}] {usage}")
        return LLMResponse(
            content=resp.choices[0].message.content or "",
            provider=self.provider,
            model=self.model,
            input_tokens=usage.prompt_tokens if usage else 0,
            output_tokens=usage.completion_tokens if usage else 0,
        )


# ---------------------------------------------------------------------------
# Google Gemini client
# ---------------------------------------------------------------------------

class GeminiClient(BaseLLMClient):
    def __init__(self, api_key: str, model: str) -> None:
        super().__init__(model=model, provider="gemini")
        from google import genai
        self._client = genai.Client(api_key=api_key)

    def chat(
        self,
        messages: list[Message],
        *,
        system: str = "",
        max_tokens: int = 4096,
        temperature: float = 0.7,
    ) -> LLMResponse:
        from google.genai import types

        contents = [
            types.Content(
                role=m.role,
                parts=[types.Part(text=m.content)],
            )
            for m in messages
        ]

        config = types.GenerateContentConfig(
            max_output_tokens=max_tokens,
            temperature=temperature,
        )
        if system:
            config.system_instruction = system

        resp = self._client.models.generate_content(
            model=self.model,
            contents=contents,
            config=config,
        )
        usage = resp.usage_metadata
        logger.debug(f"[gemini] {usage}")
        return LLMResponse(
            content=resp.text or "",
            provider=self.provider,
            model=self.model,
            input_tokens=usage.prompt_token_count if usage else 0,
            output_tokens=usage.candidates_token_count if usage else 0,
        )


# ---------------------------------------------------------------------------
# Factory
# ---------------------------------------------------------------------------

def build_client(
    provider: str,
    model: str | None = None,
    api_key: str | None = None,
) -> BaseLLMClient:
    """
    Build the correct client for the given provider.

    Args:
        provider:  "anthropic" | "openai" | "deepseek" | "qwen" | "gemini"
        model:     Model name; falls back to provider default if None.
        api_key:   Override API key; falls back to env vars if None.
    """
    import os

    resolved_model = model or _DEFAULT_MODELS.get(provider, "")
    if not resolved_model:
        raise ValueError(f"Unknown provider: {provider!r}")

    if provider == "anthropic":
        key = api_key or os.getenv("ANTHROPIC_API_KEY") or ""
        _require_key(key, "ANTHROPIC_API_KEY")
        return AnthropicClient(api_key=key, model=resolved_model)

    if provider == "gemini":
        key = api_key or os.getenv("GOOGLE_API_KEY") or ""
        _require_key(key, "GOOGLE_API_KEY")
        return GeminiClient(api_key=key, model=resolved_model)

    if provider in _OPENAI_COMPAT_PROVIDERS:
        base_url, env_var, _ = _OPENAI_COMPAT_PROVIDERS[provider]
        key = api_key or os.getenv(env_var) or ""
        _require_key(key, env_var)
        return OpenAICompatClient(
            api_key=key, model=resolved_model, base_url=base_url, provider=provider
        )

    raise ValueError(
        f"Unknown provider {provider!r}. "
        f"Valid: anthropic, openai, deepseek, qwen, gemini"
    )


def build_client_from_config() -> BaseLLMClient:
    """Build a client using LLM_PROVIDER and LLM_MODEL from config / .env."""
    from fitness_agent.utils.config import LLM_MODEL, LLM_PROVIDER
    logger.info(f"Building LLM client: provider={LLM_PROVIDER!r}, model={LLM_MODEL!r}")
    return build_client(provider=LLM_PROVIDER, model=LLM_MODEL or None)


def _require_key(key: str, env_var: str) -> None:
    if not key:
        raise ValueError(
            f"API key not set. Add {env_var} to your .env file."
        )
