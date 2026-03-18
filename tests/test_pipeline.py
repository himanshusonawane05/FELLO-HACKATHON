"""Pipeline integration tests — full LangGraph workflow execution.

These tests invoke `compiled_workflow.ainvoke()` directly, bypassing HTTP
and the controller, to verify stage transitions and output integrity.
"""
import pytest

from backend.domain.company import CompanyInput
from backend.domain.intelligence import AccountIntelligence
from backend.domain.visitor import VisitorSignal
from backend.graph.workflow import compiled_workflow


def _make_initial_state(
    visitor_signal: VisitorSignal | None = None,
    company_input: CompanyInput | None = None,
    job_id: str = "test-pipe-001",
) -> dict:
    return {
        "visitor_signal": visitor_signal,
        "company_input": company_input,
        "identified_company": None,
        "company_profile": None,
        "persona": None,
        "intent": None,
        "tech_stack": None,
        "business_signals": None,
        "leadership": None,
        "playbook": None,
        "intelligence": None,
        "job_id": job_id,
        "errors": [],
        "reasoning_trace": [],
    }


# ── Company input path (no identification stage) ───────────────────────────────

class TestCompanyPipeline:
    async def test_produces_intelligence(self):
        state = _make_initial_state(
            company_input=CompanyInput(company_name="BrightPath Lending", domain="brightpathlending.com")
        )
        result = await compiled_workflow.ainvoke(state)
        assert result.get("intelligence") is not None

    async def test_output_is_account_intelligence(self):
        state = _make_initial_state(
            company_input=CompanyInput(company_name="Acme Mortgage")
        )
        result = await compiled_workflow.ainvoke(state)
        intel = result["intelligence"]
        assert isinstance(intel, AccountIntelligence)

    async def test_company_profile_populated(self):
        state = _make_initial_state(
            company_input=CompanyInput(company_name="BrightPath Lending")
        )
        result = await compiled_workflow.ainvoke(state)
        intel: AccountIntelligence = result["intelligence"]
        assert intel.company.company_name == "BrightPath Lending"
        assert intel.company.industry is not None
        assert intel.company.confidence_score > 0.0

    async def test_tech_stack_detected(self):
        state = _make_initial_state(
            company_input=CompanyInput(company_name="BrightPath Lending")
        )
        result = await compiled_workflow.ainvoke(state)
        intel: AccountIntelligence = result["intelligence"]
        assert intel.tech_stack is not None
        assert len(intel.tech_stack.technologies) > 0

    async def test_business_signals_found(self):
        state = _make_initial_state(
            company_input=CompanyInput(company_name="BrightPath Lending")
        )
        result = await compiled_workflow.ainvoke(state)
        intel: AccountIntelligence = result["intelligence"]
        assert intel.business_signals is not None
        assert len(intel.business_signals.signals) > 0

    async def test_leadership_discovered(self):
        state = _make_initial_state(
            company_input=CompanyInput(company_name="BrightPath Lending")
        )
        result = await compiled_workflow.ainvoke(state)
        intel: AccountIntelligence = result["intelligence"]
        assert intel.leadership is not None
        assert len(intel.leadership.leaders) > 0

    async def test_playbook_generated(self):
        state = _make_initial_state(
            company_input=CompanyInput(company_name="BrightPath Lending")
        )
        result = await compiled_workflow.ainvoke(state)
        intel: AccountIntelligence = result["intelligence"]
        assert intel.playbook is not None
        assert len(intel.playbook.recommended_actions) > 0

    async def test_ai_summary_populated(self):
        state = _make_initial_state(
            company_input=CompanyInput(company_name="BrightPath Lending")
        )
        result = await compiled_workflow.ainvoke(state)
        intel: AccountIntelligence = result["intelligence"]
        assert intel.ai_summary
        assert "BrightPath Lending" in intel.ai_summary

    async def test_confidence_score_valid(self):
        state = _make_initial_state(
            company_input=CompanyInput(company_name="BrightPath Lending")
        )
        result = await compiled_workflow.ainvoke(state)
        intel: AccountIntelligence = result["intelligence"]
        assert 0.0 < intel.confidence_score <= 1.0

    async def test_no_errors_in_result(self):
        state = _make_initial_state(
            company_input=CompanyInput(company_name="BrightPath Lending")
        )
        result = await compiled_workflow.ainvoke(state)
        assert result.get("errors") == []

    async def test_reasoning_trace_populated(self):
        state = _make_initial_state(
            company_input=CompanyInput(company_name="BrightPath Lending")
        )
        result = await compiled_workflow.ainvoke(state)
        intel: AccountIntelligence = result["intelligence"]
        assert len(intel.reasoning_trace) > 0

    async def test_persona_is_none_for_company_input(self):
        """Company-only requests have no visitor signal → persona should be None."""
        state = _make_initial_state(
            company_input=CompanyInput(company_name="BrightPath Lending")
        )
        result = await compiled_workflow.ainvoke(state)
        intel: AccountIntelligence = result["intelligence"]
        assert intel.persona is None

    async def test_intent_is_none_for_company_input(self):
        """Company-only requests have no visitor signal → intent should be None."""
        state = _make_initial_state(
            company_input=CompanyInput(company_name="BrightPath Lending")
        )
        result = await compiled_workflow.ainvoke(state)
        intel: AccountIntelligence = result["intelligence"]
        assert intel.intent is None

    async def test_different_companies_produce_different_industries(self):
        mortgage_state = _make_initial_state(
            company_input=CompanyInput(company_name="BrightPath Lending")
        )
        tech_state = _make_initial_state(
            company_input=CompanyInput(company_name="TechBridge Solutions")
        )
        r1 = await compiled_workflow.ainvoke(mortgage_state)
        r2 = await compiled_workflow.ainvoke(tech_state)
        assert r1["intelligence"].company.industry != r2["intelligence"].company.industry


# ── Visitor input path (with identification stage) ─────────────────────────────

class TestVisitorPipeline:
    async def test_produces_intelligence(self):
        signal = VisitorSignal(
            visitor_id="v-001",
            ip_address="34.201.114.42",
            pages_visited=["/pricing", "/ai-sales-agent", "/case-studies"],
            time_on_site_seconds=222,
            visit_count=3,
        )
        state = _make_initial_state(visitor_signal=signal)
        result = await compiled_workflow.ainvoke(state)
        assert result.get("intelligence") is not None

    async def test_visitor_identifies_company_from_ip(self):
        signal = VisitorSignal(
            visitor_id="v-001",
            ip_address="34.201.114.42",
            pages_visited=["/pricing"],
        )
        state = _make_initial_state(visitor_signal=signal)
        result = await compiled_workflow.ainvoke(state)
        intel: AccountIntelligence = result["intelligence"]
        assert intel.company.company_name == "Acme Mortgage"

    async def test_visitor_pipeline_has_persona(self):
        signal = VisitorSignal(
            visitor_id="v-001",
            ip_address="34.201.114.42",
            pages_visited=["/pricing", "/enterprise"],
            time_on_site_seconds=120,
            visit_count=2,
        )
        state = _make_initial_state(visitor_signal=signal)
        result = await compiled_workflow.ainvoke(state)
        intel: AccountIntelligence = result["intelligence"]
        assert intel.persona is not None
        assert intel.persona.likely_role

    async def test_visitor_pipeline_has_intent(self):
        signal = VisitorSignal(
            visitor_id="v-001",
            ip_address="34.201.114.42",
            pages_visited=["/pricing", "/demo"],
            time_on_site_seconds=200,
            visit_count=3,
        )
        state = _make_initial_state(visitor_signal=signal)
        result = await compiled_workflow.ainvoke(state)
        intel: AccountIntelligence = result["intelligence"]
        assert intel.intent is not None
        assert intel.intent.intent_score > 0.0

    async def test_high_intent_visitor_gets_high_priority_playbook(self):
        signal = VisitorSignal(
            visitor_id="v-001",
            ip_address="34.201.114.42",
            pages_visited=["/pricing", "/demo", "/enterprise"],
            time_on_site_seconds=400,
            visit_count=5,
        )
        state = _make_initial_state(visitor_signal=signal)
        result = await compiled_workflow.ainvoke(state)
        intel: AccountIntelligence = result["intelligence"]
        assert intel.playbook is not None
        assert intel.playbook.priority.value in ("HIGH", "MEDIUM")


# ── Edge cases ─────────────────────────────────────────────────────────────────

class TestPipelineEdgeCases:
    async def test_company_with_no_domain(self):
        state = _make_initial_state(
            company_input=CompanyInput(company_name="Mystery Corp")
        )
        result = await compiled_workflow.ainvoke(state)
        assert result.get("intelligence") is not None
        assert result["intelligence"].company.company_name == "Mystery Corp"

    async def test_visitor_with_empty_pages(self):
        """Empty pages_visited should not crash; score will be 0."""
        signal = VisitorSignal(
            visitor_id="v-empty",
            ip_address="34.0.0.1",
            pages_visited=[],
        )
        state = _make_initial_state(visitor_signal=signal)
        result = await compiled_workflow.ainvoke(state)
        assert result.get("intelligence") is not None

    async def test_visitor_with_single_page(self):
        signal = VisitorSignal(
            visitor_id="v-one",
            ip_address="54.0.0.1",
            pages_visited=["/about"],
        )
        state = _make_initial_state(visitor_signal=signal)
        result = await compiled_workflow.ainvoke(state)
        assert result.get("intelligence") is not None

    async def test_unknown_ip_still_produces_output(self):
        """Unrecognised IP → hash-based company → full pipeline should still run."""
        signal = VisitorSignal(
            visitor_id="v-anon",
            ip_address="1.2.3.4",
            pages_visited=["/pricing"],
        )
        state = _make_initial_state(visitor_signal=signal)
        result = await compiled_workflow.ainvoke(state)
        intel: AccountIntelligence = result["intelligence"]
        assert intel is not None
        assert intel.company.company_name  # not empty

    async def test_pipeline_is_idempotent_for_same_input(self):
        """Two identical inputs must produce structurally identical outputs."""
        company = CompanyInput(company_name="BrightPath Lending")
        s1 = _make_initial_state(company_input=company, job_id="job-A")
        s2 = _make_initial_state(company_input=company, job_id="job-B")
        r1 = await compiled_workflow.ainvoke(s1)
        r2 = await compiled_workflow.ainvoke(s2)
        assert r1["intelligence"].company.industry == r2["intelligence"].company.industry
        assert r1["intelligence"].company.company_name == r2["intelligence"].company.company_name
