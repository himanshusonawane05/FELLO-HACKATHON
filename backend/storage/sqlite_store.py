"""SQLite-backed persistence for jobs and account intelligence.

Uses aiosqlite for async access. Full AccountIntelligence is stored as a JSON
blob alongside denormalized columns for efficient listing/filtering.
"""

import logging
from datetime import datetime
from pathlib import Path
from typing import Optional

import aiosqlite

from backend.domain.intelligence import AccountIntelligence
from backend.storage.base import AbstractAccountStore, AbstractJobStore
from backend.storage.job_store import JobRecord, JobStatus

logger = logging.getLogger(__name__)

_SCHEMA_SQL = """
CREATE TABLE IF NOT EXISTS jobs (
    job_id TEXT PRIMARY KEY,
    status TEXT NOT NULL DEFAULT 'PENDING',
    progress REAL NOT NULL DEFAULT 0.0,
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
    confidence_score REAL NOT NULL DEFAULT 0.0,
    analyzed_at TEXT NOT NULL,
    data JSON NOT NULL
);

CREATE INDEX IF NOT EXISTS idx_accounts_analyzed ON accounts(analyzed_at DESC);
"""


def _db_path_from_url(database_url: str) -> str:
    """Extract the file path from a 'sqlite:///...' URL.

    Supports both relative and absolute paths:
    - sqlite:///data/fello.db     -> data/fello.db (relative)
    - sqlite:////data/fello.db    -> /data/fello.db (absolute, 4 slashes)
    """
    url = (database_url or "").strip()
    if url.startswith("sqlite:///"):
        path = url[len("sqlite:///") :].rstrip("/")
        return path if path else "data/fello.db"
    return url or "data/fello.db"


async def init_db(database_url: str) -> None:
    """Create the database file (if needed) and ensure tables exist.

    Logs the absolute resolved path so production logs show exactly where
    the file is being created regardless of working directory.
    """
    db_path = _db_path_from_url(database_url)
    abs_path = Path(db_path).resolve()
    abs_path.parent.mkdir(parents=True, exist_ok=True)
    async with aiosqlite.connect(str(abs_path)) as db:
        await db.executescript(_SCHEMA_SQL)
        await db.commit()
    logger.info("SQLite database initialized at %s", abs_path)


class SQLiteJobStore(AbstractJobStore):
    """SQLite-backed job store implementing AbstractJobStore."""

    def __init__(self, database_url: str) -> None:
        self._db_path = str(Path(_db_path_from_url(database_url)).resolve())

    async def create(self, job_id: str) -> JobRecord:
        """Create a new PENDING job."""
        now = datetime.utcnow().isoformat()
        record = JobRecord(
            job_id=job_id,
            status=JobStatus.PENDING,
            created_at=now,
            updated_at=now,
        )
        async with aiosqlite.connect(self._db_path) as db:
            await db.execute(
                "INSERT INTO jobs (job_id, status, progress, current_step, result_id, error, created_at, updated_at) "
                "VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
                (
                    record.job_id,
                    record.status.value,
                    record.progress,
                    record.current_step,
                    record.result_id,
                    record.error,
                    record.created_at,
                    record.updated_at,
                ),
            )
            await db.commit()
        return record

    async def update(self, job_id: str, **fields) -> JobRecord:
        """Partially update an existing job record."""
        fields["updated_at"] = datetime.utcnow().isoformat()

        if "status" in fields and isinstance(fields["status"], JobStatus):
            fields["status"] = fields["status"].value

        set_clause = ", ".join(f"{k} = ?" for k in fields)
        values = list(fields.values())
        values.append(job_id)

        async with aiosqlite.connect(self._db_path) as db:
            cursor = await db.execute(
                f"UPDATE jobs SET {set_clause} WHERE job_id = ?",  # noqa: S608
                values,
            )
            await db.commit()
            if cursor.rowcount == 0:
                raise KeyError(f"Job {job_id!r} not found")

        return await self.get(job_id)  # type: ignore[return-value]

    async def get(self, job_id: str) -> Optional[JobRecord]:
        """Retrieve a job record by ID."""
        async with aiosqlite.connect(self._db_path) as db:
            db.row_factory = aiosqlite.Row
            cursor = await db.execute("SELECT * FROM jobs WHERE job_id = ?", (job_id,))
            row = await cursor.fetchone()
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


class SQLiteAccountStore(AbstractAccountStore):
    """SQLite-backed account store implementing AbstractAccountStore."""

    def __init__(self, database_url: str) -> None:
        self._db_path = str(Path(_db_path_from_url(database_url)).resolve())

    async def save(self, intelligence: AccountIntelligence) -> str:
        """Persist an AccountIntelligence object. Returns its ID."""
        data_json = intelligence.model_dump_json()

        company_name = intelligence.company.company_name if intelligence.company else "Unknown"
        domain = intelligence.company.domain if intelligence.company else None
        industry = intelligence.company.industry if intelligence.company else None

        async with aiosqlite.connect(self._db_path) as db:
            await db.execute(
                "INSERT OR REPLACE INTO accounts "
                "(account_id, company_name, domain, industry, confidence_score, analyzed_at, data) "
                "VALUES (?, ?, ?, ?, ?, ?, ?)",
                (
                    intelligence.id,
                    company_name,
                    domain,
                    industry,
                    intelligence.confidence_score,
                    intelligence.analyzed_at,
                    data_json,
                ),
            )
            await db.commit()
        return intelligence.id

    async def get(self, account_id: str) -> Optional[AccountIntelligence]:
        """Retrieve account intelligence by ID."""
        async with aiosqlite.connect(self._db_path) as db:
            db.row_factory = aiosqlite.Row
            cursor = await db.execute(
                "SELECT data FROM accounts WHERE account_id = ?", (account_id,)
            )
            row = await cursor.fetchone()
            if row is None:
                return None
            return AccountIntelligence.model_validate_json(row["data"])

    async def list(self, page: int = 1, size: int = 20) -> tuple[list[AccountIntelligence], int]:
        """Return a paginated list of all account intelligence records."""
        async with aiosqlite.connect(self._db_path) as db:
            db.row_factory = aiosqlite.Row
            cursor = await db.execute("SELECT COUNT(*) as cnt FROM accounts")
            count_row = await cursor.fetchone()
            total = count_row["cnt"] if count_row else 0

            offset = (page - 1) * size
            cursor = await db.execute(
                "SELECT data FROM accounts ORDER BY analyzed_at DESC LIMIT ? OFFSET ?",
                (size, offset),
            )
            rows = await cursor.fetchall()

        items = []
        for row in rows:
            try:
                items.append(AccountIntelligence.model_validate_json(row["data"]))
            except Exception:
                logger.warning("Failed to deserialize account row, skipping")
        return items, total
