import logging
from typing import ClassVar, Optional

from backend.agents.base_agent import BaseAgent
from backend.core.llm_service import generate_json
from backend.domain.base import BaseEntity
from backend.domain.company import CompanyProfile
from backend.domain.leadership import Leader, LeadershipProfile

logger = logging.getLogger(__name__)


def _is_unknown_company(name: str) -> bool:
    lower = name.strip().lower()
    return lower in ("unknown", "unknown (private ip)", "none", "")


class _LeadershipLLMResponse(BaseEntity):
    """Schema for LLM-generated leadership data."""
    leaders: list[dict] = []
    confidence_score: float = 0.5


class LeadershipAgent(BaseAgent):
    """Discovers company leadership using Tavily search and LLM.

    Returns empty leadership for unknown/unresolved companies.
    """

    agent_name: ClassVar[str] = "leadership_agent"

    def validate_input(self, input: BaseEntity) -> bool:
        return isinstance(input, CompanyProfile)

    async def run(self, input: BaseEntity) -> LeadershipProfile:
        if not self.validate_input(input):
            return LeadershipProfile(confidence_score=0.0, reasoning_trace=["No company profile"])

        company: CompanyProfile = input  # type: ignore[assignment]

        if _is_unknown_company(company.company_name) or company.confidence_score < 0.3:
            logger.info("[%s] unknown/low-confidence company — returning empty leadership", self.agent_name)
            return LeadershipProfile(
                leaders=[],
                confidence_score=0.0,
                reasoning_trace=["Company is unknown or low-confidence — leadership discovery skipped"],
            )

        logger.info("[%s] discovering leadership for %s", self.agent_name, company.company_name)

        search_context = await self._tavily_search(company)
        return await self._llm_leadership(company, search_context)

    async def _tavily_search(self, company: CompanyProfile) -> Optional[str]:
        """Search Tavily for leadership information."""
        try:
            from backend.tools.web_search import WebSearchTool

            tool = WebSearchTool()
            query = f"{company.company_name} leadership team CEO executives"
            if company.domain:
                query += f" site:{company.domain}"
            result = await tool.call(query=query, max_results=5)

            if result and result.get("results"):
                snippets = [
                    f"[{r.get('title', '')}] {r.get('snippet', '')}"
                    for r in result["results"] if r.get("snippet")
                ]
                return "\n".join(snippets[:5]) if snippets else None
            return None
        except Exception as exc:
            logger.warning("[%s] Tavily search failed: %s", self.agent_name, exc)
            return None

    async def _llm_leadership(
        self, company: CompanyProfile, search_context: Optional[str]
    ) -> LeadershipProfile:
        """Use LLM to extract leadership from search context or general knowledge."""
        context_block = ""
        if search_context:
            context_block = f"""
Here are web search results about the company's leadership:
---
{search_context}
---
Extract real leadership information from these results.
"""
        else:
            context_block = "No web search results available. Use your general knowledge if you know this company's leadership. If not, return an empty leaders array."

        prompt = f"""You are a B2B sales intelligence analyst. Identify the leadership team for "{company.company_name}" (industry: {company.industry or 'Unknown'}).

{context_block}

Return a JSON object with:
- leaders: array of objects, each with:
  - name: string (full name)
  - title: string (job title)
  - department: string (e.g. "Executive", "Sales", "Engineering")
  - linkedin_url: string URL or null
- confidence_score: float 0.0-1.0

Only include leaders you have evidence for. Max 5 leaders.
Return ONLY valid JSON."""

        result = await generate_json(
            prompt=prompt,
            response_model=_LeadershipLLMResponse,
            temperature=0.1,
            max_tokens=1024,
        )

        if result and result.leaders:
            domain = company.domain or company.company_name.lower().replace(" ", "") + ".com"
            leaders = [
                Leader(
                    name=l.get("name", "Unknown"),
                    title=l.get("title", "Unknown"),
                    department=l.get("department"),
                    linkedin_url=l.get("linkedin_url"),
                    source_url=f"https://{domain}/about",
                )
                for l in result.leaders[:5]
            ]
            return LeadershipProfile(
                leaders=leaders,
                confidence_score=max(0.0, min(1.0, result.confidence_score)),
                reasoning_trace=[f"LLM identified {len(leaders)} leaders at {company.company_name}"],
            )

        return LeadershipProfile(
            leaders=[],
            confidence_score=0.0,
            reasoning_trace=["Leadership discovery failed or returned no results"],
        )
