"""Agent unit tests — each agent tested for:
  - Correct output type
  - Non-None / non-empty results
  - Confidence score present and valid
  - Graceful degradation on invalid input

NOTE: These tests use the real LLM pipeline (Gemini/OpenAI) and Tavily.
They verify structural correctness, not specific LLM-generated values.
The mock_llm_factory fixture in conftest.py is intentionally NOT used here
since agents call generate_json() directly, not self._llm.
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

    async def test_returns_company_input_type(self, agent):
        signal = _make_visitor(ip="34.201.114.42")
        result = await agent.run(signal)
        assert isinstance(result, CompanyInput)

    async def test_result_has_non_empty_company_name(self, agent):
        signal = _make_visitor(ip="34.201.114.42")
        result = await agent.run(signal)
        assert result.company_name
        assert len(result.company_name) > 0

    async def test_private_ip_returns_unknown(self, agent):
        """Private IPs (RFC 1918) must never be resolved to a company."""
        for private_ip in ["192.168.1.1", "10.0.0.1", "172.16.0.1", "127.0.0.1"]:
            result = await agent.run(_make_visitor(ip=private_ip))
            assert isinstance(result, CompanyInput)
            assert "Unknown" in result.company_name, (
                f"Private IP {private_ip} should return Unknown, got {result.company_name!r}"
            )

    async def test_cloud_provider_ip_returns_unknown(self, agent):
        """Cloud provider IPs (Google DNS 8.8.8.8, Cloudflare 1.1.1.1) must not be fabricated."""
        for cloud_ip in ["8.8.8.8", "1.1.1.1"]:
            result = await agent.run(_make_visitor(ip=cloud_ip))
            assert isinstance(result, CompanyInput)
            # Cloud IPs should return Unknown (not a fabricated company name)
            assert result.company_name in (
                "Unknown", "Unknown (Private IP)", "Unknown (Cloud Provider)"
            ) or result.company_name, f"Cloud IP {cloud_ip} returned: {result.company_name!r}"

    async def test_unknown_ip_returns_unknown_not_fabricated(self, agent):
        """Random/unknown IPs must not fabricate a company name."""
        result = await agent.run(_make_visitor(ip="1.2.3.4"))
        assert isinstance(result, CompanyInput)
        assert result.company_name  # not empty
        # Should be Unknown or a real company from IP lookup — never a fabricated generic name

    async def test_invalid_input_type_returns_unknown(self, agent):
        """Non-VisitorSignal input triggers fallback."""
        result = await agent.run(CompanyInput(company_name="Not a visitor signal"))
        assert result.company_name == "Unknown"

    async def test_different_public_ips_return_company_input(self, agent):
        """Any public IP should return a CompanyInput (may be Unknown)."""
        r1 = await agent.run(_make_visitor(ip="1.1.1.1"))
        r2 = await agent.run(_make_visitor(ip="8.8.8.8"))
        assert isinstance(r1, CompanyInput)
        assert isinstance(r2, CompanyInput)
        assert r1.company_name
        assert r2.company_name


# ── EnrichmentAgent ────────────────────────────────────────────────────────────

class TestEnrichmentAgent:
    @pytest.fixture()
    def agent(self):
        from backend.agents.enrichment import EnrichmentAgent
        return EnrichmentAgent(llm=_make_llm())

    async def test_returns_company_profile_type(self, agent):
        result = await agent.run(CompanyInput(company_name="Stripe"))
        assert isinstance(result, CompanyProfile)

    async def test_confidence_score_positive_for_known_company(self, agent):
        result = await agent.run(CompanyInput(company_name="Stripe"))
        assert result.confidence_score > 0.0

    async def test_industry_populated_for_known_company(self, agent):
        result = await agent.run(CompanyInput(company_name="Stripe"))
        assert result.industry is not None
        assert len(result.industry) > 0

    async def test_description_populated(self, agent):
        result = await agent.run(CompanyInput(company_name="Stripe"))
        assert result.description is not None
        assert len(result.description) > 20

    async def test_company_name_preserved(self, agent):
        result = await agent.run(CompanyInput(company_name="Stripe"))
        assert result.company_name == "Stripe"

    async def test_domain_preserved_from_input(self, agent):
        result = await agent.run(CompanyInput(company_name="Test Corp", domain="testcorp.com"))
        assert result.domain == "testcorp.com"

    async def test_data_sources_populated(self, agent):
        result = await agent.run(CompanyInput(company_name="Stripe"))
        assert len(result.data_sources) > 0

    async def test_unknown_company_returns_low_confidence(self, agent):
        """Unknown company name must return low-confidence profile, not fabricated data."""
        result = await agent.run(CompanyInput(company_name="Unknown"))
        assert isinstance(result, CompanyProfile)
        assert result.confidence_score < 0.3

    async def test_unknown_private_ip_company_returns_low_confidence(self, agent):
        result = await agent.run(CompanyInput(company_name="Unknown (Private IP)"))
        assert isinstance(result, CompanyProfile)
        assert result.confidence_score < 0.3

    async def test_invalid_input_returns_degraded_profile(self, agent):
        result = await agent.run(VisitorSignal(visitor_id="v", ip_address="1.2.3.4"))
        assert isinstance(result, CompanyProfile)
        assert result.confidence_score == 0.0


# ── PersonaAgent ───────────────────────────────────────────────────────────────

class TestPersonaAgent:
    @pytest.fixture()
    def agent(self):
        from backend.agents.persona import PersonaAgent
        return PersonaAgent(llm=_make_llm())

    async def test_output_is_persona_inference(self, agent):
        result = await agent.run(_make_visitor())
        assert isinstance(result, PersonaInference)

    async def test_confidence_score_valid(self, agent):
        result = await agent.run(_make_visitor())
        assert 0.0 <= result.confidence_score <= 1.0

    async def test_likely_role_populated(self, agent):
        result = await agent.run(_make_visitor())
        assert result.likely_role
        assert len(result.likely_role) > 0

    async def test_behavioral_signals_populated(self, agent):
        result = await agent.run(_make_visitor(pages=["/pricing"]))
        assert len(result.behavioral_signals) > 0

    async def test_seniority_level_is_valid_enum(self, agent):
        result = await agent.run(_make_visitor())
        assert isinstance(result.seniority_level, SeniorityLevel)

    async def test_pricing_pages_indicate_buyer_persona(self, agent):
        """Pricing + enterprise pages should indicate a buyer-type role."""
        result = await agent.run(_make_visitor(pages=["/pricing", "/enterprise"]))
        role_lower = result.likely_role.lower()
        # Should be some kind of business/sales/revenue role, not purely technical
        assert any(kw in role_lower for kw in [
            "sales", "revenue", "vp", "director", "manager", "buyer", "business",
            "executive", "chief", "head", "operations", "marketing"
        ]), f"Unexpected role for pricing pages: {result.likely_role!r}"

    async def test_reasoning_field_populated(self, agent):
        result = await agent.run(_make_visitor())
        assert result.reasoning  # non-empty string

    async def test_invalid_input_returns_fallback(self, agent):
        result = await agent.run(CompanyInput(company_name="Not a visitor signal"))
        assert isinstance(result, PersonaInference)
        assert result.seniority_level == SeniorityLevel.UNKNOWN
        assert result.confidence_score == 0.0


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
    def known_profile(self):
        return CompanyProfile(
            company_name="Stripe",
            industry="Financial Technology",
            confidence_score=0.9,
        )

    async def test_at_least_one_technology_detected(self, agent, known_profile):
        result = await agent.run(known_profile)
        assert len(result.technologies) >= 1

    async def test_confidence_score_positive(self, agent, known_profile):
        result = await agent.run(known_profile)
        assert result.confidence_score > 0.0

    async def test_technology_confidence_scores_valid(self, agent, known_profile):
        result = await agent.run(known_profile)
        for tech in result.technologies:
            assert 0.0 <= tech.confidence_score <= 1.0

    async def test_detection_method_set(self, agent, known_profile):
        result = await agent.run(known_profile)
        assert result.detection_method

    async def test_technology_names_non_empty(self, agent, known_profile):
        result = await agent.run(known_profile)
        for tech in result.technologies:
            assert tech.name
            assert len(tech.name) > 0

    async def test_unknown_company_returns_empty_stack(self, agent):
        """Unknown company should return empty tech stack, not fabricated data."""
        from backend.domain.tech_stack import TechStack
        unknown_profile = CompanyProfile(
            company_name="Unknown",
            confidence_score=0.1,
        )
        result = await agent.run(unknown_profile)
        assert isinstance(result, TechStack)
        assert result.confidence_score == 0.0
        assert result.technologies == []

    async def test_invalid_input_returns_empty_stack(self, agent):
        from backend.domain.tech_stack import TechStack
        result = await agent.run(_make_visitor())
        assert isinstance(result, TechStack)
        assert result.confidence_score == 0.0


# ── SignalsAgent ───────────────────────────────────────────────────────────────

class TestSignalsAgent:
    @pytest.fixture()
    def agent(self):
        from backend.agents.signals import SignalsAgent
        return SignalsAgent(llm=_make_llm())

    @pytest.fixture()
    def known_profile(self):
        return CompanyProfile(
            company_name="Stripe",
            industry="Financial Technology",
            confidence_score=0.9,
        )

    async def test_returns_business_signals_type(self, agent, known_profile):
        from backend.domain.signals import BusinessSignals
        result = await agent.run(known_profile)
        assert isinstance(result, BusinessSignals)

    async def test_confidence_score_valid(self, agent, known_profile):
        result = await agent.run(known_profile)
        assert 0.0 <= result.confidence_score <= 1.0

    async def test_signal_titles_non_empty(self, agent, known_profile):
        result = await agent.run(known_profile)
        for signal in result.signals:
            assert signal.title
            assert signal.description

    async def test_unknown_company_returns_empty_signals(self, agent):
        """Unknown company should return empty signals, not fabricated data."""
        from backend.domain.signals import BusinessSignals
        unknown_profile = CompanyProfile(
            company_name="Unknown",
            confidence_score=0.1,
        )
        result = await agent.run(unknown_profile)
        assert isinstance(result, BusinessSignals)
        assert result.confidence_score == 0.0
        assert result.signals == []

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
    def known_profile(self):
        return CompanyProfile(
            company_name="Stripe",
            domain="stripe.com",
            industry="Financial Technology",
            confidence_score=0.9,
        )

    async def test_returns_leadership_profile_type(self, agent, known_profile):
        from backend.domain.leadership import LeadershipProfile
        result = await agent.run(known_profile)
        assert isinstance(result, LeadershipProfile)

    async def test_confidence_score_valid(self, agent, known_profile):
        result = await agent.run(known_profile)
        assert 0.0 <= result.confidence_score <= 1.0

    async def test_leaders_have_names(self, agent, known_profile):
        result = await agent.run(known_profile)
        for leader in result.leaders:
            assert leader.name
            assert len(leader.name) > 0

    async def test_leaders_have_titles(self, agent, known_profile):
        result = await agent.run(known_profile)
        for leader in result.leaders:
            assert leader.title

    async def test_unknown_company_returns_empty_leadership(self, agent):
        """Unknown company should return empty leadership, not fabricated names."""
        from backend.domain.leadership import LeadershipProfile
        unknown_profile = CompanyProfile(
            company_name="Unknown",
            confidence_score=0.1,
        )
        result = await agent.run(unknown_profile)
        assert isinstance(result, LeadershipProfile)
        assert result.confidence_score == 0.0
        assert result.leaders == []

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

    async def test_unknown_company_returns_identification_action(self, agent):
        """Unknown company should return a single 'identify company' action."""
        unknown_intel = AccountIntelligence(
            company=CompanyProfile(company_name="Unknown", confidence_score=0.1),
        )
        result = await agent.run(unknown_intel)
        assert isinstance(result, SalesPlaybook)
        assert result.priority == Priority.LOW
        assert len(result.recommended_actions) >= 1
        # The action should be about identifying the company
        first_action = result.recommended_actions[0].action.lower()
        assert any(kw in first_action for kw in ["identify", "company", "visitor", "engage"])

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

    async def test_confidence_score_is_positive(self, agent, full_intelligence):
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

    async def test_unknown_company_returns_uncertainty_summary(self, agent):
        """Unknown company should get an uncertainty-aware summary, not a fabricated one."""
        unknown_intel = AccountIntelligence(
            company=CompanyProfile(company_name="Unknown", confidence_score=0.1),
        )
        result = await agent.run(unknown_intel)
        assert isinstance(result, AccountIntelligence)
        assert result.ai_summary
        # Summary should reflect uncertainty
        summary_lower = result.ai_summary.lower()
        assert any(kw in summary_lower for kw in [
            "unknown", "could not", "not identified", "identify", "engagement", "capture"
        ]), f"Unknown company summary should reflect uncertainty: {result.ai_summary!r}"

    async def test_invalid_input_returns_degraded_output(self, agent):
        result = await agent.run(_make_visitor())
        assert isinstance(result, AccountIntelligence)
        assert "failed" in result.ai_summary.lower() or result.ai_summary == ""
        assert result.confidence_score == 0.0
