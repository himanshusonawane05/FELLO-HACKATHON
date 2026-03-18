import logging
from datetime import datetime
from typing import ClassVar, Optional

import httpx

from backend.tools.base_tool import BaseTool, cached_call

logger = logging.getLogger(__name__)

CLOUD_PROVIDERS = {"amazon", "aws", "google", "gcp", "microsoft", "azure",
                   "cloudflare", "digitalocean", "linode", "vultr", "fastly"}


class IPLookupTool(BaseTool):
    """Reverse IP lookup via ipapi.co with ip-api.com fallback."""

    tool_name: ClassVar[str] = "ip_lookup"

    @cached_call(ttl=300)
    async def call(self, *, ip_address: str) -> Optional[dict]:
        """Look up company information for an IP address.

        Returns:
            dict with keys: company_name, country, city, isp, org,
                            is_cloud_provider, confidence, source_url,
                            fetched_at, tool_name
            None on any failure.
        """
        result = await self._lookup_ipapi(ip_address)
        if result is None:
            result = await self._lookup_ipapi_fallback(ip_address)
        return result

    async def _lookup_ipapi(self, ip: str) -> Optional[dict]:
        """Primary: ipapi.co"""
        url = f"https://ipapi.co/{ip}/json/"
        try:
            async with httpx.AsyncClient(timeout=8.0) as client:
                resp = await client.get(url)
                resp.raise_for_status()
                data = resp.json()
            return self._normalise(data, source_url=url)
        except Exception as exc:
            logger.warning("ip_lookup ipapi.co failed for %s: %s", ip[:8] + "...", type(exc).__name__)
            return None

    async def _lookup_ipapi_fallback(self, ip: str) -> Optional[dict]:
        """Fallback: ip-api.com"""
        url = f"http://ip-api.com/json/{ip}"
        try:
            async with httpx.AsyncClient(timeout=8.0) as client:
                resp = await client.get(url)
                resp.raise_for_status()
                data = resp.json()
            return self._normalise(data, source_url=url)
        except Exception as exc:
            logger.warning("ip_lookup ip-api.com fallback failed for %s: %s", ip[:8] + "...", type(exc).__name__)
            return None

    def _normalise(self, data: dict, source_url: str) -> dict:
        org: str = data.get("org", "") or ""
        isp: str = data.get("isp", "") or ""
        is_cloud = any(cp in (org + isp).lower() for cp in CLOUD_PROVIDERS)
        company_name = None if is_cloud else (data.get("org") or data.get("isp"))
        return {
            "company_name": company_name,
            "country": data.get("country_name") or data.get("country"),
            "city": data.get("city"),
            "isp": isp,
            "org": org,
            "is_cloud_provider": is_cloud,
            "confidence": 0.5 if is_cloud else 0.8,
            "source_url": source_url,
            "fetched_at": datetime.utcnow().isoformat(),
            "tool_name": self.tool_name,
        }
