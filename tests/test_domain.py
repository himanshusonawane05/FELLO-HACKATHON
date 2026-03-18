"""Domain model tests — Pydantic validation, immutability, constraints."""
import pytest
from pydantic import ValidationError

from backend.domain.base import BaseEntity
from backend.domain.company import CompanyInput, CompanyProfile
from backend.domain.intent import IntentScore, IntentStage
from backend.domain.intelligence import AccountIntelligence
from backend.domain.leadership import Leader, LeadershipProfile
from backend.domain.persona import PersonaInference, SeniorityLevel
from backend.domain.playbook import Priority, RecommendedAction, SalesPlaybook
from backend.domain.signals import BusinessSignals, Signal, SignalType
from backend.domain.tech_stack import TechCategory, TechStack, Technology
from backend.domain.visitor import VisitorSignal


# ── BaseEntity ─────────────────────────────────────────────────────────────────

class TestBaseEntity:
    def test_auto_generates_id(self):
        e = CompanyInput(company_name="Test")
        assert e.id
        assert len(e.id) == 36  # UUID format

    def test_auto_generates_created_at(self):
        e = CompanyInput(company_name="Test")
        assert e.created_at
        assert "T" in e.created_at  # ISO 8601

    def test_two_instances_have_different_ids(self):
        a = CompanyInput(company_name="Test")
        b = CompanyInput(company_name="Test")
        assert a.id != b.id

    def test_frozen_model_rejects_mutation(self):
        e = CompanyInput(company_name="Test")
        with pytest.raises(ValidationError):
            e.company_name = "Changed"  # type: ignore[misc]


# ── CompanyInput ───────────────────────────────────────────────────────────────

class TestCompanyInput:
    def test_minimal_construction(self):
        c = CompanyInput(company_name="Acme Corp")
        assert c.company_name == "Acme Corp"
        assert c.domain is None

    def test_with_domain(self):
        c = CompanyInput(company_name="Acme Corp", domain="acme.com")
        assert c.domain == "acme.com"

    def test_requires_company_name(self):
        with pytest.raises(ValidationError):
            CompanyInput()  # type: ignore[call-arg]


# ── CompanyProfile ─────────────────────────────────────────────────────────────

class TestCompanyProfile:
    def test_defaults(self):
        p = CompanyProfile(company_name="Test Co")
        assert p.confidence_score == 0.0
        assert p.data_sources == []
        assert p.reasoning_trace == []

    def test_confidence_score_bounds(self):
        with pytest.raises(ValidationError):
            CompanyProfile(company_name="X", confidence_score=1.5)
        with pytest.raises(ValidationError):
            CompanyProfile(company_name="X", confidence_score=-0.1)

    def test_confidence_score_valid_range(self):
        p = CompanyProfile(company_name="X", confidence_score=0.85)
        assert p.confidence_score == 0.85


# ── VisitorSignal ──────────────────────────────────────────────────────────────

class TestVisitorSignal:
    def test_valid_construction(self):
        v = VisitorSignal(
            visitor_id="v-001",
            ip_address="34.201.114.42",
            pages_visited=["/pricing"],
        )
        assert v.visitor_id == "v-001"
        assert v.visit_count == 1  # default
        assert v.time_on_site_seconds == 0  # default

    def test_visit_count_minimum_one(self):
        with pytest.raises(ValidationError):
            VisitorSignal(visitor_id="v", ip_address="1.2.3.4", visit_count=0)

    def test_time_on_site_non_negative(self):
        with pytest.raises(ValidationError):
            VisitorSignal(visitor_id="v", ip_address="1.2.3.4", time_on_site_seconds=-1)

    def test_optional_fields_default_none(self):
        v = VisitorSignal(visitor_id="v", ip_address="1.2.3.4")
        assert v.referral_source is None
        assert v.device_type is None
        assert v.location is None

    def test_pages_visited_defaults_empty(self):
        v = VisitorSignal(visitor_id="v", ip_address="1.2.3.4")
        assert v.pages_visited == []

    def test_full_construction(self):
        v = VisitorSignal(
            visitor_id="v-full",
            ip_address="54.0.0.1",
            pages_visited=["/pricing", "/features"],
            time_on_site_seconds=300,
            visit_count=5,
            referral_source="linkedin",
            device_type="mobile",
            location="San Francisco, CA",
            timestamps=["2026-03-18T10:00:00Z"],
        )
        assert v.visit_count == 5
        assert len(v.pages_visited) == 2


# ── IntentScore ────────────────────────────────────────────────────────────────

class TestIntentScore:
    def test_default_values(self):
        s = IntentScore()
        assert s.intent_score == 0.0
        assert s.intent_stage == IntentStage.AWARENESS
        assert s.confidence_score == 0.0

    def test_intent_score_max_10(self):
        with pytest.raises(ValidationError):
            IntentScore(intent_score=10.1)

    def test_intent_score_min_0(self):
        with pytest.raises(ValidationError):
            IntentScore(intent_score=-1.0)

    def test_all_stages_valid(self):
        for stage in IntentStage:
            s = IntentScore(intent_stage=stage)
            assert s.intent_stage == stage

    def test_page_score_breakdown_dict(self):
        s = IntentScore(page_score_breakdown={"/pricing": 3.0, "/demo": 2.5})
        assert s.page_score_breakdown["/pricing"] == 3.0


# ── PersonaInference ───────────────────────────────────────────────────────────

class TestPersonaInference:
    def test_defaults(self):
        p = PersonaInference(likely_role="Sales")
        assert p.seniority_level == SeniorityLevel.UNKNOWN
        assert p.confidence_score == 0.0
        assert p.reasoning == ""
        assert p.behavioral_signals == []

    def test_all_seniority_levels(self):
        for level in SeniorityLevel:
            p = PersonaInference(likely_role="Test", seniority_level=level)
            assert p.seniority_level == level

    def test_reasoning_field_set(self):
        p = PersonaInference(
            likely_role="VP of Sales",
            reasoning="Pricing + case study pattern",
        )
        assert "Pricing" in p.reasoning


# ── Technology & TechStack ─────────────────────────────────────────────────────

class TestTechStack:
    def test_technology_defaults(self):
        t = Technology(name="Salesforce")
        assert t.category == TechCategory.OTHER
        assert t.confidence_score == 0.0

    def test_tech_stack_defaults(self):
        ts = TechStack()
        assert ts.technologies == []
        assert ts.detection_method == "script_analysis"

    def test_all_categories_valid(self):
        for cat in TechCategory:
            t = Technology(name="Tool", category=cat)
            assert t.category == cat


# ── Signal & BusinessSignals ───────────────────────────────────────────────────

class TestBusinessSignals:
    def test_signal_types_valid(self):
        for st in SignalType:
            s = Signal(signal_type=st, title="T", description="D")
            assert s.signal_type == st

    def test_source_url_optional(self):
        s = Signal(signal_type=SignalType.HIRING, title="T", description="D")
        assert s.source_url is None

    def test_business_signals_defaults(self):
        bs = BusinessSignals()
        assert bs.signals == []
        assert bs.confidence_score == 0.0


# ── SalesPlaybook ──────────────────────────────────────────────────────────────

class TestSalesPlaybook:
    def test_default_priority_medium(self):
        p = SalesPlaybook()
        assert p.priority == Priority.MEDIUM

    def test_recommended_action_priority(self):
        a = RecommendedAction(action="Call", rationale="High intent", priority=Priority.HIGH)
        assert a.priority == Priority.HIGH

    def test_outreach_template_optional(self):
        p = SalesPlaybook()
        assert p.outreach_template is None


# ── AccountIntelligence ────────────────────────────────────────────────────────

class TestAccountIntelligence:
    def test_minimal_construction(self):
        intel = AccountIntelligence(
            company=CompanyProfile(company_name="Acme Corp")
        )
        assert intel.company.company_name == "Acme Corp"
        assert intel.persona is None
        assert intel.intent is None
        assert intel.tech_stack is None
        assert intel.business_signals is None
        assert intel.leadership is None
        assert intel.playbook is None
        assert intel.ai_summary == ""

    def test_analyzed_at_auto_set(self):
        intel = AccountIntelligence(company=CompanyProfile(company_name="X"))
        assert intel.analyzed_at
        assert "T" in intel.analyzed_at

    def test_confidence_score_bounds(self):
        with pytest.raises(ValidationError):
            AccountIntelligence(
                company=CompanyProfile(company_name="X"),
                confidence_score=1.1,
            )

    def test_full_construction(self, full_intelligence):
        """full_intelligence fixture exercises all optional fields."""
        assert full_intelligence.persona is not None
        assert full_intelligence.intent is not None
        assert full_intelligence.tech_stack is not None
        assert full_intelligence.business_signals is not None
        assert full_intelligence.leadership is not None


# ── API Request Schemas ────────────────────────────────────────────────────────

class TestRequestSchemas:
    """Validation rules live in API request schemas, not domain models."""

    def test_visitor_request_requires_visitor_id(self):
        from backend.api.schemas.requests import VisitorAnalysisRequest
        with pytest.raises(ValidationError):
            VisitorAnalysisRequest(ip_address="1.2.3.4", pages_visited=["/pricing"])  # type: ignore[call-arg]

    def test_visitor_request_requires_ip_address(self):
        from backend.api.schemas.requests import VisitorAnalysisRequest
        with pytest.raises(ValidationError):
            VisitorAnalysisRequest(visitor_id="v-1", pages_visited=["/pricing"])  # type: ignore[call-arg]

    def test_company_request_requires_name(self):
        from backend.api.schemas.requests import CompanyAnalysisRequest
        with pytest.raises(ValidationError):
            CompanyAnalysisRequest()  # type: ignore[call-arg]

    def test_company_request_max_length(self):
        from backend.api.schemas.requests import CompanyAnalysisRequest
        with pytest.raises(ValidationError):
            CompanyAnalysisRequest(company_name="A" * 201)

    def test_batch_request_max_companies(self):
        from backend.api.schemas.requests import BatchAnalysisRequest, CompanyAnalysisRequest
        companies = [CompanyAnalysisRequest(company_name=f"Co {i}") for i in range(21)]
        with pytest.raises(ValidationError):
            BatchAnalysisRequest(companies=companies)

    def test_batch_request_min_one_company(self):
        from backend.api.schemas.requests import BatchAnalysisRequest
        with pytest.raises(ValidationError):
            BatchAnalysisRequest(companies=[])
