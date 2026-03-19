"""PostgreSQL-backed persistence for jobs and account intelligence.

Uses asyncpg for async access. Full AccountIntelligence is stored as a JSONB
blob alongside denormalized columns for efficient listing/filtering.

Drop-in replacement for SQLiteJobStore/SQLiteAccountStore — same interfaces.
"""

import logging
from datetime import datetime, timezone
from typing import Optional

import asyncpg

from backend.domain.intelligence import AccountIntelligence
from backend.storage.base import AbstractAccountStore, AbstractJobStore
from backend.storage.job_store import JobRecord, JobStatus

logger = logging.getLogger(__name__)

_SCHEMA_SQL = """
CREATE TABLE IF NOT EXISTS jobs (
    job_id TEXT PRIMARY KEY,
    status TEXT NOT NULL DEFAULT 'PENDING',
    progress DOUBLE PRECISION NOT NULL DEFAULT 0.0,
    current_step TEXT,
    result_id TEXT,
    error TEXT,
    created_at TEXT NOT NULL,
    updated_at TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS accounts (
    account_id TEXT PRIMARY KEY,
    company_name TEXT NOT NULL,
    domain TEXT,
    industry TEXT,
    confidence_score DOUBLE PRECISION NOT NULL DEFAULT 0.0,
    analyzed_at TEXT NOT NULL,
    data JSONB NOT NULL
);

CREATE INDEX IF NOT EXISTS idx_accounts_analyzed ON accounts(analyzed_at DESC);
"""


async def init_postgres(database_url: str) -> asyncpg.Pool:
    """Create a connection pool and ensure tables exist."""
    pool = await asyncpg.create_pool(database_url, min_size=2, max_size=10)
    async with pool.acquire() as conn:
        await conn.execute(_SCHEMA_SQL)
    logger.info("PostgreSQL database initialized (pool min=2, max=10)")
    return pool


class PostgresJobStore(AbstractJobStore):
    """PostgreSQL-backed job store implementing AbstractJobStore."""

    def __init__(self, pool: asyncpg.Pool) -> None:
        self._pool = pool

    async def create(self, job_id: str) -> JobRecord:
        now = datetime.now(timezone.utc).isoformat()
        record = JobRecord(
            job_id=job_id,
            status=JobStatus.PENDING,
            created_at=now,
            updated_at=now,
        )
        async with self._pool.acquire() as conn:
            await conn.execute(
                """INSERT INTO jobs (job_id, status, progress, current_step, result_id, error, created_at, updated_at)
                   VALUES ($1, $2, $3, $4, $5, $6, $7, $8)""",
                record.job_id,
                record.status.value,
                record.progress,
                record.current_step,
                record.result_id,
                record.error,
                record.created_at,
                record.updated_at,
            )
        return record

    async def update(self, job_id: str, **fields) -> JobRecord:
        fields["updated_at"] = datetime.now(timezone.utc).isoformat()

        if "status" in fields and isinstance(fields["status"], JobStatus):
            fields["status"] = fields["status"].value

        set_parts = []
        values = []
        for idx, (key, val) in enumerate(fields.items(), start=1):
            set_parts.append(f"{key} = ${idx}")
            values.append(val)
        values.append(job_id)
        set_clause = ", ".join(set_parts)

        async with self._pool.acquire() as conn:
            result = await conn.execute(
                f"UPDATE jobs SET {set_clause} WHERE job_id = ${len(values)}",  # noqa: S608
                *values,
            )
            if result == "UPDATE 0":
                raise KeyError(f"Job {job_id!r} not found")

        return await self.get(job_id)  # type: ignore[return-value]

    async def get(self, job_id: str) -> Optional[JobRecord]:
        async with self._pool.acquire() as conn:
            row = await conn.fetchrow("SELECT * FROM jobs WHERE job_id = $1", job_id)
        if row is None:
            return None
        return JobRecord(
            job_id=row["job_id"],
            status=JobStatus(row["status"]),
            progress=row["progress"],
            current_step=row["current_step"],
            result_id=row["result_id"],
            error=row["error"],
            created_at=row["created_at"],
            updated_at=row["updated_at"],
        )


class PostgresAccountStore(AbstractAccountStore):
    """PostgreSQL-backed account store implementing AbstractAccountStore."""

    def __init__(self, pool: asyncpg.Pool) -> None:
        self._pool = pool

    async def save(self, intelligence: AccountIntelligence) -> str:
        data_json = intelligence.model_dump_json()

        company_name = intelligence.company.company_name if intelligence.company else "Unknown"
        domain = intelligence.company.domain if intelligence.company else None
        industry = intelligence.company.industry if intelligence.company else None

        async with self._pool.acquire() as conn:
            await conn.execute(
                """INSERT INTO accounts (account_id, company_name, domain, industry, confidence_score, analyzed_at, data)
                   VALUES ($1, $2, $3, $4, $5, $6, $7)
                   ON CONFLICT (account_id) DO UPDATE SET
                       company_name = EXCLUDED.company_name,
                       domain = EXCLUDED.domain,
                       industry = EXCLUDED.industry,
                       confidence_score = EXCLUDED.confidence_score,
                       analyzed_at = EXCLUDED.analyzed_at,
                       data = EXCLUDED.data""",
                intelligence.id,
                company_name,
                domain,
                industry,
                intelligence.confidence_score,
                intelligence.analyzed_at,
                data_json,
            )
        return intelligence.id

    async def get(self, account_id: str) -> Optional[AccountIntelligence]:
        async with self._pool.acquire() as conn:
            row = await conn.fetchrow(
                "SELECT data FROM accounts WHERE account_id = $1", account_id
            )
        if row is None:
            return None
        return AccountIntelligence.model_validate_json(row["data"])

    async def list(self, page: int = 1, size: int = 20) -> tuple[list[AccountIntelligence], int]:
        async with self._pool.acquire() as conn:
            count_row = await conn.fetchrow("SELECT COUNT(*) AS cnt FROM accounts")
            total = count_row["cnt"] if count_row else 0

            offset = (page - 1) * size
            rows = await conn.fetch(
                "SELECT data FROM accounts ORDER BY analyzed_at DESC LIMIT $1 OFFSET $2",
                size,
                offset,
            )

        items = []
        for row in rows:
            try:
                items.append(AccountIntelligence.model_validate_json(row["data"]))
            except Exception:
                logger.warning("Failed to deserialize account row, skipping")
        return items, total
