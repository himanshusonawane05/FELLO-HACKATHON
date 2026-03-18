"""SQLite persistence layer tests.

Tests SQLiteJobStore and SQLiteAccountStore for:
  - Basic CRUD operations
  - Persistence across store instances (simulates restart)
  - Correct serialization / deserialization of Pydantic models
  - Pagination
"""
import asyncio
import os
import tempfile

import pytest

from backend.domain.company import CompanyProfile
from backend.domain.intelligence import AccountIntelligence
from backend.storage.job_store import JobStatus
from backend.storage.sqlite_store import SQLiteAccountStore, SQLiteJobStore, init_db


@pytest.fixture()
async def db_url(tmp_path):
    """Create a fresh SQLite database for each test."""
    db_file = tmp_path / "test_fello.db"
    url = f"sqlite:///{db_file}"
    await init_db(url)
    return url


@pytest.fixture()
async def job_store(db_url):
    return SQLiteJobStore(db_url)


@pytest.fixture()
async def account_store(db_url):
    return SQLiteAccountStore(db_url)


def _make_intel(company_name: str = "Test Corp", confidence: float = 0.8) -> AccountIntelligence:
    return AccountIntelligence(
        company=CompanyProfile(company_name=company_name, confidence_score=confidence),
        confidence_score=confidence,
    )


# ── SQLiteJobStore ─────────────────────────────────────────────────────────────

class TestSQLiteJobStore:
    async def test_create_returns_pending_record(self, job_store):
        from backend.storage.job_store import JobRecord
        record = await job_store.create("job-sqlite-001")
        assert isinstance(record, JobRecord)
        assert record.job_id == "job-sqlite-001"
        assert record.status == JobStatus.PENDING
        assert record.progress == 0.0
        assert record.result_id is None

    async def test_get_existing_job(self, job_store):
        await job_store.create("job-sqlite-002")
        record = await job_store.get("job-sqlite-002")
        assert record is not None
        assert record.job_id == "job-sqlite-002"

    async def test_get_nonexistent_returns_none(self, job_store):
        result = await job_store.get("no-such-job")
        assert result is None

    async def test_update_status_to_processing(self, job_store):
        await job_store.create("job-sqlite-003")
        updated = await job_store.update("job-sqlite-003", status=JobStatus.PROCESSING)
        assert updated.status == JobStatus.PROCESSING

    async def test_update_progress(self, job_store):
        await job_store.create("job-sqlite-004")
        updated = await job_store.update("job-sqlite-004", progress=0.65, current_step="Enriching")
        assert updated.progress == 0.65
        assert updated.current_step == "Enriching"

    async def test_update_to_completed(self, job_store):
        await job_store.create("job-sqlite-005")
        updated = await job_store.update(
            "job-sqlite-005",
            status=JobStatus.COMPLETED,
            progress=1.0,
            result_id="account-xyz",
        )
        assert updated.status == JobStatus.COMPLETED
        assert updated.result_id == "account-xyz"

    async def test_update_to_failed(self, job_store):
        await job_store.create("job-sqlite-006")
        updated = await job_store.update(
            "job-sqlite-006",
            status=JobStatus.FAILED,
            error="Pipeline crashed",
        )
        assert updated.status == JobStatus.FAILED
        assert updated.error == "Pipeline crashed"

    async def test_update_nonexistent_raises(self, job_store):
        with pytest.raises(KeyError):
            await job_store.update("ghost-job", status=JobStatus.PROCESSING)

    async def test_persistence_across_instances(self, db_url):
        """Data written by one store instance is readable by another (simulates restart)."""
        store1 = SQLiteJobStore(db_url)
        await store1.create("persistent-job")
        await store1.update("persistent-job", status=JobStatus.PROCESSING, progress=0.5)

        store2 = SQLiteJobStore(db_url)
        record = await store2.get("persistent-job")
        assert record is not None
        assert record.status == JobStatus.PROCESSING
        assert record.progress == 0.5

    async def test_timestamps_are_iso_strings(self, job_store):
        record = await job_store.create("job-ts-001")
        assert "T" in record.created_at
        assert "T" in record.updated_at


# ── SQLiteAccountStore ─────────────────────────────────────────────────────────

class TestSQLiteAccountStore:
    async def test_save_returns_id(self, account_store):
        intel = _make_intel()
        result_id = await account_store.save(intel)
        assert result_id == intel.id

    async def test_get_existing_account(self, account_store):
        intel = _make_intel("Stripe")
        await account_store.save(intel)
        retrieved = await account_store.get(intel.id)
        assert retrieved is not None
        assert retrieved.company.company_name == "Stripe"

    async def test_get_nonexistent_returns_none(self, account_store):
        result = await account_store.get("no-such-account")
        assert result is None

    async def test_full_model_roundtrip(self, account_store):
        """Saved model must deserialize with all fields intact."""
        from backend.domain.intent import IntentScore, IntentStage
        from backend.domain.persona import PersonaInference, SeniorityLevel

        intel = AccountIntelligence(
            company=CompanyProfile(
                company_name="Roundtrip Corp",
                industry="Technology / SaaS",
                confidence_score=0.85,
            ),
            confidence_score=0.85,
            ai_summary="Test summary for roundtrip.",
        )
        await account_store.save(intel)
        retrieved = await account_store.get(intel.id)
        assert retrieved is not None
        assert retrieved.company.company_name == "Roundtrip Corp"
        assert retrieved.company.industry == "Technology / SaaS"
        assert retrieved.ai_summary == "Test summary for roundtrip."
        assert retrieved.confidence_score == 0.85

    async def test_list_returns_all_accounts(self, account_store):
        for i in range(5):
            await account_store.save(_make_intel(f"Company {i}"))
        accounts, total = await account_store.list()
        assert total == 5
        assert len(accounts) == 5

    async def test_list_empty_store(self, account_store):
        accounts, total = await account_store.list()
        assert total == 0
        assert accounts == []

    async def test_list_pagination(self, account_store):
        for i in range(10):
            await account_store.save(_make_intel(f"Co {i}"))
        page1, total = await account_store.list(page=1, size=4)
        assert total == 10
        assert len(page1) == 4

    async def test_persistence_across_instances(self, db_url):
        """Data written by one store instance is readable by another (simulates restart)."""
        store1 = SQLiteAccountStore(db_url)
        intel = _make_intel("Persistent Corp")
        await store1.save(intel)

        store2 = SQLiteAccountStore(db_url)
        retrieved = await store2.get(intel.id)
        assert retrieved is not None
        assert retrieved.company.company_name == "Persistent Corp"

    async def test_save_overwrites_same_id(self, account_store):
        """Saving with same ID replaces existing record."""
        intel = _make_intel("Original")
        await account_store.save(intel)
        updated = intel.model_copy(update={"ai_summary": "Updated summary"})
        await account_store.save(updated)
        retrieved = await account_store.get(intel.id)
        assert retrieved.ai_summary == "Updated summary"

    async def test_list_sorted_by_analyzed_at_descending(self, account_store):
        """Most recently analyzed appears first."""
        intel1 = _make_intel("Old Corp")
        await account_store.save(intel1)
        await asyncio.sleep(0.05)
        intel2 = _make_intel("New Corp")
        await account_store.save(intel2)
        accounts, _ = await account_store.list()
        assert accounts[0].company.company_name == "New Corp"


# ── Unknown IP edge cases ──────────────────────────────────────────────────────

class TestUnknownIPEdgeCases:
    """Verify that unknown/private/cloud IPs are handled gracefully."""

    async def test_private_ip_identification(self):
        """Private IPs must return Unknown without calling external tools."""
        from backend.agents.identification import IdentificationAgent
        from unittest.mock import MagicMock

        agent = IdentificationAgent(llm=MagicMock())
        from backend.domain.visitor import VisitorSignal

        for private_ip in ["192.168.1.1", "10.0.0.1", "172.16.0.1", "127.0.0.1"]:
            signal = VisitorSignal(visitor_id="v-test", ip_address=private_ip)
            result = await agent.run(signal)
            assert "Unknown" in result.company_name, (
                f"Private IP {private_ip!r} should return Unknown, got {result.company_name!r}"
            )

    async def test_unknown_company_enrichment_is_low_confidence(self):
        """Unknown company name must produce low-confidence enrichment."""
        from backend.agents.enrichment import EnrichmentAgent
        from backend.domain.company import CompanyInput
        from unittest.mock import MagicMock

        agent = EnrichmentAgent(llm=MagicMock())
        for unknown_name in ["Unknown", "Unknown (Private IP)"]:
            result = await agent.run(CompanyInput(company_name=unknown_name))
            assert result.confidence_score < 0.3, (
                f"Unknown company {unknown_name!r} should have confidence < 0.3, got {result.confidence_score}"
            )

    async def test_unknown_company_tech_stack_is_empty(self):
        """Unknown company must return empty tech stack."""
        from backend.agents.tech_stack import TechStackAgent
        from unittest.mock import MagicMock

        agent = TechStackAgent(llm=MagicMock())
        result = await agent.run(CompanyProfile(company_name="Unknown", confidence_score=0.1))
        assert result.technologies == []
        assert result.confidence_score == 0.0

    async def test_unknown_company_signals_are_empty(self):
        """Unknown company must return empty business signals."""
        from backend.agents.signals import SignalsAgent
        from unittest.mock import MagicMock

        agent = SignalsAgent(llm=MagicMock())
        result = await agent.run(CompanyProfile(company_name="Unknown", confidence_score=0.1))
        assert result.signals == []
        assert result.confidence_score == 0.0

    async def test_unknown_company_leadership_is_empty(self):
        """Unknown company must return empty leadership."""
        from backend.agents.leadership import LeadershipAgent
        from unittest.mock import MagicMock

        agent = LeadershipAgent(llm=MagicMock())
        result = await agent.run(CompanyProfile(company_name="Unknown", confidence_score=0.1))
        assert result.leaders == []
        assert result.confidence_score == 0.0

    async def test_unknown_company_playbook_is_minimal(self):
        """Unknown company must return minimal playbook with identification action."""
        from backend.agents.playbook import PlaybookAgent
        from backend.domain.playbook import Priority
        from unittest.mock import MagicMock

        agent = PlaybookAgent(llm=MagicMock())
        intel = AccountIntelligence(
            company=CompanyProfile(company_name="Unknown", confidence_score=0.1),
        )
        result = await agent.run(intel)
        assert result.priority == Priority.LOW
        assert len(result.recommended_actions) >= 1

    async def test_unknown_company_summary_reflects_uncertainty(self):
        """Unknown company must get an uncertainty-aware summary."""
        from backend.agents.summary import SummaryAgent
        from unittest.mock import MagicMock

        agent = SummaryAgent(llm=MagicMock())
        intel = AccountIntelligence(
            company=CompanyProfile(company_name="Unknown", confidence_score=0.1),
        )
        result = await agent.run(intel)
        assert result.ai_summary
        summary_lower = result.ai_summary.lower()
        assert any(kw in summary_lower for kw in [
            "unknown", "could not", "not identified", "identify", "engagement", "capture"
        ]), f"Unknown company summary should reflect uncertainty: {result.ai_summary!r}"
