from pathlib import Path
from typing import Optional

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict

# Absolute path to backend/.env — works regardless of the working directory
# uvicorn is launched from (e.g. project root or backend/).
_ENV_FILE = Path(__file__).parent / ".env"


class Settings(BaseSettings):
    """Application configuration loaded from backend/.env.

    Resolution order (highest to lowest priority):
      1. Real environment variables set in the shell
      2. backend/.env file
    """

    model_config = SettingsConfigDict(
        env_file=str(_ENV_FILE),
        env_file_encoding="utf-8",
        # Silently ignore variables in .env that are not declared here
        extra="ignore",
    )

    # ── LLM ───────────────────────────────────────────────────────────────────
    GEMINI_API_KEY: Optional[str] = Field(default=None, description="Google Gemini API key (primary)")
    OPENAI_API_KEY: Optional[str] = Field(default=None, description="OpenAI API key (fallback)")
    MODEL_NAME: str = Field(default="gpt-4o-mini", description="OpenAI model name")
    GEMINI_MODEL_NAME: str = Field(default="gemini-2.5-flash", description="Google Gemini model name")

    # ── Tools ─────────────────────────────────────────────────────────────────
    TAVILY_API_KEY: str = Field(..., description="Tavily search API key")
    CLEARBIT_API_KEY: Optional[str] = Field(default=None, description="Clearbit API key")
    APOLLO_API_KEY: Optional[str] = Field(default=None, description="Apollo API key")

    # ── Storage ─────────────────────────────────────────────────────────────
    DATABASE_URL: Optional[str] = Field(
        default="sqlite:///data/fello.db",
        description="SQLite database path. Set to empty string or 'none' to use in-memory stores.",
    )

    # ── Server ────────────────────────────────────────────────────────────────
    HOST: str = Field(default="0.0.0.0", description="Server host")
    PORT: int = Field(default=8000, description="Server port")
    CORS_ORIGINS: list[str] = Field(
        default=["http://localhost:3000"], description="Allowed CORS origins"
    )

    # ── Tuning ────────────────────────────────────────────────────────────────
    TOOL_TIMEOUT_SECONDS: int = Field(default=8, description="Per-tool call hard timeout")
    TOOL_MAX_RETRIES: int = Field(default=3, description="Max retries per tool call")
    CACHE_TTL_SECONDS: int = Field(default=300, description="Tool result cache TTL")


# Module-level singleton — import this everywhere instead of instantiating Settings directly.
settings = Settings()
