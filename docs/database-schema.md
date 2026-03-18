# Database Schema — Fello AI Account Intelligence System

> **Version**: 1.0  
> **Date**: 2026-03-18  
> **Storage Engine**: In-memory Python dicts (hackathon scope)  
> **Depends on**: [LLD](./lld.md), [API Contracts](./api-contracts.md)

---

## 1. Storage Architecture

The system uses **in-memory dict-based stores** protected by `asyncio.Lock`. All store methods are `async def` so the interface is migration-ready for PostgreSQL/Redis without changing callers.

```
┌─────────────────────────────────────────────────────────┐
│                    Storage Layer                         │
│                                                         │
│  ┌─────────────────┐       ┌──────────────────────┐    │
│  │    JobStore      │       │   AccountStore        │    │
│  │                  │       │                       │    │
│  │  dict[str,       │  ref  │  dict[str,            │    │
│  │    JobRecord]    │──────▶│    AccountIntelligence]│    │
│  │                  │       │                       │    │
│  │  key: job_id     │       │  key: account_id      │    │
│  └─────────────────┘       └──────────────────────┘    │
│                                                         │
│  Both stores: module-level singletons                   │
│  Concurrency: asyncio.Lock per store                    │
└─────────────────────────────────────────────────────────┘
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

## 5. In-Memory Implementation Details

### 5.1 Internal Data Structure

```python
class InMemoryJobStore:
    _jobs: dict[str, JobRecord]       # key = job_id
    _lock: asyncio.Lock

class InMemoryAccountStore:
    _accounts: dict[str, AccountIntelligence]  # key = account_id
    _lock: asyncio.Lock
```

### 5.2 Concurrency Safety

- Every `create`/`update`/`save` acquires the lock before writing
- `get` operations can read without locking (Python dict reads are atomic for immutable values)
- `list` acquires lock to ensure consistent snapshot during pagination

### 5.3 Memory Constraints

For hackathon scope (< 100 accounts):
- Each AccountIntelligence: ~2–5 KB serialized
- 100 accounts: ~500 KB total
- No eviction policy needed

### 5.4 Data Lifetime

- Data persists only while the backend process runs
- Server restart = clean slate (acceptable for hackathon)
- No persistence to disk

---

## 6. Future Migration Path (Post-Hackathon)

If migrating to a real database, the async interface means zero changes to controllers/graph:

| Current | Future | Migration Effort |
|---------|--------|-----------------|
| `dict[str, JobRecord]` | PostgreSQL `jobs` table | Replace store implementation only |
| `dict[str, AccountIntelligence]` | PostgreSQL `accounts` table + JSON columns | Replace store implementation only |
| `asyncio.Lock` | DB connection pool + transactions | Automatic via async ORM |
| Module singleton | FastAPI dependency injection | Minor refactor |

### 6.1 Potential PostgreSQL Schema

```sql
CREATE TABLE jobs (
    job_id UUID PRIMARY KEY,
    status VARCHAR(20) NOT NULL DEFAULT 'PENDING',
    progress FLOAT NOT NULL DEFAULT 0.0,
    current_step VARCHAR(200),
    result_id UUID REFERENCES accounts(account_id),
    error VARCHAR(500),
    analysis_type VARCHAR(20) NOT NULL,
    batch_id UUID,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX idx_jobs_status ON jobs(status);
CREATE INDEX idx_jobs_batch_id ON jobs(batch_id) WHERE batch_id IS NOT NULL;

CREATE TABLE accounts (
    account_id UUID PRIMARY KEY,
    company_name VARCHAR(200) NOT NULL,
    domain VARCHAR(200),
    industry VARCHAR(100),
    intelligence JSONB NOT NULL,
    confidence_score FLOAT NOT NULL DEFAULT 0.0,
    analyzed_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX idx_accounts_company ON accounts(company_name);
CREATE INDEX idx_accounts_domain ON accounts(domain) WHERE domain IS NOT NULL;
CREATE INDEX idx_accounts_analyzed ON accounts(analyzed_at DESC);
```

This is provided for reference only — the hackathon implementation uses in-memory dicts.
