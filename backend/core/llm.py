"""Centralized LLM factory.

All agents must obtain their LLM instance through `get_llm()`.
Supports Gemini (primary) via LangChain adapter, OpenAI as fallback.
"""

import logging
from functools import lru_cache

from langchain_core.language_models import BaseChatModel

from backend.config import settings

logger = logging.getLogger(__name__)


@lru_cache(maxsize=4)
def get_llm(temperature: float = 0.0) -> BaseChatModel:
    """Return a configured LLM instance — tries Gemini first, falls back to OpenAI.

    Results are cached per temperature value so agent init is fast.
    """
    if settings.GEMINI_API_KEY:
        try:
            from langchain_google_genai import ChatGoogleGenerativeAI

            llm = ChatGoogleGenerativeAI(
                model=settings.GEMINI_MODEL_NAME,
                temperature=temperature,
                google_api_key=settings.GEMINI_API_KEY,
            )
            logger.info("Using Gemini model: %s (temp=%.1f)", settings.GEMINI_MODEL_NAME, temperature)
            return llm
        except Exception as exc:
            logger.warning("Gemini LLM init failed, falling back to OpenAI: %s", exc)

    if settings.OPENAI_API_KEY:
        from langchain_openai import ChatOpenAI

        llm = ChatOpenAI(
            model=settings.MODEL_NAME,
            temperature=temperature,
            api_key=settings.OPENAI_API_KEY,
        )
        logger.info("Using OpenAI model: %s (temp=%.1f)", settings.MODEL_NAME, temperature)
        return llm

    from langchain_openai import ChatOpenAI

    logger.warning("No LLM API keys configured — agents will use mock fallbacks")
    return ChatOpenAI(model=settings.MODEL_NAME, temperature=temperature, api_key="sk-missing")
