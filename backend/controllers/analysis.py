"""AnalysisController — bridges API routes and the LangGraph pipeline.

Rules:
- All public methods are async
- Accept and return domain models (or JobRecord for job creation)
- No LLM calls, no HTTP, no response schemas
- Background pipeline tasks are created via asyncio.create_task()
"""
import asyncio
import logging
from typing import Optional
from uuid import uuid4

from backend.domain.company import CompanyInput
from backend.domain.intelligence import AccountIntelligence
from backend.domain.visitor import VisitorSignal
import backend.storage.account_store as _account_store_mod
import backend.storage.job_store as _job_store_mod
from backend.storage.job_store import JobRecord, JobStatus

logger = logging.getLogger(__name__)


class AnalysisController:
    """Bridges API routes and LangGraph workflow execution."""

    async def analyze_visitor(self, signal: VisitorSignal) -> JobRecord:
        """Create job, dispatch graph for visitor analysis. Returns the JobRecord."""
        job_id = str(uuid4())
        record = await _job_store_mod.job_store.create(job_id)
        asyncio.create_task(
            self._run_pipeline(job_id, visitor_signal=signal),
            name=f"pipeline-{job_id[:8]}",
        )
        return record

    async def analyze_company(self, input: CompanyInput) -> JobRecord:
        """Create job, dispatch graph for company analysis. Returns the JobRecord."""
        job_id = str(uuid4())
        record = await _job_store_mod.job_store.create(job_id)
        asyncio.create_task(
            self._run_pipeline(job_id, company_input=input),
            name=f"pipeline-{job_id[:8]}",
        )
        return record

    async def analyze_batch(self, inputs: list[CompanyInput]) -> tuple[JobRecord, list[str]]:
        """Create a batch job + one job per company. Returns (batch_record, job_ids)."""
        batch_id = str(uuid4())
        batch_record = await _job_store_mod.job_store.create(batch_id)
        job_ids: list[str] = []
        for company_input in inputs:
            record = await self.analyze_company(company_input)
            job_ids.append(record.job_id)
        await _job_store_mod.job_store.update(
            batch_id, status=JobStatus.PROCESSING, progress=0.05,
            current_step="Individual jobs dispatched",
        )
        return batch_record, job_ids

    async def get_job_status(self, job_id: str) -> Optional[JobRecord]:
        """Return the current JobRecord. Returns None if not found."""
        return await _job_store_mod.job_store.get(job_id)

    async def get_account(self, account_id: str) -> Optional[AccountIntelligence]:
        """Return completed AccountIntelligence from AccountStore."""
        return await _account_store_mod.account_store.get(account_id)

    async def list_accounts(self, page: int = 1, page_size: int = 20) -> tuple[list, int]:
        """Return paginated account list and total count."""
        return await _account_store_mod.account_store.list(page=page, size=page_size)

    # ── Private pipeline runner ────────────────────────────────────────────────

    async def _run_pipeline(
        self,
        job_id: str,
        *,
        visitor_signal: Optional[VisitorSignal] = None,
        company_input: Optional[CompanyInput] = None,
    ) -> None:
        """Execute the LangGraph pipeline as a background task with granular progress."""
        from backend.graph.workflow import compiled_workflow

        await _job_store_mod.job_store.update(
            job_id,
            status=JobStatus.PROCESSING,
            progress=0.02,
            current_step="Pipeline starting",
        )

        try:
            initial_state: dict = {
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

            result = await compiled_workflow.ainvoke(initial_state)
            intelligence: Optional[AccountIntelligence] = result.get("intelligence")

            if intelligence:
                result_id = await _account_store_mod.account_store.save(intelligence)
                await _job_store_mod.job_store.update(
                    job_id,
                    status=JobStatus.COMPLETED,
                    progress=1.0,
                    current_step=None,
                    result_id=result_id,
                )
                logger.info("Job %s completed → account %s", job_id[:8], result_id[:8])
            else:
                errors = result.get("errors", [])
                error_msg = "; ".join(errors) if errors else "Pipeline produced no output"
                await _job_store_mod.job_store.update(
                    job_id,
                    status=JobStatus.FAILED,
                    error=error_msg,
                )
                logger.warning("Job %s failed: %s", job_id[:8], error_msg)

        except Exception as exc:
            logger.error("Job %s pipeline exception: %s", job_id[:8], exc, exc_info=True)
            await _job_store_mod.job_store.update(
                job_id,
                status=JobStatus.FAILED,
                error=str(exc),
            )


analysis_controller = AnalysisController()
