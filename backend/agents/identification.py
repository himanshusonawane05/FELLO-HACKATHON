import logging
from typing import ClassVar

from backend.agents.base_agent import BaseAgent
from backend.domain.base import BaseEntity
from backend.domain.company import CompanyInput
from backend.domain.visitor import VisitorSignal

logger = logging.getLogger(__name__)

_PRIVATE_PREFIXES = (
    "10.", "127.", "192.168.", "0.", "100.64.", "100.65.", "100.66.", "100.67.",
    "169.254.", "172.16.", "172.17.", "172.18.", "172.19.", "172.2", "172.3",
    "198.18.", "198.19.",
)


class IdentificationAgent(BaseAgent):
    """Resolves a visitor IP address to a company name.

    Uses real IP lookup tools (ipapi.co, ip-api.com) and Tavily web search.
    For unresolved or cloud-provider IPs, returns a low-confidence 'Unknown'
    result instead of fabricating a company name.
    """

    agent_name: ClassVar[str] = "identification_agent"

    def validate_input(self, input: BaseEntity) -> bool:
        return isinstance(input, VisitorSignal) and bool(input.ip_address)

    async def run(self, input: BaseEntity) -> CompanyInput:
        if not self.validate_input(input):
            logger.warning("[%s] invalid input — returning Unknown", self.agent_name)
            return CompanyInput(company_name="Unknown")

        signal: VisitorSignal = input  # type: ignore[assignment]
        ip = signal.ip_address

        if any(ip.startswith(p) for p in _PRIVATE_PREFIXES):
            logger.info("[%s] private/reserved IP %s — cannot resolve", self.agent_name, ip)
            return CompanyInput(company_name="Unknown (Private IP)")

        company_name, domain = await self._real_ip_lookup(ip)

        if company_name:
            logger.info("[%s] IP %s → %s (real lookup)", self.agent_name, ip, company_name)
            return CompanyInput(company_name=company_name, domain=domain)

        company_name = await self._tavily_search(ip)
        if company_name:
            logger.info("[%s] IP %s → %s (Tavily search)", self.agent_name, ip, company_name)
            return CompanyInput(company_name=company_name)

        logger.info(
            "[%s] IP %s could not be resolved to a company — returning Unknown",
            self.agent_name, ip,
        )
        return CompanyInput(company_name="Unknown")

    async def _real_ip_lookup(self, ip: str) -> tuple[str | None, str | None]:
        """Attempt real IP lookup via IPLookupTool. Returns (company_name, domain) or (None, None)."""
        try:
            from backend.tools.ip_lookup import IPLookupTool

            tool = IPLookupTool()
            result = await tool.call(ip_address=ip)

            if result is None:
                logger.info("[%s] IP lookup tool returned None for %s", self.agent_name, ip)
                return None, None

            if result.get("is_cloud_provider"):
                org = result.get("org", "")
                isp = result.get("isp", "")
                logger.info(
                    "[%s] IP %s belongs to cloud/ISP provider (org=%s, isp=%s) — not a company",
                    self.agent_name, ip, org, isp,
                )
                return None, None

            company_name = result.get("company_name")
            if not company_name or company_name.strip().lower() in ("", "unknown", "none"):
                return None, None

            return company_name, None

        except Exception as exc:
            logger.warning("[%s] IP lookup failed for %s: %s", self.agent_name, ip, exc)
            return None, None

    async def _tavily_search(self, ip: str) -> str | None:
        """Use Tavily web search to try to identify the company behind an IP."""
        try:
            from backend.tools.web_search import WebSearchTool

            tool = WebSearchTool()
            result = await tool.call(query=f"what company uses IP address {ip}", max_results=3)

            if result is None or not result.get("results"):
                return None

            for r in result["results"]:
                title = r.get("title", "")
                snippet = r.get("snippet", "")
                if title and len(title) > 3 and "ip" not in title.lower():
                    logger.info("[%s] Tavily found potential match: %s", self.agent_name, title[:60])
                    return None  # Tavily rarely gives reliable company-from-IP; don't fabricate

            return None

        except Exception as exc:
            logger.warning("[%s] Tavily search failed for IP %s: %s", self.agent_name, ip, exc)
            return None
