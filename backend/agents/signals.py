import logging
from typing import ClassVar, Optional

from backend.agents.base_agent import BaseAgent
from backend.core.llm_service import generate_json
from backend.domain.base import BaseEntity
from backend.domain.company import CompanyProfile
from backend.domain.signals import BusinessSignals, Signal, SignalType

logger = logging.getLogger(__name__)


def _is_unknown_company(name: str) -> bool:
    lower = name.strip().lower()
    return lower in ("unknown", "unknown (private ip)", "none", "")


class _SignalsLLMResponse(BaseEntity):
    """Schema for LLM-generated business signals."""
    signals: list[dict] = []
    confidence_score: float = 0.5


class SignalsAgent(BaseAgent):
    """Discovers business signals using Tavily search and LLM analysis.

    Returns empty signals for unknown/unresolved companies.
    """

    agent_name: ClassVar[str] = "signals_agent"

    def validate_input(self, input: BaseEntity) -> bool:
        return isinstance(input, CompanyProfile)

    async def run(self, input: BaseEntity) -> BusinessSignals:
        if not self.validate_input(input):
            return BusinessSignals(confidence_score=0.0, reasoning_trace=["No company profile"])

        company: CompanyProfile = input  # type: ignore[assignment]

        if _is_unknown_company(company.company_name) or company.confidence_score < 0.3:
            logger.info("[%s] unknown/low-confidence company — returning empty signals", self.agent_name)
            return BusinessSignals(
                signals=[],
                confidence_score=0.0,
                reasoning_trace=["Company is unknown or low-confidence — signal detection skipped"],
            )

        logger.info("[%s] searching business signals for %s", self.agent_name, company.company_name)

        search_context = await self._tavily_search(company)
        return await self._llm_signals(company, search_context)

    async def _tavily_search(self, company: CompanyProfile) -> Optional[str]:
        """Search Tavily for recent business signals."""
        try:
            from backend.tools.web_search import WebSearchTool

            tool = WebSearchTool()
            query = f"{company.company_name} recent news hiring funding expansion partnership 2024 2025 2026"
            result = await tool.call(query=query, max_results=5)

            if result and result.get("results"):
                snippets = [
                    f"[{r.get('title', '')}] {r.get('snippet', '')}"
                    for r in result["results"] if r.get("snippet")
                ]
                context = "\n".join(snippets[:5])
                logger.info("[%s] Tavily found %d signal results for %s",
                           self.agent_name, len(snippets), company.company_name)
                return context if context.strip() else None
            return None
        except Exception as exc:
            logger.warning("[%s] Tavily search failed: %s", self.agent_name, exc)
            return None

    async def _llm_signals(self, company: CompanyProfile, search_context: Optional[str]) -> BusinessSignals:
        """Use LLM to extract business signals from search context."""
        context_block = ""
        if search_context:
            context_block = f"""
Here are recent web search results about the company:
---
{search_context}
---
Extract real business signals from this information.
"""
        else:
            context_block = "No web search results available. Use your general knowledge if you know this company well. If not, return an empty signals array."

        prompt = f"""You are a B2B sales intelligence analyst. Identify business signals for "{company.company_name}" (industry: {company.industry or 'Unknown'}).

{context_block}

Return a JSON object with:
- signals: array of objects, each with:
  - signal_type: one of: HIRING, FUNDING, EXPANSION, PRODUCT_LAUNCH, PARTNERSHIP, LEADERSHIP_CHANGE, OTHER
  - title: string (short title)
  - description: string (1-2 sentence description)
  - source_url: string URL or null
- confidence_score: float 0.0-1.0

Only include signals you have evidence for. Max 5 signals.
Return ONLY valid JSON."""

        result = await generate_json(
            prompt=prompt,
            response_model=_SignalsLLMResponse,
            temperature=0.2,
            max_tokens=1024,
        )

        if result and result.signals:
            signals = []
            for s in result.signals[:5]:
                try:
                    signal_type = SignalType(s.get("signal_type", "OTHER"))
                except ValueError:
                    signal_type = SignalType.OTHER
                signals.append(Signal(
                    signal_type=signal_type,
                    title=s.get("title", "Business Signal"),
                    description=s.get("description", ""),
                    source_url=s.get("source_url"),
                ))
            return BusinessSignals(
                signals=signals,
                confidence_score=max(0.0, min(1.0, result.confidence_score)),
                reasoning_trace=[f"LLM extracted {len(signals)} signals for {company.company_name}"],
            )

        return BusinessSignals(
            signals=[],
            confidence_score=0.0,
            reasoning_trace=["Signal detection failed or returned no results"],
        )
