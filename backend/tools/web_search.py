import asyncio
import logging
from datetime import datetime
from typing import ClassVar, Optional

from backend.config import settings
from backend.tools.base_tool import BaseTool, cached_call

logger = logging.getLogger(__name__)

BLOCKED_DOMAINS = {"reddit.com", "quora.com", "pinterest.com"}


class WebSearchTool(BaseTool):
    """Web search via Tavily API."""

    tool_name: ClassVar[str] = "web_search"

    @cached_call(ttl=300)
    async def call(self, *, query: str, max_results: int = 5) -> Optional[dict]:
        """Search the web using Tavily.

        Returns:
            dict with keys: results (list), query, source_url, fetched_at, tool_name
            None on any failure.
        """
        if not settings.TAVILY_API_KEY:
            logger.warning("TAVILY_API_KEY not configured — web search unavailable")
            return None

        try:
            from tavily import TavilyClient

            client = TavilyClient(api_key=settings.TAVILY_API_KEY)
            response = await asyncio.to_thread(
                client.search, query=query, max_results=max_results + 3
            )

            filtered = [
                {
                    "title": r.get("title", ""),
                    "url": r.get("url", ""),
                    "snippet": r.get("content", ""),
                    "rank": idx + 1,
                    "domain": r.get("url", "").split("/")[2] if r.get("url") else "",
                }
                for idx, r in enumerate(response.get("results", []))
                if not any(bd in r.get("url", "") for bd in BLOCKED_DOMAINS)
            ][:max_results]

            logger.info("Tavily search returned %d results for '%s'", len(filtered), query[:50])
            return {
                "results": filtered,
                "query": query,
                "source_url": "https://api.tavily.com",
                "fetched_at": datetime.utcnow().isoformat(),
                "tool_name": self.tool_name,
            }
        except Exception as exc:
            logger.warning("web_search failed for query '%s': %s", query[:50], type(exc).__name__)
            return None
