"""LLM provider adapters — Anthropic Claude and OpenAI."""

from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Optional

from trustpipe.core.config import TrustPipeConfig


class LLMProvider(ABC):
    """Abstract base for LLM providers."""

    @abstractmethod
    def generate(self, prompt: str, *, system: str = "", max_tokens: int = 1024) -> str:
        """Generate text from a prompt."""
        ...


class AnthropicProvider(LLMProvider):
    """Anthropic Claude provider."""

    def __init__(self, api_key: Optional[str] = None, model: str = "claude-sonnet-4-20250514") -> None:
        try:
            import anthropic
        except ImportError:
            raise ImportError("Install anthropic: pip install trustpipe[llm]")

        import os
        key = api_key or os.environ.get("ANTHROPIC_API_KEY") or os.environ.get("TRUSTPIPE_LLM_KEY")
        if not key:
            raise ValueError("Anthropic API key required. Set ANTHROPIC_API_KEY or TRUSTPIPE_LLM_KEY")
        self._client = anthropic.Anthropic(api_key=key)
        self._model = model

    def generate(self, prompt: str, *, system: str = "", max_tokens: int = 1024) -> str:
        message = self._client.messages.create(
            model=self._model,
            max_tokens=max_tokens,
            system=system or "You are a data governance expert writing compliance documentation.",
            messages=[{"role": "user", "content": prompt}],
        )
        return message.content[0].text


class OpenAIProvider(LLMProvider):
    """OpenAI provider."""

    def __init__(self, api_key: Optional[str] = None, model: str = "gpt-4o") -> None:
        try:
            import openai
        except ImportError:
            raise ImportError("Install openai: pip install trustpipe[llm]")

        import os
        key = api_key or os.environ.get("OPENAI_API_KEY") or os.environ.get("TRUSTPIPE_LLM_KEY")
        if not key:
            raise ValueError("OpenAI API key required. Set OPENAI_API_KEY or TRUSTPIPE_LLM_KEY")
        self._client = openai.OpenAI(api_key=key)
        self._model = model

    def generate(self, prompt: str, *, system: str = "", max_tokens: int = 1024) -> str:
        response = self._client.chat.completions.create(
            model=self._model,
            max_tokens=max_tokens,
            messages=[
                {"role": "system", "content": system or "You are a data governance expert writing compliance documentation."},
                {"role": "user", "content": prompt},
            ],
        )
        return response.choices[0].message.content or ""


def get_provider(config: Optional[TrustPipeConfig] = None) -> Optional[LLMProvider]:
    """Get configured LLM provider, or None if not configured."""
    cfg = config or TrustPipeConfig()
    if not cfg.llm_provider:
        return None

    if cfg.llm_provider == "anthropic":
        return AnthropicProvider(api_key=cfg.llm_api_key, model=cfg.llm_model or "claude-sonnet-4-20250514")
    elif cfg.llm_provider == "openai":
        return OpenAIProvider(api_key=cfg.llm_api_key, model=cfg.llm_model or "gpt-4o")
    else:
        raise ValueError(f"Unknown LLM provider: {cfg.llm_provider}. Use 'anthropic' or 'openai'.")
