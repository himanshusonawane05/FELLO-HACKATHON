# Database Schema — Fello AI Account Intelligence System

> **Version**: 3.0  
> **Date**: 2026-03-19  
> **Storage Engine**: PostgreSQL (production) / SQLite (local dev) / In-memory (fallback)  
> **Depends on**: [LLD](./lld.md), [API Contracts](./api-contracts.md)  
> **Status**: PostgreSQL support added — data persists across Railway deployments

---

## 1. Storage Architecture

The system supports three storage backends, selected automatically by the `DATABASE_URL` config setting. All three implement the same `AbstractJobStore` / `AbstractAccountStore` interfaces — controllers, graph nodes, and API routes are completely unaffected by which backend is active.

```
┌──────────────────────────────────────────────────────────────────┐
│                        Storage Layer                              │
│                                                                  │
│  ┌──────────────────────────────────────────────────────────┐    │
│  │         AbstractJobStore / AbstractAccountStore           │    │
│  │                  (backend/storage/base.py)                │    │
│  └────────────┬──────────────────┬──────────────────────────┘    │
│               │                  │                  │             │
│  ┌────────────▼──────┐  ┌────────▼──────┐  ┌───────▼──────────┐ │
│  │ PostgresJobStore   │  │ SQLiteJobStore│  │ InMemoryJobStore  │ │
│  │ PostgresAccount    │  │ SQLiteAccount │  │ InMemoryAccount   │ │
│  │ Store              │  │ Store         │  │ Store             │ │
│  │ (postgres_store.py)│  │(sqlite_store) │  │(job_store.py,     │ │
│  │                    │  │               │  │ account_store.py) │ │
│  │ asyncpg pool       │  │ aiosqlite     │  │ Python dicts +    │ │
│  │ production/Railway │  │ local dev     │  │ asyncio.Lock      │ │
│  └────────────────────┘  └───────────────┘  └──────────────────┘ │
│                                                                  │
│  DATABASE_URL=postgresql://...  → PostgresJobStore (production)  │
│  DATABASE_URL=sqlite:///...     → SQLiteJobStore (local dev)     │
│  DATABASE_URL=none or unset     → InMemoryJobStore (ephemeral)   │
│                                                                  │
│  Module-level singletons swapped in main.py lifespan            │
└──────────────────────────────────────────────────────────────────┘
```

**Relationship:** When a job completes, its `result_id` field points to an `account_id` in the AccountStore. This is the foreign key link between the two stores.

---

## 2. JobStore Schema

### 2.1 JobRecord

| Field | Type | Constraints | Default | Description |
|-------|------|------------|---------|-------------|
| `job_id` | `str` | PK, UUID format | required | Unique job identifier |
| `status` | `JobStatus` | enum | `PENDING` | Current execution state |
| `progress` | `float` | 0.0–1.0 | `0.0` | Fractional completion |
| `current_step` | `Optional[str]` | max 200 chars | `None` | Human-readable step label |
| `result_id` | `Optional[str]` | FK → AccountStore | `None` | Set on COMPLETED |
| `error` | `Optional[str]` | max 500 chars | `None` | Set on FAILED |
| `analysis_type` | `str` | "visitor"\|"company"\|"batch" | required | Input type that created this job |
| `batch_id` | `Optional[str]` | UUID format | `None` | Parent batch (for batch jobs) |
| `created_at` | `str` | ISO 8601 | auto | Creation timestamp |
| `updated_at` | `str` | ISO 8601 | auto | Last modification timestamp |

### 2.2 JobStatus Enum

```python
class JobStatus(str, Enum):
    PENDING = "PENDING"
    PROCESSING = "PROCESSING"
    COMPLETED = "COMPLETED"
    FAILED = "FAILED"
```

### 2.3 State Transitions

```
PENDING ──▶ PROCESSING ──▶ COMPLETED
                │
                └──────────▶ FAILED
```

- `PENDING → PROCESSING`: When graph execution begins
- `PROCESSING → COMPLETED`: When SummaryAgent returns AccountIntelligence
- `PROCESSING → FAILED`: When unrecoverable error occurs (all agents return degraded; this is rare)

### 2.4 Operations

| Operation | Signature | Complexity | Notes |
|-----------|-----------|-----------|-------|
| `create` | `(job_id: str, analysis_type: str, batch_id: Optional[str]) → JobRecord` | O(1) | Sets status=PENDING, timestamps |
| `update` | `(job_id: str, **fields) → JobRecord` | O(1) | Updates only provided fields + updated_at |
| `get` | `(job_id: str) → Optional[JobRecord]` | O(1) | Returns None if not found |
| `get_batch_jobs` | `(batch_id: str) → list[JobRecord]` | O(n) | Filters all jobs by batch_id |

### 2.5 Example Records

**Pending job:**
```json
{
  "job_id": "550e8400-e29b-41d4-a716-446655440000",
  "status": "PENDING",
  "progress": 0.0,
  "current_step": null,
  "result_id": null,
  "error": null,
  "analysis_type": "visitor",
  "batch_id": null,
  "created_at": "2026-03-18T10:05:00Z",
  "updated_at": "2026-03-18T10:05:00Z"
}
```

**Processing job (mid-pipeline):**
```json
{
  "job_id": "550e8400-e29b-41d4-a716-446655440000",
  "status": "PROCESSING",
  "progress": 0.45,
  "current_step": "Enriching company profile",
  "result_id": null,
  "error": null,
  "analysis_type": "visitor",
  "batch_id": null,
  "created_at": "2026-03-18T10:05:00Z",
  "updated_at": "2026-03-18T10:05:12Z"
}
```

**Completed job:**
```json
{
  "job_id": "550e8400-e29b-41d4-a716-446655440000",
  "status": "COMPLETED",
  "progress": 1.0,
  "current_step": null,
  "result_id": "880e8400-e29b-41d4-a716-446655440010",
  "error": null,
  "analysis_type": "visitor",
  "batch_id": null,
  "created_at": "2026-03-18T10:05:00Z",
  "updated_at": "2026-03-18T10:05:28Z"
}
```

---

## 3. AccountStore Schema

### 3.1 AccountIntelligence (Aggregate Root)

The AccountStore stores the full `AccountIntelligence` domain model. This is the same object returned by the `GET /accounts/{id}` endpoint.

| Field | Type | Nullable | Source Agent |
|-------|------|----------|-------------|
| `id` | `str` | no | BaseEntity (auto UUID) |
| `company` | `CompanyProfile` | no | EnrichmentAgent |
| `persona` | `PersonaInference` | yes | PersonaAgent |
| `intent` | `IntentScore` | yes | IntentScorerAgent |
| `tech_stack` | `TechStack` | yes | TechStackAgent |
| `business_signals` | `BusinessSignals` | yes | SignalsAgent |
| `leadership` | `LeadershipProfile` | yes | LeadershipAgent |
| `playbook` | `SalesPlaybook` | yes | PlaybookAgent |
| `ai_summary` | `str` | no | SummaryAgent |
| `analyzed_at` | `str` | no | auto (ISO 8601) |
| `confidence_score` | `float` | no | SummaryAgent (weighted avg) |
| `reasoning_trace` | `list[str]` | no | All agents (merged) |
| `created_at` | `str` | no | BaseEntity |

### 3.2 Nested Object Schemas

**CompanyProfile** (always present):

| Field | Type | Nullable | Indexed |
|-------|------|----------|---------|
| `company_name` | `str` | no | yes (for list filtering) |
| `domain` | `str` | yes | yes (dedup key) |
| `industry` | `str` | yes | yes (for list filtering) |
| `company_size_estimate` | `str` | yes | no |
| `headquarters` | `str` | yes | no |
| `founding_year` | `int` | yes | no |
| `description` | `str` | yes | no |
| `annual_revenue_range` | `str` | yes | no |
| `confidence_score` | `float` | no | no |
| `data_sources` | `list[str]` | no | no |

**PersonaInference** (null if company-only flow):

| Field | Type | Nullable |
|-------|------|----------|
| `likely_role` | `str` | no |
| `department` | `str` | yes |
| `seniority_level` | `SeniorityLevel` | no |
| `behavioral_signals` | `list[str]` | no |
| `confidence_score` | `float` | no |

**IntentScore** (null if company-only flow):

| Field | Type | Nullable |
|-------|------|----------|
| `intent_score` | `float` | no (0.0–10.0) |
| `intent_stage` | `IntentStage` | no |
| `signals_detected` | `list[str]` | no |
| `page_score_breakdown` | `dict[str, float]` | no |
| `confidence_score` | `float` | no |

**TechStack** (null if detection failed):

| Field | Type | Nullable |
|-------|------|----------|
| `technologies` | `list[Technology]` | no |
| `detection_method` | `str` | no |
| `confidence_score` | `float` | no |

**BusinessSignals** (null if search found nothing):

| Field | Type | Nullable |
|-------|------|----------|
| `signals` | `list[Signal]` | no |
| `confidence_score` | `float` | no |

**LeadershipProfile** (null if discovery failed):

| Field | Type | Nullable |
|-------|------|----------|
| `leaders` | `list[Leader]` | no |
| `confidence_score` | `float` | no |

**SalesPlaybook** (null if insufficient data):

| Field | Type | Nullable |
|-------|------|----------|
| `priority` | `Priority` | no |
| `recommended_actions` | `list[RecommendedAction]` | no |
| `talking_points` | `list[str]` | no |
| `outreach_template` | `str` | yes |
| `confidence_score` | `float` | no |

### 3.3 Operations

| Operation | Signature | Complexity | Notes |
|-----------|-----------|-----------|-------|
| `save` | `(intelligence: AccountIntelligence) → str` | O(1) | Returns account_id (= intelligence.id) |
| `get` | `(account_id: str) → Optional[AccountIntelligence]` | O(1) | Returns None if not found |
| `list` | `(page: int, page_size: int) → tuple[list, int]` | O(n) | Sorted by analyzed_at desc |

---

## 4. Mapping: Store → API Response

### 4.1 JobRecord → JobStatusResponse

```
JobRecord.job_id          → response.job_id
JobRecord.status          → response.status
JobRecord.progress        → response.progress
JobRecord.current_step    → response.current_step
JobRecord.result_id       → response.result_id
JobRecord.error           → response.error
JobRecord.created_at      → response.created_at
JobRecord.updated_at      → response.updated_at
```

Direct 1:1 mapping. No transformation needed.

### 4.2 AccountIntelligence → AccountIntelligenceResponse

```
AccountIntelligence.id                → response.account_id
AccountIntelligence.company           → response.company (direct embed)
AccountIntelligence.persona           → response.persona (direct embed, nullable)
AccountIntelligence.intent            → response.intent (direct embed, nullable)
AccountIntelligence.tech_stack        → response.tech_stack (direct embed, nullable)
AccountIntelligence.business_signals  → response.business_signals (direct embed, nullable)
AccountIntelligence.leadership        → response.leadership (direct embed, nullable)
AccountIntelligence.playbook          → response.playbook (direct embed, nullable)
AccountIntelligence.ai_summary        → response.ai_summary
AccountIntelligence.analyzed_at       → response.analyzed_at
AccountIntelligence.confidence_score  → response.confidence_score
AccountIntelligence.reasoning_trace   → response.reasoning_trace
```

Direct 1:1 mapping. The domain model IS the response shape (via `model_validate`).

### 4.3 AccountIntelligence → AccountSummary (for list endpoint)

```
AccountIntelligence.id                       → summary.account_id
AccountIntelligence.company.company_name     → summary.company_name
AccountIntelligence.company.domain           → summary.domain
AccountIntelligence.company.industry         → summary.industry
AccountIntelligence.intent?.intent_score     → summary.intent_score (null if no intent)
AccountIntelligence.intent?.intent_stage     → summary.intent_stage (null if no intent)
AccountIntelligence.playbook?.priority       → summary.priority (null if no playbook)
AccountIntelligence.confidence_score         → summary.confidence_score
AccountIntelligence.analyzed_at              → summary.analyzed_at
```

This is a **projection** — a read-only subset of the full object. The API layer constructs this from the stored AccountIntelligence.

---

## 5. Implementation Details

### 5.1 PostgreSQL Backend (Production)

- File: `backend/storage/postgres_store.py`
- Driver: `asyncpg` — native async PostgreSQL driver, no ORM
- Connection pool: `asyncpg.create_pool(min_size=2, max_size=10)` — created once at startup, shared across all requests
- `accounts.data` column is `JSONB` — stores full `AccountIntelligence` via `model_dump_json()`; deserialized on read via `model_validate_json()`
- Denormalized columns (`company_name`, `domain`, `industry`, `confidence_score`, `analyzed_at`) enable efficient listing without JSON parsing
- Upsert via `INSERT ... ON CONFLICT (account_id) DO UPDATE SET ...`
- Tables created automatically on startup via `CREATE TABLE IF NOT EXISTS`
- Pool closed gracefully on server shutdown
- Activated when `DATABASE_URL` starts with `postgresql://` or `postgres://`

**Why PostgreSQL was added:** Railway's free plan uses an ephemeral filesystem — the `data/fello.db` SQLite file is wiped on every deployment. PostgreSQL (via Railway's managed Postgres addon) provides a persistent external store that survives restarts and redeployments.

### 5.2 SQLite Backend (Local Development)

- File: `backend/storage/sqlite_store.py`
- Driver: `aiosqlite` (async wrapper around Python's built-in `sqlite3`)
- Each operation opens and closes a connection (simple, no pooling)
- `accounts.data` column stores full `AccountIntelligence` as JSON via `model_dump_json()`
- Deserialized on read via `AccountIntelligence.model_validate_json()`
- Denormalized columns (`company_name`, `domain`, `industry`, `confidence_score`) enable efficient listing without JSON parsing
- Database file at `data/fello.db` (created automatically on startup)
- Activated when `DATABASE_URL` starts with `sqlite:///`

### 5.3 In-Memory Backend (Fallback / Testing)

```python
class InMemoryJobStore(AbstractJobStore):
    _store: dict[str, JobRecord]       # key = job_id
    _lock: asyncio.Lock

class InMemoryAccountStore(AbstractAccountStore):
    _store: dict[str, AccountIntelligence]  # key = account_id
    _lock: asyncio.Lock
```

- Activated by setting `DATABASE_URL=none` or leaving it unset
- Data lost on server restart
- Useful for unit testing or when no database is available

### 5.4 Store Selection (main.py lifespan)

On startup, `backend/main.py` lifespan checks `settings.DATABASE_URL`:

```
DATABASE_URL starts with postgresql:// or postgres://
    → init_postgres(url) creates asyncpg pool + tables
    → job_store = PostgresJobStore(pool)
    → account_store = PostgresAccountStore(pool)

DATABASE_URL starts with sqlite:///
    → init_db(url) creates file + tables
    → job_store = SQLiteJobStore(url)
    → account_store = SQLiteAccountStore(url)

DATABASE_URL is None, empty, or "none"
    → keep default InMemoryJobStore / InMemoryAccountStore
```

If any backend fails to initialize, the lifespan logs the error and falls back to in-memory stores. The server still starts.

### 5.5 URL Normalization

Railway provides `DATABASE_URL` as `postgres://...` but `asyncpg` requires `postgresql://...`. The `normalize_database_url` validator in `backend/config.py` rewrites the scheme automatically:

```python
if stripped.startswith("postgres://"):
    stripped = "postgresql://" + stripped[len("postgres://"):]
```

This means Railway's auto-injected `DATABASE_URL` works without any manual intervention.

### 5.6 Concurrency Safety

- **PostgreSQL**: `asyncpg` connection pool handles concurrent access natively; each coroutine acquires a connection from the pool
- **SQLite**: SQLite handles its own locking; each operation opens a separate connection with a 30s timeout
- **In-memory**: `asyncio.Lock` protects concurrent writes

---

## 6. Database Schema (Shared: PostgreSQL and SQLite)

Both backends use the same logical schema. The only differences are SQL type names (`DOUBLE PRECISION` vs `REAL`, `JSONB` vs `JSON`) and parameterization style (`$1` vs `?`).

### 6.1 Schema SQL (PostgreSQL)

```sql
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
```

### 6.2 Schema SQL (SQLite)

```sql
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
```

### 6.3 Design Decisions

- `accounts.data` stores the full `AccountIntelligence` as a JSON/JSONB blob (`model_dump_json()` / `model_validate_json()`) — avoids a complex relational schema for a deeply nested domain model
- Top-level columns (`company_name`, `domain`, `industry`, `confidence_score`, `analyzed_at`) are denormalized for efficient listing/filtering without parsing the full JSON blob
- `jobs` table stores flat fields directly — no JSON blob needed
- No migrations framework — `CREATE TABLE IF NOT EXISTS` is sufficient for hackathon scope
- Timestamps stored as ISO 8601 strings (not native `TIMESTAMP`) for portability across SQLite and Postgres

### 6.4 Configuration Reference

```env
# Production (Railway Postgres)
DATABASE_URL=postgresql://user:pass@host:5432/dbname

# Railway auto-injects as postgres:// — config.py normalizes it automatically
DATABASE_URL=postgres://user:pass@host:5432/dbname

# Local development (SQLite)
DATABASE_URL=sqlite:///data/fello.db

# No persistence (in-memory, data lost on restart)
DATABASE_URL=none
```

### 6.5 Dependencies

| Backend | Python package | Version |
|---------|---------------|---------|
| PostgreSQL | `asyncpg` | `>=0.29.0` |
| SQLite | `aiosqlite` | `>=0.20.0` |
| In-memory | (stdlib only) | — |
