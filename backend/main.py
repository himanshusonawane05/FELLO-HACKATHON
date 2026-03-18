import logging
from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from backend.config import settings, _ENV_FILE

logging.basicConfig(level=logging.INFO, format="%(levelname)s  %(name)s  %(message)s")
logger = logging.getLogger(__name__)


def _mask(key: str) -> str:
    """Return first 8 chars + '...' for safe logging of secret keys."""
    return key[:8] + "..." if len(key) > 8 else "***"


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan: startup validation + shutdown hooks."""
    env_source = str(_ENV_FILE) if _ENV_FILE.exists() else "shell environment"
    logger.info("━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━")
    logger.info("  Fello AI Account Intelligence API  v1.0.0")
    logger.info("━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━")
    logger.info("  ENV source   : %s", env_source)
    logger.info("  GEMINI key   : %s", _mask(settings.GEMINI_API_KEY or ""))
    logger.info("  OPENAI key   : %s", _mask(settings.OPENAI_API_KEY or ""))
    logger.info("  TAVILY key   : %s", _mask(settings.TAVILY_API_KEY))
    logger.info("  LLM primary  : %s", settings.GEMINI_MODEL_NAME if settings.GEMINI_API_KEY else settings.MODEL_NAME)
    logger.info("  LLM fallback : %s", settings.MODEL_NAME if settings.GEMINI_API_KEY else "none")
    logger.info("  CORS origins : %s", settings.CORS_ORIGINS)

    db_url = settings.DATABASE_URL
    if db_url and db_url.lower() not in ("", "none"):
        try:
            from backend.storage.sqlite_store import (
                SQLiteAccountStore,
                SQLiteJobStore,
                init_db,
            )

            await init_db(db_url)

            import backend.storage.account_store as _as
            import backend.storage.job_store as _js

            _js.job_store = SQLiteJobStore(db_url)
            _as.account_store = SQLiteAccountStore(db_url)
            logger.info("  Storage      : SQLite (%s)", db_url)
        except Exception as exc:
            logger.error(
                "  Storage      : SQLite init FAILED (%s) — falling back to in-memory: %s",
                db_url,
                exc,
                exc_info=True,
            )
            logger.warning("  Storage      : In-memory (data will not persist)")
    else:
        logger.info("  Storage      : In-memory (data lost on restart)")

    logger.info("━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━")
    yield
    logger.info("Shutting down Fello AI Account Intelligence API")


def create_app() -> FastAPI:
    """Create and configure the FastAPI application."""
    app = FastAPI(
        title="Fello AI Account Intelligence",
        description="Multi-agent pipeline converting visitor signals into sales intelligence.",
        version="1.0.0",
        lifespan=lifespan,
    )

    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.CORS_ORIGINS,
        allow_credentials=False,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    from backend.api.router import router
    app.include_router(router, prefix="/api/v1")

    return app


app = create_app()
