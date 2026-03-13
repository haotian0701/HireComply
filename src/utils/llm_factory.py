"""LLM provider factory.

Supports switching between OpenAI, Anthropic, and other providers
via configuration. This makes it easy to benchmark different models
on the same recruitment pipeline — relevant for thesis work too.
"""

from __future__ import annotations

from functools import lru_cache
from typing import Literal

from langchain_core.language_models import BaseChatModel

from configs.settings import get_settings

ModelProvider = Literal["openai", "anthropic", "gemini"]


@lru_cache(maxsize=4)
def get_llm(
    provider: ModelProvider | None = None,
    model: str | None = None,
    temperature: float = 0.0,
) -> BaseChatModel:
    """Create an LLM instance.

    Args:
        provider: "openai", "anthropic", or "gemini". Defaults to config.
        model: Model name override. Defaults to config.
        temperature: Sampling temperature. 0.0 for deterministic outputs
                     (important for reproducible audit trails).
    """
    settings = get_settings()
    provider = provider or settings.llm_provider
    model = model or settings.llm_model

    if provider == "openai":
        from langchain_openai import ChatOpenAI

        return ChatOpenAI(
            model=model,
            temperature=temperature,
            api_key=settings.openai_api_key,
        )
    elif provider == "anthropic":
        from langchain_anthropic import ChatAnthropic

        return ChatAnthropic(
            model=model,
            temperature=temperature,
            api_key=settings.anthropic_api_key,
        )
    elif provider == "gemini":
        from langchain_google_genai import ChatGoogleGenerativeAI

        if not settings.google_api_key:
            raise ValueError(
                "Missing GOOGLE_API_KEY for Gemini provider. "
                "Set GOOGLE_API_KEY in your environment or .env file."
            )

        return ChatGoogleGenerativeAI(
            model=model,
            temperature=temperature,
            google_api_key=settings.google_api_key,
        )
    else:
        raise ValueError(f"Unsupported provider: {provider}")
