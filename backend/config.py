import json
from pathlib import Path
from typing import Optional

from pydantic import Field, field_validator
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
        description="Database URL: postgres://..., sqlite:///path, or 'none' for in-memory.",
    )

    @field_validator("DATABASE_URL", mode="before")
    @classmethod
    def normalize_database_url(cls, v: object) -> Optional[str]:
        """Strip whitespace and normalise postgres URI scheme.

        Railway provides DATABASE_URL as postgres://... but asyncpg expects
        postgresql://... — we accept both and leave the value otherwise untouched.
        """
        if v is None:
            return None
        if isinstance(v, str):
            stripped = v.strip()
            if not stripped:
                return None
            if stripped.startswith("postgres://"):
                stripped = "postgresql://" + stripped[len("postgres://"):]
            return stripped
        return v  # type: ignore[return-value]

    # ── Server ────────────────────────────────────────────────────────────────
    HOST: str = Field(default="0.0.0.0", description="Server host")
    PORT: int = Field(default=8000, description="Server port")

    # Declared as str so pydantic-settings does NOT attempt json.loads() on it.
    # parse_cors_origins converts it to list[str] before validation completes.
    CORS_ORIGINS: str = Field(
        default="http://localhost:3000",
        description="Allowed CORS origins — comma-separated or JSON array string.",
    )

    @field_validator("CORS_ORIGINS", mode="before")
    @classmethod
    def parse_cors_origins(cls, v: object) -> str:
        """Normalise any input form to a comma-joined string.

        Accepted forms (from Railway / .env / code):
          - Plain URL:          https://foo.vercel.app
          - Comma-separated:    https://foo.vercel.app,http://localhost:3000
          - JSON array string:  ["https://foo.vercel.app"]
          - Python list:        ["https://foo.vercel.app"]  (from .env parsing)

        Returns a comma-joined string so the field type stays str and
        pydantic-settings never tries json.loads() on it.
        """
        if isinstance(v, list):
            return ",".join(str(o).strip() for o in v if str(o).strip())
        if isinstance(v, str):
            stripped = v.strip()
            if stripped.startswith("["):
                try:
                    parsed = json.loads(stripped)
                    return ",".join(str(o).strip() for o in parsed if str(o).strip())
                except json.JSONDecodeError:
                    pass
            return stripped
        return str(v) if v is not None else ""

    @property
    def cors_origins_list(self) -> list[str]:
        """Return CORS_ORIGINS as a parsed list of origin strings."""
        return [o.strip() for o in self.CORS_ORIGINS.split(",") if o.strip()]

    # ── Tuning ────────────────────────────────────────────────────────────────
    TOOL_TIMEOUT_SECONDS: int = Field(default=8, description="Per-tool call hard timeout")
    TOOL_MAX_RETRIES: int = Field(default=3, description="Max retries per tool call")
    CACHE_TTL_SECONDS: int = Field(default=300, description="Tool result cache TTL")


# Module-level singleton — import this everywhere instead of instantiating Settings directly.
settings = Settings()
