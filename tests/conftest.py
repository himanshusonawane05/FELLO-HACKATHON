"""Shared fixtures for the Fello backend test suite.

Isolation strategy:
  - `mock_llm`      → replaces get_llm() so no real ChatOpenAI is constructed.
  - `fresh_stores`  → patches module-level job_store / account_store singletons
                       with new instances so tests never share state.
  - `async_client`  → httpx.AsyncClient wired to the FastAPI app; uses fresh_stores.
"""
from __future__ import annotations

from unittest.mock import MagicMock

import pytest
import pytest_asyncio
from httpx import ASGITransport, AsyncClient

from backend.domain.company import CompanyInput, CompanyProfile
from backend.domain.intent import IntentScore, IntentStage
from backend.domain.intelligence import AccountIntelligence
from backend.domain.leadership import Leader, LeadershipProfile
from backend.domain.persona import PersonaInference, SeniorityLevel
from backend.domain.playbook import Priority, RecommendedAction, SalesPlaybook
from backend.domain.signals import BusinessSignals, Signal, SignalType
from backend.domain.tech_stack import TechCategory, TechStack, Technology
from backend.domain.visitor import VisitorSignal
from backend.storage.account_store import InMemoryAccountStore
from backend.storage.job_store import InMemoryJobStore


# ── LLM mock ──────────────────────────────────────────────────────────────────

@pytest.fixture(autouse=True)
def mock_llm_factory(monkeypatch):
    """Prevent any test from constructing a real ChatOpenAI instance.

    Patches both the cached factory and the lru_cache so the mock is always
    returned regardless of call order.
    """
    mock = MagicMock()

    from backend.core import llm as llm_module
    llm_module.get_llm.cache_clear()
    monkeypatch.setattr(llm_module, "get_llm", lambda temperature=0.0: mock)

    return mock


# ── Store isolation ────────────────────────────────────────────────────────────

@pytest.fixture()
def fresh_stores(monkeypatch):
    """Patch module-level store singletons with fresh instances per test.

    Uses sys.modules to get the actual module objects, bypassing the
    backend.storage package __init__.py which shadows submodule names.
    """
    import sys

    new_job_store = InMemoryJobStore()
    new_account_store = InMemoryAccountStore()

    # Ensure modules are imported before patching
    import backend.storage.job_store  # noqa: F401
    import backend.storage.account_store  # noqa: F401
    import backend.controllers.analysis  # noqa: F401

    js_mod = sys.modules["backend.storage.job_store"]
    as_mod = sys.modules["backend.storage.account_store"]
    ctrl_mod = sys.modules["backend.controllers.analysis"]

    monkeypatch.setattr(js_mod, "job_store", new_job_store)
    monkeypatch.setattr(as_mod, "account_store", new_account_store)
    monkeypatch.setattr(ctrl_mod, "job_store", new_job_store)
    monkeypatch.setattr(ctrl_mod, "account_store", new_account_store)

    return new_job_store, new_account_store


@pytest_asyncio.fixture()
async def async_client(fresh_stores):
    """Async HTTP client wired to the FastAPI app with isolated stores."""
    from backend.main import app

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        yield client


# ── Reusable domain objects ────────────────────────────────────────────────────

@pytest.fixture()
def visitor_signal() -> VisitorSignal:
    return VisitorSignal(
        visitor_id="v-test-001",
        ip_address="34.201.114.42",
        pages_visited=["/pricing", "/ai-sales-agent", "/case-studies"],
        time_on_site_seconds=222,
        visit_count=3,
        referral_source="google",
        device_type="desktop",
        location="New York, USA",
    )


@pytest.fixture()
def company_input() -> CompanyInput:
    return CompanyInput(company_name="BrightPath Lending", domain="brightpathlending.com")


@pytest.fixture()
def company_profile() -> CompanyProfile:
    return CompanyProfile(
        company_name="BrightPath Lending",
        domain="brightpathlending.com",
        industry="Mortgage Lending",
        company_size_estimate="200-500 employees",
        headquarters="Dallas, TX, USA",
        founding_year=2008,
        description="A residential mortgage lender.",
        annual_revenue_range="$50M-$100M",
        confidence_score=0.82,
        data_sources=["mock_enrichment"],
    )


@pytest.fixture()
def full_intelligence(company_profile: CompanyProfile) -> AccountIntelligence:
    """Fully populated AccountIntelligence for testing playbook/summary agents."""
    return AccountIntelligence(
        company=company_profile,
        persona=PersonaInference(
            likely_role="VP of Sales",
            department="Sales",
            seniority_level=SeniorityLevel.VP,
            behavioral_signals=["Visited pricing page"],
            confidence_score=0.72,
            reasoning="Pricing + case study pattern",
        ),
        intent=IntentScore(
            intent_score=8.4,
            intent_stage=IntentStage.EVALUATION,
            signals_detected=["Pricing page visit"],
            page_score_breakdown={"/pricing": 3.0},
            confidence_score=0.88,
        ),
        tech_stack=TechStack(
            technologies=[
                Technology(name="Salesforce", category=TechCategory.CRM, confidence_score=0.9),
            ],
            detection_method="heuristic",
            confidence_score=0.85,
        ),
        business_signals=BusinessSignals(
            signals=[
                Signal(
                    signal_type=SignalType.HIRING,
                    title="Hiring SDRs",
                    description="3 open SDR roles on LinkedIn",
                    source_url="https://linkedin.com/jobs",
                )
            ],
            confidence_score=0.72,
        ),
        leadership=LeadershipProfile(
            leaders=[
                Leader(
                    name="James Thornton",
                    title="VP of Sales",
                    department="Sales",
                    linkedin_url="https://linkedin.com/in/james-thornton",
                    source_url="https://brightpathlending.com/about",
                )
            ],
            confidence_score=0.74,
        ),
        confidence_score=0.80,
    )
