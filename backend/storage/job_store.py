import asyncio
from datetime import datetime
from enum import Enum
from typing import Optional

from pydantic import BaseModel


class JobStatus(str, Enum):
    PENDING = "PENDING"
    PROCESSING = "PROCESSING"
    COMPLETED = "COMPLETED"
    FAILED = "FAILED"


class JobRecord(BaseModel):
    """Mutable job record stored in-memory."""

    job_id: str
    status: JobStatus
    progress: float = 0.0
    current_step: Optional[str] = None
    result_id: Optional[str] = None
    error: Optional[str] = None
    created_at: str
    updated_at: str


class InMemoryJobStore:
    """Thread-safe, asyncio-compatible in-memory job store."""

    def __init__(self) -> None:
        self._store: dict[str, JobRecord] = {}
        self._lock = asyncio.Lock()

    async def create(self, job_id: str) -> JobRecord:
        """Create a new PENDING job."""
        now = datetime.utcnow().isoformat()
        record = JobRecord(
            job_id=job_id,
            status=JobStatus.PENDING,
            created_at=now,
            updated_at=now,
        )
        async with self._lock:
            self._store[job_id] = record
        return record

    async def update(self, job_id: str, **fields) -> JobRecord:
        """Partially update an existing job record."""
        async with self._lock:
            record = self._store[job_id]
            updated = record.model_copy(update={**fields, "updated_at": datetime.utcnow().isoformat()})
            self._store[job_id] = updated
        return updated

    async def get(self, job_id: str) -> Optional[JobRecord]:
        """Retrieve a job record by ID. Returns None if not found."""
        async with self._lock:
            return self._store.get(job_id)


job_store = InMemoryJobStore()
