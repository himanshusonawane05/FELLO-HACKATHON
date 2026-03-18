import asyncio
import logging
from datetime import datetime
from typing import ClassVar, Optional

import httpx
from bs4 import BeautifulSoup

from backend.tools.base_tool import BaseTool, cached_call

logger = logging.getLogger(__name__)


class ScraperTool(BaseTool):
    """Async web scraper with 8-second hard timeout."""

    tool_name: ClassVar[str] = "scraper"

    @cached_call(ttl=300)
    async def call(self, *, url: str) -> Optional[dict]:
        """Scrape a URL and extract text content and script sources.

        Returns:
            dict with keys: url, title, meta_description, visible_text,
                            script_sources, source_url, fetched_at, tool_name
            None on any failure.
        """
        if not url.startswith(("http://", "https://")):
            url = f"https://{url}"
        try:
            async with asyncio.timeout(8.0):
                async with httpx.AsyncClient(
                    timeout=8.0,
                    follow_redirects=True,
                    headers={"User-Agent": "Mozilla/5.0 (compatible; FelloBot/1.0)"},
                ) as client:
                    resp = await client.get(url)
                    resp.raise_for_status()
                    html = resp.text
        except Exception as exc:
            logger.warning("scraper failed for %s: %s", url, type(exc).__name__)
            return None

        return self._parse(html, url)

    def _parse(self, html: str, url: str) -> dict:
        soup = BeautifulSoup(html, "html.parser")

        title = soup.title.string.strip() if soup.title else None
        meta_tag = soup.find("meta", attrs={"name": "description"})
        meta_description = meta_tag.get("content", "").strip() if meta_tag else None

        for tag in soup(["script", "style", "nav", "footer", "header"]):
            tag.decompose()
        visible_text = " ".join(soup.get_text(" ", strip=True).split())[:2000]

        script_sources = [
            s.get("src", "")
            for s in soup.find_all("script", src=True)
            if s.get("src")
        ]

        return {
            "url": url,
            "title": title,
            "meta_description": meta_description,
            "visible_text": visible_text,
            "script_sources": script_sources,
            "source_url": url,
            "fetched_at": datetime.utcnow().isoformat(),
            "tool_name": self.tool_name,
        }
