import logging
from datetime import datetime
from typing import ClassVar, Optional

import httpx

from backend.config import settings
from backend.tools.base_tool import BaseTool, cached_call

logger = logging.getLogger(__name__)


class EnrichmentAPITool(BaseTool):
    """Company enrichment via Clearbit → Apollo → LLM fallback."""

    tool_name: ClassVar[str] = "enrichment_apis"

    @cached_call(ttl=300)
    async def call(self, *, company_name: str, domain: Optional[str] = None) -> Optional[dict]:
        """Enrich a company using available APIs.

        Tries Clearbit first, then Apollo, falls back to stub for LLM enrichment.

        Returns:
            Normalised dict compatible with CompanyProfile fields.
            None on total failure.
        """
        if settings.CLEARBIT_API_KEY:
            result = await self._clearbit(domain or company_name)
            if result:
                return result

        if settings.APOLLO_API_KEY:
            result = await self._apollo(company_name, domain)
            if result:
                return result

        return self._llm_fallback_stub(company_name, domain)

    async def _clearbit(self, domain: str) -> Optional[dict]:
        url = f"https://company.clearbit.com/v2/companies/find?domain={domain}"
        try:
            async with httpx.AsyncClient(timeout=8.0) as client:
                resp = await client.get(
                    url, headers={"Authorization": f"Bearer {settings.CLEARBIT_API_KEY}"}
                )
                resp.raise_for_status()
                d = resp.json()
            return self._normalise_clearbit(d)
        except Exception as exc:
            logger.warning("clearbit failed for %s: %s", domain, type(exc).__name__)
            return None

    async def _apollo(self, company_name: str, domain: Optional[str]) -> Optional[dict]:
        url = "https://api.apollo.io/v1/organizations/enrich"
        params = {"api_key": settings.APOLLO_API_KEY, "domain": domain or "", "name": company_name}
        try:
            async with httpx.AsyncClient(timeout=8.0) as client:
                resp = await client.get(url, params=params)
                resp.raise_for_status()
                d = resp.json().get("organization", {})
            return self._normalise_apollo(d)
        except Exception as exc:
            logger.warning("apollo failed for %s: %s", company_name, type(exc).__name__)
            return None

    def _llm_fallback_stub(self, company_name: str, domain: Optional[str]) -> dict:
        """Minimal stub returned when no enrichment API is available.
        The agent will use its LLM to populate fields from this base."""
        return {
            "company_name": company_name,
            "domain": domain,
            "industry": None,
            "company_size": None,
            "headquarters": None,
            "description": None,
            "founded_year": None,
            "enrichment_source": "llm_fallback",
            "source_url": "",
            "fetched_at": datetime.utcnow().isoformat(),
            "tool_name": self.tool_name,
        }

    def _normalise_clearbit(self, d: dict) -> dict:
        return {
            "company_name": d.get("name", ""),
            "domain": d.get("domain"),
            "industry": d.get("category", {}).get("sector"),
            "company_size": d.get("metrics", {}).get("employeesRange"),
            "headquarters": f"{d.get('geo', {}).get('city')}, {d.get('geo', {}).get('country')}",
            "description": d.get("description"),
            "founded_year": d.get("foundedYear"),
            "enrichment_source": "clearbit",
            "source_url": f"https://clearbit.com/company/{d.get('domain', '')}",
            "fetched_at": datetime.utcnow().isoformat(),
            "tool_name": self.tool_name,
        }

    def _normalise_apollo(self, d: dict) -> dict:
        return {
            "company_name": d.get("name", ""),
            "domain": d.get("primary_domain"),
            "industry": d.get("industry"),
            "company_size": d.get("estimated_num_employees"),
            "headquarters": d.get("city"),
            "description": d.get("short_description"),
            "founded_year": d.get("founded_year"),
            "enrichment_source": "apollo",
            "source_url": f"https://app.apollo.io/companies/{d.get('id', '')}",
            "fetched_at": datetime.utcnow().isoformat(),
            "tool_name": self.tool_name,
        }
