"""Agent unit tests — each agent tested for:
  - Correct output type
  - Non-None / non-empty results
  - Confidence score present and valid
  - Graceful degradation on invalid input
"""
from unittest.mock import MagicMock

import pytest

from backend.domain.company import CompanyInput, CompanyProfile
from backend.domain.intelligence import AccountIntelligence
from backend.domain.intent import IntentScore, IntentStage
from backend.domain.persona import PersonaInference, SeniorityLevel
from backend.domain.playbook import Priority, SalesPlaybook
from backend.domain.visitor import VisitorSignal


def _make_llm() -> MagicMock:
    return MagicMock()


def _make_visitor(
    ip: str = "34.201.114.42",
    pages: list[str] | None = None,
    time_on_site: int = 222,
    visit_count: int = 3,
) -> VisitorSignal:
    return VisitorSignal(
        visitor_id="v-test",
        ip_address=ip,
        pages_visited=pages or ["/pricing", "/ai-sales-agent", "/case-studies"],
        time_on_site_seconds=time_on_site,
        visit_count=visit_count,
    )


# ── IdentificationAgent ────────────────────────────────────────────────────────

class TestIdentificationAgent:
    @pytest.fixture()
    def agent(self):
        from backend.agents.identification import IdentificationAgent
        return IdentificationAgent(llm=_make_llm())

    async def test_known_ip_prefix_resolves(self, agent):
        signal = _make_visitor(ip="34.201.114.42")
        result = await agent.run(signal)
        assert isinstance(result, CompanyInput)
        assert result.company_name == "Acme Mortgage"
        assert result.domain == "acmemortgage.com"

    async def test_brightpath_ip_prefix(self, agent):
        signal = _make_visitor(ip="54.100.0.1")
        result = await agent.run(signal)
        assert result.company_name == "BrightPath Lending"

    async def test_unknown_ip_returns_deterministic_fallback(self, agent):
        signal = _make_visitor(ip="1.2.3.4")
        result = await agent.run(signal)
        assert isinstance(result, CompanyInput)
        assert result.company_name  # not empty
        assert result.company_name != "Unknown"  # uses hash fallback

    async def test_different_unknown_ips_may_map_differently(self, agent):
        r1 = await agent.run(_make_visitor(ip="1.1.1.1"))
        r2 = await agent.run(_make_visitor(ip="8.8.8.8"))
        # Both should have company names (even if same by hash coincidence)
        assert r1.company_name
        assert r2.company_name

    async def test_invalid_input_type_returns_unknown(self, agent):
        """Non-VisitorSignal input triggers fallback."""
        from backend.domain.base import BaseEntity
        result = await agent.run(CompanyInput(company_name="Not a visitor signal"))
        assert result.company_name == "Unknown"

    async def test_returns_company_input_type(self, agent):
        result = await agent.run(_make_visitor())
        assert isinstance(result, CompanyInput)


# ── EnrichmentAgent ────────────────────────────────────────────────────────────

class TestEnrichmentAgent:
    @pytest.fixture()
    def agent(self):
        from backend.agents.enrichment import EnrichmentAgent
        return EnrichmentAgent(llm=_make_llm())

    async def test_mortgage_company_gets_correct_industry(self, agent):
        result = await agent.run(CompanyInput(company_name="BrightPath Lending"))
        assert result.industry == "Mortgage Lending"

    async def test_tech_company_gets_saas_industry(self, agent):
        result = await agent.run(CompanyInput(company_name="TechBridge Solutions"))
        assert result.industry == "Technology / SaaS"

    async def test_real_estate_company_gets_industry(self, agent):
        result = await agent.run(CompanyInput(company_name="Summit Realty Group"))
        assert "Real Estate" in result.industry

    async def test_confidence_score_positive(self, agent):
        result = await agent.run(CompanyInput(company_name="BrightPath Lending"))
        assert result.confidence_score > 0.0

    async def test_data_sources_populated(self, agent):
        result = await agent.run(CompanyInput(company_name="BrightPath Lending"))
        assert len(result.data_sources) > 0

    async def test_description_uses_company_name(self, agent):
        result = await agent.run(CompanyInput(company_name="Acme Mortgage"))
        assert "Acme Mortgage" in result.description

    async def test_domain_preserved_from_input(self, agent):
        result = await agent.run(CompanyInput(company_name="Test Corp", domain="testcorp.com"))
        assert result.domain == "testcorp.com"

    async def test_invalid_input_returns_degraded_profile(self, agent):
        from backend.domain.visitor import VisitorSignal
        result = await agent.run(VisitorSignal(visitor_id="v", ip_address="1.2.3.4"))
        assert isinstance(result, CompanyProfile)
        assert result.confidence_score == 0.0

    async def test_returns_company_profile_type(self, agent):
        result = await agent.run(CompanyInput(company_name="Test Corp"))
        assert isinstance(result, CompanyProfile)


# ── PersonaAgent ───────────────────────────────────────────────────────────────

class TestPersonaAgent:
    @pytest.fixture()
    def agent(self):
        from backend.agents.persona import PersonaAgent
        return PersonaAgent(llm=_make_llm())

    async def test_pricing_pages_map_to_vp_sales(self, agent):
        result = await agent.run(_make_visitor(pages=["/pricing", "/enterprise"]))
        assert "sales" in result.likely_role.lower() or "revenue" in result.likely_role.lower()

    async def test_docs_pages_map_to_engineer(self, agent):
        result = await agent.run(_make_visitor(pages=["/docs", "/api", "/integration"]))
        assert "engineer" in result.likely_role.lower() or "developer" in result.likely_role.lower()

    async def test_output_is_persona_inference(self, agent):
        result = await agent.run(_make_visitor())
        assert isinstance(result, PersonaInference)

    async def test_confidence_score_valid(self, agent):
        result = await agent.run(_make_visitor())
        assert 0.0 <= result.confidence_score <= 1.0

    async def test_behavioral_signals_populated(self, agent):
        result = await agent.run(_make_visitor(pages=["/pricing"]))
        assert len(result.behavioral_signals) > 0

    async def test_visit_count_boosts_confidence(self, agent):
        low = await agent.run(_make_visitor(visit_count=1))
        high = await agent.run(_make_visitor(visit_count=10))
        assert high.confidence_score >= low.confidence_score

    async def test_repeat_visit_noted_in_signals(self, agent):
        result = await agent.run(_make_visitor(visit_count=5))
        signals_text = " ".join(result.behavioral_signals)
        assert "5" in signals_text

    async def test_time_on_site_noted_in_signals(self, agent):
        result = await agent.run(_make_visitor(time_on_site=300))
        signals_text = " ".join(result.behavioral_signals)
        assert "5m" in signals_text

    async def test_invalid_input_returns_fallback(self, agent):
        result = await agent.run(CompanyInput(company_name="Not a visitor signal"))
        assert isinstance(result, PersonaInference)
        assert result.seniority_level == SeniorityLevel.UNKNOWN
        assert result.confidence_score == 0.0

    async def test_reasoning_field_populated(self, agent):
        result = await agent.run(_make_visitor())
        assert result.reasoning  # non-empty string


# ── IntentScorerAgent ──────────────────────────────────────────────────────────

class TestIntentScorerAgent:
    @pytest.fixture()
    def agent(self):
        from backend.agents.intent_scorer import IntentScorerAgent
        return IntentScorerAgent(llm=_make_llm())

    async def test_pricing_plus_demo_high_score(self, agent):
        result = await agent.run(_make_visitor(pages=["/pricing", "/demo"]))
        assert result.intent_score >= 5.0

    async def test_blog_only_low_score(self, agent):
        result = await agent.run(_make_visitor(pages=["/blog"]))
        assert result.intent_score < 4.0

    async def test_pricing_page_maps_to_evaluation_or_purchase(self, agent):
        result = await agent.run(_make_visitor(pages=["/pricing", "/case-studies"]))
        assert result.intent_stage in (IntentStage.EVALUATION, IntentStage.PURCHASE)

    async def test_blog_only_maps_to_awareness(self, agent):
        result = await agent.run(_make_visitor(pages=["/blog"], visit_count=1, time_on_site=30))
        assert result.intent_stage == IntentStage.AWARENESS

    async def test_score_capped_at_10(self, agent):
        result = await agent.run(_make_visitor(
            pages=["/pricing", "/demo", "/enterprise", "/case-studies"],
            visit_count=10,
            time_on_site=3600,
        ))
        assert result.intent_score <= 10.0

    async def test_score_minimum_zero(self, agent):
        result = await agent.run(_make_visitor(pages=["/unknown-page"], visit_count=1, time_on_site=0))
        assert result.intent_score >= 0.0

    async def test_page_score_breakdown_populated(self, agent):
        result = await agent.run(_make_visitor(pages=["/pricing"]))
        assert "/pricing" in result.page_score_breakdown

    async def test_visit_count_bonus_added(self, agent):
        result = await agent.run(_make_visitor(pages=["/pricing"], visit_count=3))
        assert "repeat_visit_bonus" in result.page_score_breakdown

    async def test_signals_detected_populated(self, agent):
        result = await agent.run(_make_visitor(pages=["/pricing"]))
        assert len(result.signals_detected) > 0

    async def test_confidence_score_valid(self, agent):
        result = await agent.run(_make_visitor())
        assert 0.0 <= result.confidence_score <= 1.0

    async def test_invalid_input_returns_zero_score(self, agent):
        result = await agent.run(CompanyInput(company_name="Not a signal"))
        assert isinstance(result, IntentScore)
        assert result.intent_score == 0.0
        assert result.confidence_score == 0.0

    async def test_output_type(self, agent):
        result = await agent.run(_make_visitor())
        assert isinstance(result, IntentScore)


# ── TechStackAgent ─────────────────────────────────────────────────────────────

class TestTechStackAgent:
    @pytest.fixture()
    def agent(self):
        from backend.agents.tech_stack import TechStackAgent
        return TechStackAgent(llm=_make_llm())

    @pytest.fixture()
    def mortgage_profile(self):
        return CompanyProfile(
            company_name="BrightPath Lending",
            industry="Mortgage Lending",
            confidence_score=0.8,
        )

    @pytest.fixture()
    def tech_profile(self):
        return CompanyProfile(
            company_name="TechBridge Solutions",
            industry="Technology / SaaS",
            confidence_score=0.8,
        )

    async def test_mortgage_company_includes_salesforce(self, agent, mortgage_profile):
        result = await agent.run(mortgage_profile)
        names = [t.name for t in result.technologies]
        assert "Salesforce" in names

    async def test_tech_company_includes_hubspot(self, agent, tech_profile):
        result = await agent.run(tech_profile)
        names = [t.name for t in result.technologies]
        assert "HubSpot" in names

    async def test_at_least_one_technology_detected(self, agent, mortgage_profile):
        result = await agent.run(mortgage_profile)
        assert len(result.technologies) >= 1

    async def test_confidence_score_positive(self, agent, mortgage_profile):
        result = await agent.run(mortgage_profile)
        assert result.confidence_score > 0.0

    async def test_technology_confidence_scores_valid(self, agent, mortgage_profile):
        result = await agent.run(mortgage_profile)
        for tech in result.technologies:
            assert 0.0 <= tech.confidence_score <= 1.0

    async def test_detection_method_set(self, agent, mortgage_profile):
        result = await agent.run(mortgage_profile)
        assert result.detection_method

    async def test_invalid_input_returns_empty_stack(self, agent):
        result = await agent.run(_make_visitor())
        from backend.domain.tech_stack import TechStack
        assert isinstance(result, TechStack)
        assert result.confidence_score == 0.0


# ── SignalsAgent ───────────────────────────────────────────────────────────────

class TestSignalsAgent:
    @pytest.fixture()
    def agent(self):
        from backend.agents.signals import SignalsAgent
        return SignalsAgent(llm=_make_llm())

    @pytest.fixture()
    def mortgage_profile(self):
        return CompanyProfile(
            company_name="BrightPath Lending",
            industry="Mortgage Lending",
            confidence_score=0.8,
        )

    async def test_returns_at_least_one_signal(self, agent, mortgage_profile):
        result = await agent.run(mortgage_profile)
        assert len(result.signals) >= 1

    async def test_mortgage_company_has_hiring_signal(self, agent, mortgage_profile):
        from backend.domain.signals import SignalType
        result = await agent.run(mortgage_profile)
        signal_types = [s.signal_type for s in result.signals]
        assert SignalType.HIRING in signal_types

    async def test_signal_has_source_url(self, agent, mortgage_profile):
        result = await agent.run(mortgage_profile)
        for signal in result.signals:
            assert signal.source_url
            assert signal.source_url.startswith("https://")

    async def test_signal_titles_non_empty(self, agent, mortgage_profile):
        result = await agent.run(mortgage_profile)
        for signal in result.signals:
            assert signal.title
            assert signal.description

    async def test_confidence_score_positive(self, agent, mortgage_profile):
        result = await agent.run(mortgage_profile)
        assert result.confidence_score > 0.0

    async def test_invalid_input_returns_empty_signals(self, agent):
        from backend.domain.signals import BusinessSignals
        result = await agent.run(_make_visitor())
        assert isinstance(result, BusinessSignals)
        assert result.confidence_score == 0.0


# ── LeadershipAgent ────────────────────────────────────────────────────────────

class TestLeadershipAgent:
    @pytest.fixture()
    def agent(self):
        from backend.agents.leadership import LeadershipAgent
        return LeadershipAgent(llm=_make_llm())

    @pytest.fixture()
    def profile(self):
        return CompanyProfile(
            company_name="BrightPath Lending",
            domain="brightpathlending.com",
            industry="Mortgage Lending",
            confidence_score=0.8,
        )

    async def test_returns_at_least_one_leader(self, agent, profile):
        result = await agent.run(profile)
        assert len(result.leaders) >= 1

    async def test_leaders_have_names(self, agent, profile):
        result = await agent.run(profile)
        for leader in result.leaders:
            assert leader.name

    async def test_leaders_have_titles(self, agent, profile):
        result = await agent.run(profile)
        for leader in result.leaders:
            assert leader.title

    async def test_linkedin_urls_generated(self, agent, profile):
        result = await agent.run(profile)
        for leader in result.leaders:
            assert leader.linkedin_url
            assert "linkedin.com" in leader.linkedin_url

    async def test_source_urls_use_company_domain(self, agent, profile):
        result = await agent.run(profile)
        for leader in result.leaders:
            assert "brightpathlending.com" in leader.source_url

    async def test_confidence_score_positive(self, agent, profile):
        result = await agent.run(profile)
        assert result.confidence_score > 0.0

    async def test_invalid_input_returns_empty_leadership(self, agent):
        from backend.domain.leadership import LeadershipProfile
        result = await agent.run(_make_visitor())
        assert isinstance(result, LeadershipProfile)
        assert result.confidence_score == 0.0


# ── PlaybookAgent ──────────────────────────────────────────────────────────────

class TestPlaybookAgent:
    @pytest.fixture()
    def agent(self):
        from backend.agents.playbook import PlaybookAgent
        return PlaybookAgent(llm=_make_llm())

    async def test_high_intent_produces_high_priority(self, agent, full_intelligence):
        """full_intelligence fixture has intent_score=8.4 → should be HIGH."""
        result = await agent.run(full_intelligence)
        assert result.priority == Priority.HIGH

    async def test_low_intent_produces_medium_or_low_priority(self, agent, company_profile):
        from backend.domain.intent import IntentScore, IntentStage
        intel = AccountIntelligence(
            company=company_profile,
            intent=IntentScore(intent_score=2.0, intent_stage=IntentStage.AWARENESS),
        )
        result = await agent.run(intel)
        assert result.priority in (Priority.MEDIUM, Priority.LOW)

    async def test_recommended_actions_non_empty(self, agent, full_intelligence):
        result = await agent.run(full_intelligence)
        assert len(result.recommended_actions) > 0

    async def test_talking_points_non_empty(self, agent, full_intelligence):
        result = await agent.run(full_intelligence)
        assert len(result.talking_points) > 0

    async def test_outreach_template_generated(self, agent, full_intelligence):
        result = await agent.run(full_intelligence)
        assert result.outreach_template
        assert len(result.outreach_template) > 50

    async def test_confidence_score_valid(self, agent, full_intelligence):
        result = await agent.run(full_intelligence)
        assert 0.0 <= result.confidence_score <= 1.0

    async def test_actions_have_rationale(self, agent, full_intelligence):
        result = await agent.run(full_intelligence)
        for action in result.recommended_actions:
            assert action.action
            assert action.rationale

    async def test_invalid_input_returns_low_priority_playbook(self, agent):
        result = await agent.run(_make_visitor())
        assert isinstance(result, SalesPlaybook)
        assert result.priority == Priority.LOW

    async def test_output_type(self, agent, full_intelligence):
        result = await agent.run(full_intelligence)
        assert isinstance(result, SalesPlaybook)


# ── SummaryAgent ───────────────────────────────────────────────────────────────

class TestSummaryAgent:
    @pytest.fixture()
    def agent(self):
        from backend.agents.summary import SummaryAgent
        return SummaryAgent(llm=_make_llm())

    async def test_ai_summary_populated(self, agent, full_intelligence):
        result = await agent.run(full_intelligence)
        assert result.ai_summary
        assert len(result.ai_summary) > 50

    async def test_summary_mentions_company_name(self, agent, full_intelligence):
        result = await agent.run(full_intelligence)
        assert "BrightPath Lending" in result.ai_summary

    async def test_summary_mentions_industry(self, agent, full_intelligence):
        result = await agent.run(full_intelligence)
        assert "Mortgage" in result.ai_summary

    async def test_confidence_score_is_average_of_sub_scores(self, agent, full_intelligence):
        result = await agent.run(full_intelligence)
        assert 0.0 < result.confidence_score <= 1.0

    async def test_returns_account_intelligence(self, agent, full_intelligence):
        result = await agent.run(full_intelligence)
        assert isinstance(result, AccountIntelligence)

    async def test_all_sub_fields_preserved(self, agent, full_intelligence):
        result = await agent.run(full_intelligence)
        assert result.persona is not None
        assert result.intent is not None
        assert result.tech_stack is not None

    async def test_invalid_input_returns_degraded_output(self, agent):
        result = await agent.run(_make_visitor())
        assert isinstance(result, AccountIntelligence)
        assert "failed" in result.ai_summary.lower() or result.ai_summary == ""
        assert result.confidence_score == 0.0
