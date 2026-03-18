"""Centralized LLM service layer with Gemini (primary) and OpenAI (fallback).

Provides a single async interface for structured JSON generation.
All agent LLM calls should go through `llm_service.generate_json()`.
"""

import asyncio
import json
import logging
from typing import Any, Optional, Type, TypeVar

from pydantic import BaseModel

from backend.config import settings

logger = logging.getLogger(__name__)

T = TypeVar("T", bound=BaseModel)

_gemini_client: Any = None
_openai_model: Any = None


def _get_gemini_client() -> Optional[Any]:
    """Lazily initialize and return a google.genai Client, or None if unavailable."""
    global _gemini_client
    if _gemini_client is not None:
        return _gemini_client

    if not settings.GEMINI_API_KEY:
        logger.info("GEMINI_API_KEY not set — Gemini provider unavailable")
        return None

    try:
        from google import genai

        _gemini_client = genai.Client(api_key=settings.GEMINI_API_KEY)
        logger.info("Gemini client initialized for model: %s", settings.GEMINI_MODEL_NAME)
        return _gemini_client
    except Exception as exc:
        logger.warning("Failed to initialize Gemini client: %s", exc)
        return None


def _get_openai_model() -> Optional[Any]:
    """Lazily initialize and return a ChatOpenAI instance, or None if unavailable."""
    global _openai_model
    if _openai_model is not None:
        return _openai_model

    if not settings.OPENAI_API_KEY:
        logger.info("OPENAI_API_KEY not set — OpenAI provider unavailable")
        return None

    try:
        from langchain_openai import ChatOpenAI

        _openai_model = ChatOpenAI(
            model=settings.MODEL_NAME,
            temperature=0.0,
            api_key=settings.OPENAI_API_KEY,
        )
        logger.info("OpenAI model initialized: %s", settings.MODEL_NAME)
        return _openai_model
    except Exception as exc:
        logger.warning("Failed to initialize OpenAI: %s", exc)
        return None


def _extract_json_from_text(text: str) -> dict[str, Any]:
    """Extract JSON from LLM response text, handling markdown code fences and prose prefixes."""
    import re

    text = text.strip()
    # Try direct parse first
    try:
        return json.loads(text)
    except json.JSONDecodeError:
        pass

    # Extract JSON from ```json ... ``` or ``` ... ``` block
    match = re.search(r"```(?:json)?\s*([\s\S]*?)\s*```", text)
    if match:
        try:
            return json.loads(match.group(1).strip())
        except json.JSONDecodeError:
            pass

    # Extract first { ... } object
    brace_start = text.find("{")
    if brace_start >= 0:
        depth, i = 0, brace_start
        for i, c in enumerate(text[brace_start:], brace_start):
            if c == "{":
                depth += 1
            elif c == "}":
                depth -= 1
                if depth == 0:
                    try:
                        return json.loads(text[brace_start : i + 1])
                    except json.JSONDecodeError:
                        break
    raise json.JSONDecodeError("No valid JSON found", text, 0)


async def _call_gemini(prompt: str, temperature: float, max_tokens: int) -> Optional[str]:
    """Call Gemini API via google.genai and return raw text response."""
    client = _get_gemini_client()
    if client is None:
        return None

    try:
        from google.genai import types

        budget = max(max_tokens * 3, 8192)
        config = types.GenerateContentConfig(
            temperature=temperature,
            max_output_tokens=budget,
            response_mime_type="application/json",
        )
        response = await asyncio.to_thread(
            client.models.generate_content,
            model=settings.GEMINI_MODEL_NAME,
            contents=prompt,
            config=config,
        )
        if response and response.text:
            return response.text
        logger.warning("Gemini returned empty response")
        return None
    except Exception as exc:
        logger.warning("Gemini call failed: %s", exc)
        return None


async def _call_openai(prompt: str, temperature: float, max_tokens: int) -> Optional[str]:
    """Call OpenAI via LangChain and return raw text response."""
    if not settings.OPENAI_API_KEY:
        return None

    try:
        from langchain_openai import ChatOpenAI
        from langchain_core.messages import HumanMessage, SystemMessage

        configured_model = ChatOpenAI(
            model=settings.MODEL_NAME,
            temperature=temperature,
            max_tokens=max_tokens,
            api_key=settings.OPENAI_API_KEY,
            model_kwargs={"response_format": {"type": "json_object"}},
        )
        messages = [
            SystemMessage(content="You are a precise JSON generator. Always respond with valid JSON only."),
            HumanMessage(content=prompt),
        ]
        response = await configured_model.ainvoke(messages)
        if response and response.content:
            return str(response.content)
        logger.warning("OpenAI returned empty response")
        return None
    except Exception as exc:
        logger.warning("OpenAI call failed: %s", exc)
        return None


async def generate_json(
    prompt: str,
    response_model: Type[T],
    temperature: float = 0.0,
    max_tokens: int = 1000,
    max_retries: int = 2,
) -> Optional[T]:
    """Generate a structured JSON response from LLM, validated against a Pydantic model.

    Tries Gemini first, falls back to OpenAI on failure.
    Retries parsing up to `max_retries` times before giving up.

    Args:
        prompt: The full prompt including system instructions and expected output schema.
        response_model: Pydantic model class to validate and parse the response into.
        temperature: Sampling temperature for the LLM.
        max_tokens: Maximum output tokens.
        max_retries: Number of parse retry attempts per provider.

    Returns:
        A validated Pydantic model instance, or None if all attempts fail.
    """
    providers: list[tuple[str, Any]] = [
        ("gemini", _call_gemini),
        ("openai", _call_openai),
    ]

    for provider_name, call_fn in providers:
        for attempt in range(1, max_retries + 1):
            logger.info(
                "LLM call [%s] attempt %d/%d (temp=%.1f, max_tokens=%d)",
                provider_name, attempt, max_retries, temperature, max_tokens,
            )
            raw_text = await call_fn(prompt, temperature, max_tokens)
            if raw_text is None:
                logger.warning("[%s] returned None on attempt %d", provider_name, attempt)
                break

            try:
                parsed = _extract_json_from_text(raw_text)
                result = response_model.model_validate(parsed)
                logger.info("[%s] successfully parsed %s on attempt %d", provider_name, response_model.__name__, attempt)
                return result
            except (json.JSONDecodeError, ValueError, Exception) as exc:
                logger.warning(
                    "[%s] parse failed on attempt %d: %s — raw: %s",
                    provider_name, attempt, exc, raw_text[:200],
                )

    logger.error("All LLM providers failed for %s", response_model.__name__)
    return None
