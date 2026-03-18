"""Storage layer tests — InMemoryJobStore and InMemoryAccountStore."""
import asyncio

import pytest

from backend.domain.company import CompanyProfile
from backend.domain.intelligence import AccountIntelligence
from backend.storage.account_store import InMemoryAccountStore
from backend.storage.job_store import InMemoryJobStore, JobRecord, JobStatus


# ── InMemoryJobStore ───────────────────────────────────────────────────────────

class TestInMemoryJobStore:
    @pytest.fixture()
    def store(self) -> InMemoryJobStore:
        return InMemoryJobStore()

    async def test_create_returns_pending_record(self, store):
        record = await store.create("job-001")
        assert isinstance(record, JobRecord)
        assert record.job_id == "job-001"
        assert record.status == JobStatus.PENDING
        assert record.progress == 0.0
        assert record.result_id is None
        assert record.error is None

    async def test_create_sets_timestamps(self, store):
        record = await store.create("job-001")
        assert record.created_at
        assert record.updated_at
        assert "T" in record.created_at

    async def test_get_existing_job(self, store):
        await store.create("job-001")
        record = await store.get("job-001")
        assert record is not None
        assert record.job_id == "job-001"

    async def test_get_nonexistent_job_returns_none(self, store):
        result = await store.get("does-not-exist")
        assert result is None

    async def test_update_status(self, store):
        await store.create("job-001")
        updated = await store.update("job-001", status=JobStatus.PROCESSING)
        assert updated.status == JobStatus.PROCESSING

    async def test_update_progress(self, store):
        await store.create("job-001")
        updated = await store.update("job-001", progress=0.45, current_step="Enriching")
        assert updated.progress == 0.45
        assert updated.current_step == "Enriching"

    async def test_update_to_completed_with_result_id(self, store):
        await store.create("job-001")
        updated = await store.update(
            "job-001",
            status=JobStatus.COMPLETED,
            progress=1.0,
            current_step=None,
            result_id="account-abc",
        )
        assert updated.status == JobStatus.COMPLETED
        assert updated.result_id == "account-abc"
        assert updated.progress == 1.0

    async def test_update_to_failed_with_error(self, store):
        await store.create("job-001")
        updated = await store.update(
            "job-001",
            status=JobStatus.FAILED,
            error="Identification failed",
        )
        assert updated.status == JobStatus.FAILED
        assert updated.error == "Identification failed"

    async def test_update_refreshes_updated_at(self, store):
        record = await store.create("job-001")
        original_updated_at = record.updated_at
        await asyncio.sleep(0.01)
        updated = await store.update("job-001", progress=0.5)
        assert updated.updated_at >= original_updated_at

    async def test_update_nonexistent_raises(self, store):
        with pytest.raises(KeyError):
            await store.update("ghost-job", status=JobStatus.PROCESSING)

    async def test_concurrent_creates_are_safe(self, store):
        """Two concurrent creates must not lose either record."""
        jobs = [f"job-{i:03d}" for i in range(20)]
        await asyncio.gather(*[store.create(j) for j in jobs])
        for job_id in jobs:
            record = await store.get(job_id)
            assert record is not None

    async def test_multiple_jobs_independent(self, store):
        await store.create("job-A")
        await store.create("job-B")
        await store.update("job-A", status=JobStatus.COMPLETED, progress=1.0)
        record_b = await store.get("job-B")
        assert record_b.status == JobStatus.PENDING  # B unaffected by A's update


# ── InMemoryAccountStore ───────────────────────────────────────────────────────

class TestInMemoryAccountStore:
    @pytest.fixture()
    def store(self) -> InMemoryAccountStore:
        return InMemoryAccountStore()

    def _make_intel(self, company_name: str = "Test Corp") -> AccountIntelligence:
        return AccountIntelligence(
            company=CompanyProfile(company_name=company_name, confidence_score=0.8),
            confidence_score=0.8,
        )

    async def test_save_returns_id(self, store):
        intel = self._make_intel()
        result_id = await store.save(intel)
        assert result_id == intel.id

    async def test_get_existing_account(self, store):
        intel = self._make_intel()
        await store.save(intel)
        retrieved = await store.get(intel.id)
        assert retrieved is not None
        assert retrieved.company.company_name == "Test Corp"

    async def test_get_nonexistent_returns_none(self, store):
        result = await store.get("no-such-account")
        assert result is None

    async def test_list_returns_all_accounts(self, store):
        for i in range(5):
            await store.save(self._make_intel(f"Company {i}"))
        accounts, total = await store.list()
        assert total == 5
        assert len(accounts) == 5

    async def test_list_pagination_page_1(self, store):
        for i in range(10):
            await store.save(self._make_intel(f"Co {i}"))
        page1, total = await store.list(page=1, size=4)
        assert total == 10
        assert len(page1) == 4

    async def test_list_pagination_last_page(self, store):
        for i in range(10):
            await store.save(self._make_intel(f"Co {i}"))
        page3, total = await store.list(page=3, size=4)
        assert total == 10
        assert len(page3) == 2  # 10 items, page 3 of size 4 → 2 remain

    async def test_list_empty_store(self, store):
        accounts, total = await store.list()
        assert total == 0
        assert accounts == []

    async def test_list_sorted_by_analyzed_at_descending(self, store):
        """Most recently analyzed appears first.
        
        Creates intel2 AFTER the sleep so its analyzed_at is guaranteed newer.
        """
        intel1 = self._make_intel("Old Corp")
        await store.save(intel1)
        await asyncio.sleep(0.05)  # ensure clock advances before second object is created
        intel2 = self._make_intel("New Corp")  # created (and timestamped) after sleep
        await store.save(intel2)
        accounts, _ = await store.list()
        assert accounts[0].company.company_name == "New Corp"

    async def test_save_overwrites_same_id(self, store):
        """Saving with same ID replaces existing record (store keyed by id)."""
        intel = self._make_intel("Original")
        await store.save(intel)
        # Build a new object with the same id by using model_copy (since frozen)
        updated = intel.model_copy(update={"ai_summary": "Updated summary"})
        await store.save(updated)
        retrieved = await store.get(intel.id)
        assert retrieved.ai_summary == "Updated summary"
