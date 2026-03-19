import logging
from typing import ClassVar, Optional

from backend.agents.base_agent import BaseAgent
from backend.core.llm_service import generate_json
from backend.domain.base import BaseEntity
from backend.domain.company import CompanyInput, CompanyProfile

logger = logging.getLogger(__name__)


def _is_unknown_company(name: str) -> bool:
    """Check if company name indicates an unresolved identification."""
    lower = name.strip().lower()
    return lower in ("unknown", "unknown (private ip)", "none", "")


class _EnrichmentLLMResponse(BaseEntity):
    """Schema for LLM-generated company enrichment."""
    industry: Optional[str] = None
    company_size_estimate: Optional[str] = None
    headquarters: Optional[str] = None
    founding_year: Optional[int] = None
    description: Optional[str] = None
    annual_revenue_range: Optional[str] = None
    confidence_score: float = 0.5


class EnrichmentAgent(BaseAgent):
    """Enriches a CompanyInput into a full CompanyProfile.

    Uses Tavily web search for real data and LLM for synthesis.
    For Unknown/unresolved companies, returns minimal low-confidence profiles.
    """

    agent_name: ClassVar[str] = "enrichment_agent"

    def validate_input(self, input: BaseEntity) -> bool:
        return isinstance(input, CompanyInput) and bool(input.company_name)

    async def run(self, input: BaseEntity) -> CompanyProfile:
        if not self.validate_input(input):
            return CompanyProfile(company_name="Unknown", confidence_score=0.0)

        company: CompanyInput = input  # type: ignore[assignment]

        if _is_unknown_company(company.company_name):
            logger.info("[%s] company is Unknown — returning low-confidence profile", self.agent_name)
            return CompanyProfile(
                company_name=company.company_name,
                domain=company.domain,
                confidence_score=0.1,
                reasoning_trace=[
                    "Company could not be identified from visitor IP",
                    "No enrichment data available for unknown company",
                ],
            )

        logger.info("[%s] enriching %s via Tavily + LLM", self.agent_name, company.company_name)

        search_context = await self._tavily_enrich(company.company_name, company.domain)
        scrape_context = await self._scrape_enrich(company.domain)

        llm_profile = await self._llm_enrich(
            company.company_name, company.domain, search_context, scrape_context
        )

        if llm_profile:
            raw_confidence = llm_profile.get("confidence_score", 0.6)
            # Ensure confidence >= 0.4 for identified companies so downstream agents
            # (TechStack, Signals, Leadership) do not skip when Tavily failed but LLM succeeded
            effective_confidence = max(float(raw_confidence), 0.4) if not search_context else raw_confidence
            data_sources = []
            if search_context:
                data_sources.append("tavily_search")
            if scrape_context:
                data_sources.append("web_scrape")
            data_sources.append("llm_synthesis")
            return CompanyProfile(
                company_name=company.company_name,
                domain=company.domain or llm_profile.get("domain"),
                industry=llm_profile.get("industry"),
                company_size_estimate=llm_profile.get("company_size_estimate"),
                headquarters=llm_profile.get("headquarters"),
                founding_year=llm_profile.get("founding_year"),
                description=llm_profile.get("description"),
                annual_revenue_range=llm_profile.get("annual_revenue_range"),
                confidence_score=effective_confidence,
                data_sources=data_sources,
                reasoning_trace=[
                    f"Enriched {company.company_name} via LLM with "
                    f"{'web search context' if search_context else 'general knowledge'}"
                    f"{' + scraped homepage' if scrape_context else ''}",
                ],
            )

        logger.warning("[%s] LLM enrichment failed — returning minimal profile", self.agent_name)
        return CompanyProfile(
            company_name=company.company_name,
            domain=company.domain,
            confidence_score=0.3,
            data_sources=["fallback"],
            reasoning_trace=["LLM enrichment failed; returning minimal profile"],
        )

    def _normalize_for_search(self, company_name: str) -> str:
        """Normalize company name for search consistency (avoids cache fragmentation)."""
        s = company_name.strip()
        for suffix in (" Inc.", " Inc", " Inc.,", " LLC.", " LLC", ", Inc.", ", Inc"):
            if s.endswith(suffix):
                return s[: -len(suffix)].strip()
        return s

    async def _tavily_enrich(self, company_name: str, domain: Optional[str]) -> Optional[str]:
        """Search Tavily for company information. Returns concatenated search snippets."""
        try:
            from backend.tools.web_search import WebSearchTool

            tool = WebSearchTool()
            normalized = self._normalize_for_search(company_name)
            query = f"{normalized} company overview industry employees revenue"
            if domain:
                query = f"site:{domain} OR {query}"

            result = await tool.call(query=query, max_results=5)
            if result is None or not result.get("results"):
                logger.info("[%s] Tavily returned no results for %s", self.agent_name, company_name)
                return None

            snippets = [
                f"[{r.get('title', '')}] {r.get('snippet', '')}"
                for r in result["results"]
                if r.get("snippet")
            ]
            context = "\n".join(snippets[:5])
            logger.info("[%s] Tavily returned %d results for %s", self.agent_name, len(snippets), company_name)
            return context if context.strip() else None

        except Exception as exc:
            logger.warning("[%s] Tavily search failed for %s: %s", self.agent_name, company_name, exc)
            return None

    async def _scrape_enrich(self, domain: Optional[str]) -> Optional[str]:
        """Scrape the company homepage for additional context. Returns None on any failure."""
        if not domain:
            logger.info("[%s] scraper skipped (no domain)", self.agent_name)
            return None
        try:
            from backend.tools.scraper import ScraperTool

            tool = ScraperTool()
            result = await tool.call(url=domain)
            if not result:
                logger.info("[%s] scraper skipped (no result for %s)", self.agent_name, domain)
                return None

            parts: list[str] = []
            if result.get("title"):
                parts.append(f"Title: {result['title']}")
            if result.get("meta_description"):
                parts.append(f"Description: {result['meta_description']}")
            if result.get("visible_text"):
                parts.append(f"Page text: {result['visible_text'][:500]}")

            if not parts:
                return None

            logger.info("[%s] scraper used for %s", self.agent_name, domain)
            return "\n".join(parts)
        except Exception as exc:
            logger.info("[%s] scraper skipped (%s: %s)", self.agent_name, domain, exc)
            return None

    async def _llm_enrich(
        self,
        company_name: str,
        domain: Optional[str],
        search_context: Optional[str],
        scrape_context: Optional[str] = None,
    ) -> Optional[dict]:
        """Use LLM to synthesize a company profile from search results or general knowledge."""
        context_block = ""
        if search_context or scrape_context:
            sections: list[str] = []
            if search_context:
                sections.append(f"Web search results:\n---\n{search_context}\n---")
            if scrape_context:
                sections.append(f"Homepage content:\n---\n{scrape_context}\n---")
            context_block = (
                "\n\n".join(sections)
                + "\n\nUse this information to fill in the profile accurately."
            )
        else:
            context_block = """No web search results are available. Use your general knowledge.
For well-known organizations (e.g. Wikimedia Foundation, major tech companies, Fortune 500), set confidence_score >= 0.5.
If you don't recognize the company at all, set confidence_score below 0.4."""

        prompt = f"""You are a B2B sales intelligence analyst. Generate a company profile for "{company_name}"{f' (domain: {domain})' if domain else ''}.

{context_block}

Return a JSON object with these fields:
- industry: string (e.g. "Technology / SaaS", "Financial Services")
- company_size_estimate: string (e.g. "50-200 employees")
- headquarters: string (e.g. "San Francisco, CA, USA")
- founding_year: integer or null
- description: string (2-3 sentence company description)
- annual_revenue_range: string (e.g. "$10M-$50M") or null
- confidence_score: float 0.0-1.0 (how confident you are in this data)

IMPORTANT: Only include information you are confident about. Set confidence_score based on data quality.
If you don't know the company, set confidence_score below 0.3 and leave fields null.

Return ONLY valid JSON, no markdown, no explanation."""

        result = await generate_json(
            prompt=prompt,
            response_model=_EnrichmentLLMResponse,
            temperature=0.1,
            max_tokens=1024,
        )

        if result:
            return result.model_dump()
        return None
