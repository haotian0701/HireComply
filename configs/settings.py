"""Application configuration via pydantic-settings.

Reads from environment variables and .env file.
"""

from __future__ import annotations

from functools import lru_cache
from typing import Literal

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """HireComply configuration."""

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    # ── LLM ──
    llm_provider: Literal["openai", "anthropic", "gemini"] = "gemini"
    llm_model: str = "gemini-2.5-flash"
    openai_api_key: str = ""
    anthropic_api_key: str = ""
    google_api_key: str = ""

    # ── Database ──
    database_url: str = "postgresql://localhost:5432/hirecomply"

    # ── LangSmith (optional) ──
    langchain_tracing_v2: bool = False
    langchain_api_key: str = ""
    langchain_project: str = "hire-comply"

    # ── App ──
    log_level: str = "INFO"
    bias_risk_threshold: float = 0.6  # Score above this triggers bias alert
    min_screening_score: float = 0.5  # Minimum score to pass screening


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    """Cached settings singleton."""
    return Settings()
