"""LangGraph node functions.

Each node runs one stage of the pipeline and returns a partial state update dict.
Parallel stages use asyncio.gather internally — LangGraph sees a single sequential node,
which is simpler and avoids LangGraph fan-in edge complications.

Progress is written directly to job_store inside each node so the poller always
sees up-to-date status.
"""
import asyncio
import logging
from typing import Any, Optional

from backend.graph.state import PipelineState

logger = logging.getLogger(__name__)


def _build_agents() -> dict[str, Any]:
    """Lazily import and instantiate agents. Called once per node execution."""
    from backend.agents.enrichment import EnrichmentAgent
    from backend.agents.identification import IdentificationAgent
    from backend.agents.intent_scorer import IntentScorerAgent
    from backend.agents.leadership import LeadershipAgent
    from backend.agents.persona import PersonaAgent
    from backend.agents.playbook import PlaybookAgent
    from backend.agents.signals import SignalsAgent
    from backend.agents.summary import SummaryAgent
    from backend.agents.tech_stack import TechStackAgent
    from backend.core.llm import get_llm

    llm = get_llm()
    return {
        "identification": IdentificationAgent(llm=llm),
        "enrichment": EnrichmentAgent(llm=llm),
        "persona": PersonaAgent(llm=llm),
        "intent_scorer": IntentScorerAgent(llm=llm),
        "tech_stack": TechStackAgent(llm=llm),
        "signals": SignalsAgent(llm=llm),
        "leadership": LeadershipAgent(llm=llm),
        "playbook": PlaybookAgent(llm=llm),
        "summary": SummaryAgent(llm=llm),
    }


async def _update_progress(job_id: str, progress: float, step: str) -> None:
    """Write job progress to store. Silently ignores failures."""
    try:
        import backend.storage.job_store as _js
        await _js.job_store.update(job_id, status=_js.JobStatus.PROCESSING, progress=progress, current_step=step)
    except Exception as exc:
        logger.warning("progress update failed for %s: %s", job_id, exc)


# ── Routing ────────────────────────────────────────────────────────────────────

def route_input(state: PipelineState) -> str:
    """Conditional router: visitor signal needs identification; company skips straight to stage 1."""
    if state.get("visitor_signal"):
        return "identification_node"
    return "stage1_node"


# ── Stage 0 ────────────────────────────────────────────────────────────────────

async def identification_node(state: PipelineState) -> dict:
    """Resolve visitor IP → CompanyInput. Progress: 0.05 → 0.15."""
    job_id: str = state.get("job_id", "")
    await _update_progress(job_id, 0.05, "Identifying company from visitor signal")

    agents = _build_agents()
    signal = state.get("visitor_signal")
    if not signal:
        return {"errors": ["identification_node: no visitor_signal in state"], "reasoning_trace": []}

    try:
        result = await agents["identification"].run(signal)
        await _update_progress(job_id, 0.15, f"Company identified: {result.company_name}")
        return {
            "identified_company": result,
            "errors": [],
            "reasoning_trace": [f"Stage 0 — Identified company: {result.company_name} from IP {signal.ip_address[:8]}..."],
        }
    except Exception as exc:
        logger.error("identification_node error: %s", exc)
        from backend.domain.company import CompanyInput
        return {
            "identified_company": CompanyInput(company_name="Unknown"),
            "errors": [f"identification_node: {exc}"],
            "reasoning_trace": ["Stage 0 — Identification failed; using Unknown fallback"],
        }


# ── Stage 1 (parallel via asyncio.gather) ─────────────────────────────────────

async def stage1_node(state: PipelineState) -> dict:
    """Enrichment + Persona + IntentScorer concurrently. Progress: 0.15 → 0.50."""
    job_id: str = state.get("job_id", "")
    await _update_progress(job_id, 0.20, "Enriching company profile")

    agents = _build_agents()
    company_input = state.get("identified_company") or state.get("company_input")
    visitor_signal = state.get("visitor_signal")

    if not company_input:
        return {"errors": ["stage1_node: no company_input"], "reasoning_trace": []}

    async def run_enrichment():
        try:
            return await agents["enrichment"].run(company_input)
        except Exception as exc:
            logger.error("enrichment error: %s", exc)
            from backend.domain.company import CompanyProfile
            return CompanyProfile(company_name=company_input.company_name, confidence_score=0.0,
                                  reasoning_trace=[str(exc)])

    async def run_persona():
        if not visitor_signal:
            return None
        try:
            return await agents["persona"].run(visitor_signal)
        except Exception as exc:
            logger.error("persona error: %s", exc)
            return None

    async def run_intent():
        if not visitor_signal:
            return None
        try:
            return await agents["intent_scorer"].run(visitor_signal)
        except Exception as exc:
            logger.error("intent error: %s", exc)
            return None

    enrichment_result, persona_result, intent_result = await asyncio.gather(
        run_enrichment(), run_persona(), run_intent()
    )

    await _update_progress(job_id, 0.50, "Analyzing tech stack, signals, and leadership")

    trace = [
        f"Stage 1 — Enriched: {enrichment_result.company_name} (confidence: {enrichment_result.confidence_score})",
    ]
    if persona_result:
        trace.append(f"Stage 1 — Persona: {persona_result.likely_role} ({persona_result.seniority_level.value})")
    if intent_result:
        trace.append(f"Stage 1 — Intent: {intent_result.intent_score}/10 → {intent_result.intent_stage.value}")

    return {
        "company_profile": enrichment_result,
        "persona": persona_result,
        "intent": intent_result,
        "errors": [],
        "reasoning_trace": trace,
    }


# ── Stage 2 (parallel via asyncio.gather) ─────────────────────────────────────

async def stage2_node(state: PipelineState) -> dict:
    """TechStack + Signals + Leadership concurrently. Progress: 0.50 → 0.80."""
    job_id: str = state.get("job_id", "")
    await _update_progress(job_id, 0.55, "Detecting tech stack and business signals")

    agents = _build_agents()
    profile = state.get("company_profile")

    if not profile:
        return {"errors": ["stage2_node: no company_profile"], "reasoning_trace": []}

    async def run_tech():
        try:
            return await agents["tech_stack"].run(profile)
        except Exception as exc:
            logger.error("tech_stack error: %s", exc)
            return None

    async def run_signals():
        try:
            return await agents["signals"].run(profile)
        except Exception as exc:
            logger.error("signals error: %s", exc)
            return None

    async def run_leadership():
        try:
            return await agents["leadership"].run(profile)
        except Exception as exc:
            logger.error("leadership error: %s", exc)
            return None

    tech_result, signals_result, leadership_result = await asyncio.gather(
        run_tech(), run_signals(), run_leadership()
    )

    await _update_progress(job_id, 0.80, "Building sales playbook")

    trace: list[str] = []
    if tech_result:
        trace.append(f"Stage 2 — Tech stack: {len(tech_result.technologies)} technologies detected")
    if signals_result:
        trace.append(f"Stage 2 — Signals: {len(signals_result.signals)} business signals found")
    if leadership_result:
        trace.append(f"Stage 2 — Leadership: {len(leadership_result.leaders)} contacts discovered")

    return {
        "tech_stack": tech_result,
        "business_signals": signals_result,
        "leadership": leadership_result,
        "errors": [],
        "reasoning_trace": trace,
    }


# ── Stage 3a — Playbook ────────────────────────────────────────────────────────

async def playbook_node(state: PipelineState) -> dict:
    """Synthesise sales playbook from assembled intelligence. Progress: 0.80 → 0.90."""
    job_id: str = state.get("job_id", "")
    await _update_progress(job_id, 0.82, "Generating sales playbook")

    agents = _build_agents()
    profile = state.get("company_profile")
    if not profile:
        return {"errors": ["playbook_node: no company_profile"], "reasoning_trace": []}

    from backend.domain.intelligence import AccountIntelligence
    assembled = AccountIntelligence(
        company=profile,
        persona=state.get("persona"),
        intent=state.get("intent"),
        tech_stack=state.get("tech_stack"),
        business_signals=state.get("business_signals"),
        leadership=state.get("leadership"),
    )

    try:
        result = await agents["playbook"].run(assembled)
        await _update_progress(job_id, 0.90, "Writing AI summary")
        return {
            "playbook": result,
            "errors": [],
            "reasoning_trace": [f"Stage 3 — Playbook: priority={result.priority.value}, {len(result.recommended_actions)} actions"],
        }
    except Exception as exc:
        logger.error("playbook_node error: %s", exc)
        return {"errors": [f"playbook_node: {exc}"], "reasoning_trace": []}


# ── Stage 3b — Summary ─────────────────────────────────────────────────────────

async def summary_node(state: PipelineState) -> dict:
    """Generate narrative + assemble final AccountIntelligence. Progress: 0.90 → 1.0."""
    job_id: str = state.get("job_id", "")
    await _update_progress(job_id, 0.92, "Writing AI intelligence summary")

    agents = _build_agents()
    profile = state.get("company_profile")
    if not profile:
        return {"errors": ["summary_node: no company_profile"], "reasoning_trace": []}

    from backend.domain.intelligence import AccountIntelligence
    assembled = AccountIntelligence(
        company=profile,
        persona=state.get("persona"),
        intent=state.get("intent"),
        tech_stack=state.get("tech_stack"),
        business_signals=state.get("business_signals"),
        leadership=state.get("leadership"),
        playbook=state.get("playbook"),
        reasoning_trace=list(state.get("reasoning_trace", [])),
    )

    try:
        result = await agents["summary"].run(assembled)
        await _update_progress(job_id, 0.98, "Finalising")
        return {
            "intelligence": result,
            "errors": [],
            "reasoning_trace": ["Stage 3 — Summary complete"],
        }
    except Exception as exc:
        logger.error("summary_node error: %s", exc)
        return {"intelligence": assembled, "errors": [f"summary_node: {exc}"], "reasoning_trace": []}
