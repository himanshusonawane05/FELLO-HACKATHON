# System Architecture — Fello AI Account Intelligence

> **Version**: 1.0  
> **Date**: 2026-03-19  
> **Author**: Senior Backend + Systems Engineer review  
> **Audience**: Hackathon judges, demo operators, interviewers, onboarding engineers

This document is the single source of truth for understanding the Fello AI Account Intelligence system end-to-end — from a browser click to a stored, rendered sales intelligence report.

---

## Table of Contents

1. [High-Level System Overview](#1-high-level-system-overview)
2. [Module-wise Breakdown](#2-module-wise-breakdown)
3. [Agent Pipeline Flow](#3-agent-pipeline-flow)
4. [Data Model & Persistence](#4-data-model--persistence)
5. [System Design Decisions](#5-system-design-decisions)
6. [Deployment Architecture](#6-deployment-architecture)
7. [Sequence Flow (Request Lifecycle)](#7-sequence-flow-request-lifecycle)
8. [Cross-check with Existing Docs](#8-cross-check-with-existing-docs)
9. [Deployment.md Updates](#9-deploymentmd-updates)
10. [Future Scalability & Production Architecture](#10-future-scalability--production-architecture)

---

## 1. High-Level System Overview

### 1.1 End-to-End Flow

```
┌───────────────────────────────────────────────────────────────────────────────┐
│                         BROWSER (Next.js 14)                                  │
│  ┌──────────┐ ┌──────────────┐ ┌────────────────┐ ┌────────────────────────┐ │
│  │Dashboard │ │AnalysisForm  │ │VisitorScenarios│ │ Account Detail View    │ │
│  │  (list)  │ │(visitor/co.) │ │ (demo presets) │ │ (full intelligence)    │ │
│  └──────────┘ └──────────────┘ └────────────────┘ └────────────────────────┘ │
│                    │ all calls via lib/api.ts                                 │
└────────────────────┼─────────────────────────────────────────────────────────┘
                     │ HTTPS / JSON
                     ▼
┌───────────────────────────────────────────────────────────────────────────────┐
│                    FASTAPI BACKEND (Uvicorn, async)                           │
│                                                                              │
│  ┌──────────────┐  ┌────────────────────────────┐  ┌──────────────────────┐ │
│  │  API Routes   │→│  AnalysisController         │→│  LangGraph Pipeline  │ │
│  │  (thin HTTP)  │  │  (job creation, dispatch)   │  │  (multi-agent DAG)  │ │
│  └──────────────┘  └────────────────────────────┘  └─────────┬────────────┘ │
│                                                               │              │
│                    ┌──────────────────────────────────────────┘              │
│                    ▼                                                         │
│  ┌──────────────────────────────────────────────────────────────────────┐    │
│  │  AGENTS (9 specialized workers)                                      │    │
│  │  ┌──────────┐ ┌──────────┐ ┌──────────┐ ┌──────────┐ ┌──────────┐  │    │
│  │  │Identific.│ │Enrichment│ │ Persona  │ │  Intent  │ │TechStack │  │    │
│  │  └──────────┘ └──────────┘ └──────────┘ └──────────┘ └──────────┘  │    │
│  │  ┌──────────┐ ┌──────────┐ ┌──────────┐ ┌──────────┐              │    │
│  │  │ Signals  │ │Leadership│ │ Playbook │ │ Summary  │              │    │
│  │  └──────────┘ └──────────┘ └──────────┘ └──────────┘              │    │
│  └──────────────────────────────┬───────────────────────────────────────┘    │
│                                 │ uses                                       │
│                    ┌────────────┼────────────┐                               │
│                    ▼            ▼            ▼                               │
│              ┌──────────┐ ┌──────────┐ ┌──────────────┐                     │
│              │ Tools    │ │ LLM Svc  │ │  Storage     │                     │
│              │ (I/O)    │ │ (Gemini/ │ │ (Postgres/   │                     │
│              │          │ │  OpenAI) │ │  SQLite/Mem) │                     │
│              └──────────┘ └──────────┘ └──────────────┘                     │
└───────────────────────────────────────────────────────────────────────────────┘
```

### 1.2 Key Design Decisions

| Decision | Rationale |
|----------|-----------|
| **Fully async (FastAPI + asyncio)** | Non-blocking I/O for concurrent LLM/tool calls; single-process handles many jobs |
| **Multi-agent pipeline via LangGraph** | Each intelligence dimension (enrichment, intent, persona, tech, signals, leadership) is an isolated, testable agent |
| **Background task + polling** | Analysis takes 15–65s; HTTP 202 + job polling avoids timeouts |
| **Three-tier storage (Postgres → SQLite → In-Memory)** | Production persistence on Railway, local dev persistence, zero-dep fallback |
| **Gemini primary, OpenAI fallback** | Gemini 2.5 Flash is cost-effective; OpenAI as reliability net |
| **Tool + LLM hybrid** | Real data from APIs (IP lookup, Tavily search) grounds LLM reasoning |

---

## 2. Module-wise Breakdown

### 2.1 `backend/main.py` — App Lifecycle & Dependency Wiring

**Responsibility:** FastAPI app factory, lifespan management, storage selection, CORS configuration.

**Lifecycle (startup):**
1. Log environment source, masked API keys, model names, CORS origins
2. Read `DATABASE_URL` from config
3. **Storage selection logic:**
   - `postgresql://` or `postgres://` → import & init `PostgresJobStore` + `PostgresAccountStore` via `asyncpg` pool
   - `sqlite:///...` → import & init `SQLiteJobStore` + `SQLiteAccountStore` via `aiosqlite`
   - `none` or empty → keep default `InMemoryJobStore` + `InMemoryAccountStore`
   - On any init failure → fall back to in-memory with a warning
4. Module-level singletons `job_store` and `account_store` are **swapped at startup** — no downstream code needs to know which backend is active

**Lifecycle (shutdown):**
- Close `asyncpg` connection pool if Postgres was initialized

**Key pattern:** Storage modules (`job_store.py`, `account_store.py`) export a module-level `job_store` / `account_store` variable. `main.py` replaces these variables during startup. All other code imports from the module, so the swap is transparent.

### 2.2 Storage Layer

```
backend/storage/
├── base.py              # AbstractJobStore, AbstractAccountStore (ABCs)
├── job_store.py          # InMemoryJobStore + JobRecord + JobStatus
├── account_store.py      # InMemoryAccountStore
├── sqlite_store.py       # SQLiteJobStore + SQLiteAccountStore
└── postgres_store.py     # PostgresJobStore + PostgresAccountStore
```

| Backend | Activation Condition | Library | Pool/Connection | Use Case |
|---------|---------------------|---------|-----------------|----------|
| **PostgreSQL** | `DATABASE_URL` starts with `postgresql://` or `postgres://` | `asyncpg` | Pool (min=2, max=10) | Railway production |
| **SQLite** | `DATABASE_URL` starts with `sqlite:///` | `aiosqlite` | Per-query connection (timeout=30s) | Local dev |
| **In-Memory** | `DATABASE_URL=none` or empty or init failure | Python `dict` | `asyncio.Lock` | Zero-dep fallback |

**Schema (shared by Postgres and SQLite):**

```sql
-- Jobs table (flat)
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

-- Accounts table (JSONB blob + denormalized columns)
CREATE TABLE IF NOT EXISTS accounts (
    account_id TEXT PRIMARY KEY,
    company_name TEXT NOT NULL,
    domain TEXT,
    industry TEXT,
    confidence_score REAL NOT NULL DEFAULT 0.0,
    analyzed_at TEXT NOT NULL,
    data JSONB NOT NULL          -- Postgres: JSONB / SQLite: JSON
);
CREATE INDEX IF NOT EXISTS idx_accounts_analyzed ON accounts(analyzed_at DESC);
```

### 2.3 Agents

All agents extend `BaseAgent` (`backend/agents/base_agent.py`) which provides:
- `agent_name: ClassVar[str]` — unique identifier
- `run(input: BaseEntity) -> BaseEntity` — main execution (must never raise)
- `validate_input(input: BaseEntity) -> bool` — precondition check
- `_timed_call(task_name)` — async context manager for LLM call timing/logging

| Agent | File | Input | Output | LLM? | Tools | Responsibility |
|-------|------|-------|--------|------|-------|----------------|
| **IdentificationAgent** | `identification.py` | `VisitorSignal` | `CompanyInput` | No | `IPLookupTool`, `WebSearchTool` | Resolve IP → company name. Detects private IPs, cloud providers. Returns "Unknown" if unresolvable. |
| **EnrichmentAgent** | `enrichment.py` | `CompanyInput` | `CompanyProfile` | Yes (Gemini) | `WebSearchTool` | Tavily search for company data → LLM synthesis into structured profile. Min confidence 0.4 for identified companies. |
| **PersonaAgent** | `persona.py` | `VisitorSignal` | `PersonaInference` | Yes (Gemini) | None | LLM infers likely role, department, seniority from page-visit patterns. Rule-based fallback on LLM failure. |
| **IntentScorerAgent** | `intent_scorer.py` | `VisitorSignal` | `IntentScore` | No | None | Pure rule-based: weighted page scores + visit count bonus + time-on-site bonus → 0–10 score + buying stage. |
| **TechStackAgent** | `tech_stack.py` | `CompanyProfile` | `TechStack` | Yes (Gemini) | None | LLM infers likely tech stack from company profile. Skips for unknown/low-confidence companies. |
| **SignalsAgent** | `signals.py` | `CompanyProfile` | `BusinessSignals` | Yes (Gemini) | `WebSearchTool` | Tavily search for recent news/hiring/funding → LLM extraction. Skips for unknown companies. |
| **LeadershipAgent** | `leadership.py` | `CompanyProfile` | `LeadershipProfile` | Yes (Gemini) | `WebSearchTool` | Tavily search for C-suite/VP leaders → LLM extraction. Skips for unknown companies. |
| **PlaybookAgent** | `playbook.py` | `AccountIntelligence` | `SalesPlaybook` | Yes (Gemini) | None | LLM synthesizes prioritized sales strategy from all prior intelligence. Rule-based fallback. |
| **SummaryAgent** | `summary.py` | `AccountIntelligence` | `AccountIntelligence` | Yes (Gemini) | None | LLM generates executive briefing narrative. Assembles final aggregate model. Computes overall confidence. |

### 2.4 Controllers

**`AnalysisController`** (`backend/controllers/analysis.py`):

Single controller bridging HTTP and pipeline. Module-level singleton `analysis_controller`.

| Method | Purpose | Returns |
|--------|---------|---------|
| `analyze_visitor(signal)` | Create job → dispatch pipeline as `asyncio.create_task` | `JobRecord` |
| `analyze_company(input)` | Create job → dispatch pipeline as `asyncio.create_task` | `JobRecord` |
| `analyze_batch(inputs)` | Create batch job + per-company jobs | `(JobRecord, list[str])` |
| `get_job_status(job_id)` | Read from job store | `Optional[JobRecord]` |
| `get_account(account_id)` | Read from account store | `Optional[AccountIntelligence]` |
| `list_accounts(page, size)` | Paginated list from account store | `(list, int)` |

**`_run_pipeline(job_id, ...)`** is the background task:
1. Update job status to PROCESSING
2. Build initial `PipelineState` dict
3. Invoke `compiled_workflow.ainvoke(state)`
4. On success: save `AccountIntelligence` to account store, mark job COMPLETED with `result_id`
5. On failure: mark job FAILED with error message

### 2.5 Tools

All tools extend `BaseTool` (`backend/tools/base_tool.py`) which provides:
- `tool_name: ClassVar[str]` — identifier
- `call(**kwargs) -> Optional[dict]` — must return `None` on failure, never raise
- `@cached_call(ttl=300)` — decorator caching results by SHA-256 hash of kwargs

| Tool | File | External Service | Fallback | Cache TTL |
|------|------|-----------------|----------|-----------|
| **IPLookupTool** | `ip_lookup.py` | ipapi.co → ip-api.com | Second provider | 300s |
| **WebSearchTool** | `web_search.py` | Tavily API | `None` | 300s |
| **ScraperTool** | `scraper.py` | Direct HTTP + BeautifulSoup | `None` | 300s |
| **EnrichmentAPITool** | `enrichment_apis.py` | Clearbit → Apollo → stub | LLM fallback stub | 300s |

**Note:** `ScraperTool` and `EnrichmentAPITool` are implemented but **not called** by any agent in the current pipeline. Enrichment uses `WebSearchTool` + LLM. Tech stack uses LLM knowledge directly.

### 2.6 LLM Service

Two complementary LLM access layers exist:

**`backend/core/llm_service.py`** — The primary call path for all agent LLM work:

```
generate_json(prompt, response_model, temperature, max_tokens, max_retries)
    │
    ├── Try Gemini (google.genai SDK, response_mime_type="application/json")
    │   ├── Up to 2 retry attempts per provider
    │   ├── Token budget: max(requested * 3, 8192) for thinking-model overhead
    │   └── On failure → fall through
    │
    ├── Try OpenAI (LangChain ChatOpenAI, response_format=json_object)
    │   ├── Up to 2 retry attempts
    │   └── On failure → fall through
    │
    └── Return None (agent uses mock/rule-based fallback)
```

JSON extraction is robust: handles direct JSON, markdown fences (` ```json ... ``` `), and brace-depth extraction from prose responses.

**`backend/core/llm.py`** — LangChain model factory (`get_llm()`):
- Used by `graph/nodes.py` to pass an `llm` instance to agent constructors
- Agents accept this but call `generate_json()` directly instead of `self._llm`
- Exists for LangChain compatibility; the actual call path bypasses it

**Provider priority:**
1. **Gemini 2.5 Flash** (`GEMINI_API_KEY`) — primary, cost-effective, supports JSON mode
2. **OpenAI GPT-4o-mini** (`OPENAI_API_KEY`) — fallback for reliability

---

## 3. Agent Pipeline Flow

### 3.1 Pipeline Topology (LangGraph DAG)

```
START
  │
  ▼
route_input (conditional)
  │
  ├── [has visitor_signal] ──► identification_node ──┐
  │                                                   │
  └── [has company_input] ────────────────────────────┤
                                                      ▼
                                              stage1_node
                                    ┌─────────────┼────────────┐
                                    ▼             ▼            ▼
                              enrichment     persona     intent_scorer
                              (Tavily+LLM)   (LLM)       (rule-based)
                                    └─────────────┼────────────┘
                                                  ▼
                                              stage2_node
                                    ┌─────────────┼────────────┐
                                    ▼             ▼            ▼
                              tech_stack     signals      leadership
                              (LLM)         (Tavily+LLM)  (Tavily+LLM)
                                    └─────────────┼────────────┘
                                                  ▼
                                          playbook_node (LLM)
                                                  │
                                                  ▼
                                          summary_node (LLM)
                                                  │
                                                  ▼
                                                 END
```

**Parallelism:** `stage1_node` and `stage2_node` each use `asyncio.gather()` internally to run their child agents concurrently. LangGraph sees them as single sequential nodes.

### 3.2 Step-by-Step Execution

#### Visitor Signal Input (`POST /api/v1/analyze/visitor`)

| Step | Progress | Node | What Happens |
|------|----------|------|--------------|
| 1 | 0.02 | — | Job created as PENDING, background task dispatched |
| 2 | 0.05 | `identification_node` | IP lookup via ipapi.co/ip-api.com. Cloud provider check. Tavily search (conservative). Produces `CompanyInput`. |
| 3 | 0.15–0.20 | `stage1_node` | **Parallel:** EnrichmentAgent (Tavily + LLM → `CompanyProfile`), PersonaAgent (LLM → `PersonaInference`), IntentScorerAgent (rules → `IntentScore`) |
| 4 | 0.50–0.55 | `stage2_node` | **Parallel:** TechStackAgent (LLM → `TechStack`), SignalsAgent (Tavily + LLM → `BusinessSignals`), LeadershipAgent (Tavily + LLM → `LeadershipProfile`) |
| 5 | 0.80–0.82 | `playbook_node` | PlaybookAgent assembles all prior outputs → LLM generates `SalesPlaybook` |
| 6 | 0.90–0.92 | `summary_node` | SummaryAgent assembles all outputs → LLM generates narrative → final `AccountIntelligence` |
| 7 | 1.0 | — | `AccountIntelligence` saved to account store. Job marked COMPLETED with `result_id`. |

#### Company Name Input (`POST /api/v1/analyze/company`)

Same as above but **skips `identification_node`** — starts directly at `stage1_node` with the provided `CompanyInput`.

### 3.3 When Company IS Identified

```
IP: 208.80.154.1
  ↓
IPLookupTool → org: "Wikimedia Foundation", is_cloud_provider: false
  ↓
CompanyInput(company_name="Wikimedia Foundation")
  ↓
EnrichmentAgent → Tavily search "Wikimedia Foundation company overview..."
                → LLM synthesis → CompanyProfile(confidence_score=0.85)
  ↓
[All Stage 2 agents run with high-confidence profile]
  ↓
TechStack: [MediaWiki, PHP, MySQL, Varnish, ...]
Signals: [Fundraising campaign, engineering hiring, ...]
Leadership: [Jimmy Wales (Founder), Maryana Iskander (CEO), ...]
  ↓
PlaybookAgent: HIGH priority, 4 targeted actions
SummaryAgent: Full executive briefing with specific data points
```

### 3.4 When Company is NOT Identified

```
IP: 34.201.45.12
  ↓
IPLookupTool → org: "Amazon Technologies", is_cloud_provider: true
  ↓
CompanyInput(company_name="Unknown")
  ↓
EnrichmentAgent → CompanyProfile(confidence_score=0.1, all fields null)
  ↓
[Stage 2 agents check confidence_score < 0.3 → skip]
  ↓
TechStack: empty (skipped)
Signals: empty (skipped)
Leadership: empty (skipped)
  ↓
PlaybookAgent: LOW priority, single action: "Identify visitor's company"
SummaryAgent: "The visitor's company could not be identified from their IP..."
```

### 3.5 Data Passed Between Agents

```
PipelineState (TypedDict) — shared mutable state bag
  │
  ├── visitor_signal: VisitorSignal          ← input (visitor path)
  ├── company_input: CompanyInput            ← input (company path)
  │
  ├── identified_company: CompanyInput       ← identification_node output
  ├── company_profile: CompanyProfile        ← stage1_node (enrichment)
  ├── persona: PersonaInference              ← stage1_node (persona)
  ├── intent: IntentScore                    ← stage1_node (intent)
  │
  ├── tech_stack: TechStack                  ← stage2_node
  ├── business_signals: BusinessSignals      ← stage2_node
  ├── leadership: LeadershipProfile          ← stage2_node
  │
  ├── playbook: SalesPlaybook                ← playbook_node
  ├── intelligence: AccountIntelligence      ← summary_node (final output)
  │
  ├── job_id: str                            ← metadata
  ├── errors: list[str]                      ← accumulated errors (Annotated + operator.add)
  └── reasoning_trace: list[str]             ← accumulated trace (Annotated + operator.add)
```

---

## 4. Data Model & Persistence

### 4.1 Domain Models (Pydantic v2, Frozen)

All models extend `BaseEntity`:

```python
class BaseEntity(BaseModel):
    model_config = ConfigDict(frozen=True)
    id: str = Field(default_factory=lambda: str(uuid4()))
    created_at: str = Field(default_factory=lambda: datetime.utcnow().isoformat())
```

**Model hierarchy:**

```
BaseEntity
├── VisitorSignal          (input: IP, pages, behavior)
├── CompanyInput           (input: company name + optional domain)
├── CompanyProfile         (enrichment output)
├── PersonaInference       (persona agent output)
├── IntentScore            (intent scorer output)
├── TechStack              (tech stack agent output)
│   └── Technology         (individual tech item)
├── BusinessSignals        (signals agent output)
│   └── Signal             (individual signal)
├── LeadershipProfile      (leadership agent output)
│   └── Leader             (individual leader)
├── SalesPlaybook          (playbook agent output)
│   └── RecommendedAction  (individual action)
└── AccountIntelligence    (aggregate root — final output)
```

**`AccountIntelligence`** is the aggregate root that holds references to all other models:

```python
class AccountIntelligence(BaseEntity):
    company: CompanyProfile
    persona: Optional[PersonaInference]
    intent: Optional[IntentScore]
    tech_stack: Optional[TechStack]
    business_signals: Optional[BusinessSignals]
    leadership: Optional[LeadershipProfile]
    playbook: Optional[SalesPlaybook]
    ai_summary: str
    analyzed_at: str
    confidence_score: float      # weighted average of sub-agent scores
    reasoning_trace: list[str]   # accumulated chain-of-thought
```

### 4.2 Jobs Table

Tracks async pipeline execution state for polling.

| Column | Type | Purpose |
|--------|------|---------|
| `job_id` | TEXT PK | UUID assigned at creation |
| `status` | TEXT | PENDING → PROCESSING → COMPLETED / FAILED |
| `progress` | REAL | 0.0 → 1.0 (updated by each pipeline node) |
| `current_step` | TEXT | Human-readable step name for UI display |
| `result_id` | TEXT | `AccountIntelligence.id` when COMPLETED |
| `error` | TEXT | Error message when FAILED |
| `created_at` | TEXT | ISO timestamp |
| `updated_at` | TEXT | ISO timestamp (updated on every state change) |

### 4.3 Accounts Table

Stores completed analysis results. The `data` column holds the full `AccountIntelligence` as serialized JSON. Denormalized columns enable efficient listing/filtering without deserializing the blob.

| Column | Type | Purpose |
|--------|------|---------|
| `account_id` | TEXT PK | Same as `AccountIntelligence.id` |
| `company_name` | TEXT | Denormalized for listing |
| `domain` | TEXT | Denormalized for filtering |
| `industry` | TEXT | Denormalized for filtering |
| `confidence_score` | REAL | Denormalized for sorting |
| `analyzed_at` | TEXT | ISO timestamp, indexed DESC for recency |
| `data` | JSONB (Postgres) / JSON (SQLite) | Full `AccountIntelligence` blob |

### 4.4 asyncpg Connection Pooling (PostgreSQL)

```python
pool = await asyncpg.create_pool(database_url, min_size=2, max_size=10)
```

- **`min_size=2`**: Two connections kept warm for immediate availability
- **`max_size=10`**: Cap at 10 to avoid overwhelming Railway's Postgres (shared infra)
- Each store method calls `async with self._pool.acquire() as conn:` to borrow a connection
- Pool is created once during app startup and closed on shutdown
- Tables are created via `CREATE TABLE IF NOT EXISTS` on the first acquired connection

### 4.5 Why PostgreSQL Replaced SQLite

**Problem:** Railway uses ephemeral containers. Every deployment wipes the filesystem, including `data/fello.db`. All analyzed accounts and in-flight jobs were lost.

**Why not persistent volumes?** Railway's free/hobby plan does not offer persistent volumes. Even on paid plans, persistent volumes add operational complexity.

**Solution:** Railway provides a managed PostgreSQL addon that survives deployments. The app detects `DATABASE_URL=postgresql://...` (auto-injected by Railway) and uses `asyncpg` instead of `aiosqlite`. SQLite remains available for local dev.

---

## 5. System Design Decisions

### 5.1 Why Async FastAPI

- **Concurrent LLM calls:** Each analysis triggers 6+ LLM calls (Gemini API latency ~8–15s each). Async allows multiple analyses to run concurrently without thread-pool exhaustion.
- **Background tasks:** `asyncio.create_task()` dispatches the pipeline without blocking the HTTP response. The client gets `202 Accepted` instantly.
- **Single-process simplicity:** No need for Celery, Redis, or a task queue. A single Uvicorn process handles both HTTP and pipeline execution.

### 5.2 Why Multi-Agent Architecture

- **Separation of concerns:** Each intelligence dimension (enrichment, intent, persona, tech, signals, leadership, playbook, summary) is an isolated agent with clear input/output contracts.
- **Graceful degradation:** If one agent fails, others still produce results. `AccountIntelligence` has `Optional` fields for every sub-model.
- **Parallel execution:** Independent agents run concurrently via `asyncio.gather`. Stage 1 (enrichment + persona + intent) and Stage 2 (tech + signals + leadership) each run 3 agents in parallel.
- **Testability:** Each agent can be tested in isolation with mock inputs.

### 5.3 Why Tool + LLM Hybrid

- **Grounded reasoning:** Tavily search provides real, current data that the LLM synthesizes. This prevents hallucinated company details.
- **Cost control:** IP lookup and intent scoring are rule-based (zero LLM cost). Only enrichment, persona, tech stack, signals, leadership, playbook, and summary use LLM calls.
- **Reliability:** If Tavily fails, agents fall back to LLM general knowledge. If LLM fails, agents return degraded output (rule-based or empty). The pipeline never crashes.

### 5.4 Failure Handling Matrix

| Layer | Failure Type | Handling |
|-------|-------------|----------|
| **Tool** | HTTP timeout / rate limit | Retry (built-in to tool) → return `None` |
| **Tool** | API error | Log + return `None` |
| **Agent** | LLM timeout / empty response | Try Gemini → Try OpenAI → return `None` |
| **Agent** | JSON parse failure | Retry up to 2x per provider → `None` |
| **Agent** | `generate_json` returns `None` | Use rule-based fallback or return degraded model |
| **Agent** | Unexpected exception | Caught at node level → error appended to `state.errors` |
| **Pipeline** | Any node exception | Caught in `_run_pipeline` → job marked FAILED |
| **Storage** | Postgres init failure | Fall back to in-memory with warning |
| **API** | Validation error | 422 (automatic via FastAPI/Pydantic) |
| **API** | Job/Account not found | 404 with structured error |
| **Frontend** | API unreachable | Error state UI, retry button |
| **Frontend** | Polling timeout | Shows "taking longer than expected", keeps polling |

---

## 6. Deployment Architecture

### 6.1 Production (Railway)

```
┌────────────────────────────────────────────────────────────────┐
│                       RAILWAY PROJECT                          │
│                                                                │
│  ┌─────────────────────────────────────────────────────────┐  │
│  │  Backend Service                                         │  │
│  │  Start: python -m uvicorn backend.main:app               │  │
│  │         --host 0.0.0.0 --port $PORT                      │  │
│  │                                                          │  │
│  │  Env vars:                                               │  │
│  │    GEMINI_API_KEY, OPENAI_API_KEY, TAVILY_API_KEY        │  │
│  │    CORS_ORIGINS=["https://your-frontend.vercel.app"]     │  │
│  │    DATABASE_URL  (auto-injected by Railway Postgres)     │  │
│  └──────────────────────────┬──────────────────────────────┘  │
│                              │ asyncpg (TCP)                   │
│  ┌──────────────────────────▼──────────────────────────────┐  │
│  │  Railway PostgreSQL Addon                                │  │
│  │  Managed, persistent, survives deployments               │  │
│  │  DATABASE_URL=postgres://user:pass@host:5432/railway     │  │
│  └─────────────────────────────────────────────────────────┘  │
└────────────────────────────────────────────────────────────────┘

┌────────────────────────────────────────────────────────────────┐
│                         VERCEL                                 │
│  ┌─────────────────────────────────────────────────────────┐  │
│  │  Frontend (Next.js 14)                                   │  │
│  │  Root directory: frontend/                               │  │
│  │  NEXT_PUBLIC_API_URL=https://your-backend.railway.app    │  │
│  └─────────────────────────────────────────────────────────┘  │
└────────────────────────────────────────────────────────────────┘
```

### 6.2 Environment Variables

| Variable | Required | Where | Purpose |
|----------|----------|-------|---------|
| `GEMINI_API_KEY` | Yes (one of) | Backend | Gemini LLM — primary provider |
| `OPENAI_API_KEY` | Yes (one of) | Backend | OpenAI LLM — fallback provider |
| `TAVILY_API_KEY` | Yes | Backend | Web search tool |
| `DATABASE_URL` | No | Backend | Storage backend selection (default: `sqlite:///data/fello.db`) |
| `CORS_ORIGINS` | No | Backend | Allowed frontend origins (default: `http://localhost:3000`) |
| `PORT` | No | Backend | Server port (default: 8000; Railway injects this) |
| `NEXT_PUBLIC_API_URL` | Yes | Frontend | Backend URL for API calls |

### 6.3 Why DATABASE_URL Is Critical

Railway auto-injects `DATABASE_URL=postgres://user:pass@host:5432/railway` when a Postgres addon is attached. This single variable controls:

1. **Storage backend selection** — `main.py` checks the URL scheme to decide Postgres vs SQLite vs in-memory
2. **URL normalization** — Railway uses `postgres://` but asyncpg requires `postgresql://`. The config validator (`config.py`) rewrites this automatically.
3. **Data persistence** — Without this variable pointing to Postgres, Railway deployments lose all data (ephemeral filesystem wipes SQLite)

If `DATABASE_URL` is missing, misspelled, or points to an unreachable Postgres instance, the system falls back to in-memory storage with a logged warning.

### 6.4 Local Development

```bash
# Backend
pip install -r requirements.txt
mkdir data
python -m uvicorn backend.main:app --host 0.0.0.0 --port 8000 --reload

# Frontend
cd frontend && npm install && npm run dev
```

Default `DATABASE_URL=sqlite:///data/fello.db` — data persists across restarts on disk.

---

## 7. Sequence Flow (Request Lifecycle)

### 7.1 Full Visitor Analysis Lifecycle

```
Browser                    Frontend                  Backend API           Controller          Pipeline (bg task)
   │                          │                          │                    │                      │
   │  [Fill form, click       │                          │                    │                      │
   │   "Analyze"]             │                          │                    │                      │
   │─────────────────────────►│                          │                    │                      │
   │                          │  POST /analyze/visitor   │                    │                      │
   │                          │─────────────────────────►│                    │                      │
   │                          │                          │  analyze_visitor() │                      │
   │                          │                          │───────────────────►│                      │
   │                          │                          │                    │  create job (PENDING) │
   │                          │                          │                    │  asyncio.create_task()│
   │                          │                          │                    │─────────────────────►│
   │                          │                          │  ◄── JobRecord     │                      │
   │                          │  ◄── 202 {job_id}        │                    │                      │
   │  ◄── show progress bar  │                          │                    │                      │
   │                          │                          │                    │                      │
   │  [poll every 2s]         │                          │                    │                      │
   │─────────────────────────►│                          │                    │    [pipeline runs]    │
   │                          │  GET /jobs/{job_id}      │                    │    identification     │
   │                          │─────────────────────────►│───────────────────►│    → stage1 (∥3)     │
   │                          │  ◄── {progress: 0.50}   │                    │    → stage2 (∥3)     │
   │  ◄── update progress     │                          │                    │    → playbook        │
   │                          │                          │                    │    → summary         │
   │  [poll again]            │                          │                    │                      │
   │─────────────────────────►│                          │                    │    save account      │
   │                          │  GET /jobs/{job_id}      │                    │    mark COMPLETED    │
   │                          │─────────────────────────►│───────────────────►│                      │
   │                          │  ◄── {status:COMPLETED,  │                    │                      │
   │                          │       result_id: "abc"}  │                    │                      │
   │                          │                          │                    │                      │
   │                          │  GET /accounts/abc       │                    │                      │
   │                          │─────────────────────────►│───────────────────►│                      │
   │                          │  ◄── AccountIntelligence │                    │                      │
   │                          │                          │                    │                      │
   │  ◄── navigate to         │                          │                    │                      │
   │      /account/abc        │                          │                    │                      │
   │      (full detail view)  │                          │                    │                      │
```

### 7.2 Timing Breakdown

| Phase | Wall Clock | Notes |
|-------|-----------|-------|
| Job creation + HTTP response | < 50ms | Synchronous, fast |
| Identification (IP lookup) | 1–3s | Two HTTP calls (ipapi.co, ip-api.com) |
| Stage 1 (enrichment + persona + intent) | 10–20s | Parallel; bottleneck is Gemini API latency |
| Stage 2 (tech + signals + leadership) | 10–20s | Parallel; 3 Tavily searches + 3 LLM calls |
| Playbook generation | 5–10s | Single LLM call, larger prompt |
| Summary generation | 3–8s | Single LLM call |
| **Total (known company)** | **30–60s** | Dominated by LLM latency |
| **Total (unknown company)** | **15–25s** | Most Stage 2 agents skip |

---

## 8. Cross-check with Existing Docs

### 8.1 Comparison with `docs/LLD.md`

| LLD Section | LLD Says | Actual Implementation | Status |
|-------------|----------|----------------------|--------|
| §1 Directory Structure | `backend/services/` not listed | `backend/core/` exists with `llm.py` and `llm_service.py` | **MISMATCH** — LLD has no `core/` layer |
| §2 Domain Models | All 11 models listed | All 11 implemented as specified | **MATCH** |
| §3.1 BaseAgent | `__init__(llm, tools)` as call path | Agents accept `llm` but call `generate_json()` directly | **DEVIATION** — LLD implies per-agent LLM via `self._llm` |
| §3.2 Agent Table | EnrichmentAgent uses `enrichment_apis` tool | Uses `WebSearchTool` + LLM instead | **MISMATCH** |
| §4 PipelineState | `Send()` for parallel fan-out | `asyncio.gather()` inside sequential nodes | **DEVIATION** — functionally equivalent |
| §5 Tool Specs | 4 tools described | 4 tools implemented; 2 not called by any agent | **PARTIAL** |
| §7 Storage | `InMemoryJobStore`/`InMemoryAccountStore` only | + `SQLiteJobStore`/`SQLiteAccountStore` + `PostgresJobStore`/`PostgresAccountStore` | **EXTENDED** |
| §8 Config | `OPENAI_API_KEY` required | `GEMINI_API_KEY` is primary; OpenAI is fallback | **MISMATCH** |

### 8.2 Corrections Suggested for LLD.md

1. **Add `backend/core/` to directory structure** with `llm.py` and `llm_service.py`
2. **Update Agent Table (§3.2):**
   - IdentificationAgent: mark LLM as "No", tools as `IPLookupTool, WebSearchTool`
   - EnrichmentAgent: tools should be `WebSearchTool` not `enrichment_apis`
   - TechStackAgent: tools should be "None" not `scraper`
3. **Update §4 Graph Edges:** Replace `Send()` topology with `asyncio.gather` inside nodes
4. **Update §7 Storage:** Add SQLite and PostgreSQL backends alongside in-memory
5. **Update §8 Config:** Add `GEMINI_API_KEY`, `GEMINI_MODEL_NAME`, `DATABASE_URL` fields

### 8.3 Comparison with `docs/deployment.md`

| deployment.md Section | Current Content | Actual Status |
|-----------------------|----------------|---------------|
| §1 Architecture diagram | Shows only SQLite | **OUTDATED** — should show Postgres as primary, SQLite as local dev |
| §2 Component table | Database: "SQLite (aiosqlite)" | **OUTDATED** — Postgres is production backend |
| §4 SQLite File Handling | Detailed SQLite file instructions | Still valid for local dev |
| §5b Backend — Railway | Recommends persistent volume for SQLite | **OUTDATED** — should recommend Postgres addon instead |
| §5b Railway env vars | `DATABASE_URL=sqlite:////data/fello.db` | **WRONG** for Railway — should be `postgresql://` (auto-injected) |

---

## 9. Deployment.md Updates

The following changes are needed in `docs/deployment.md`:

### 9.1 Architecture Diagram (§1)

The diagram should show PostgreSQL as the production database with Railway, and SQLite as local dev only.

### 9.2 Component Table (§1)

| Component | Technology | Role |
|-----------|-----------|------|
| Frontend | Next.js 14, React 18, Tailwind CSS | UI — forms, dashboards, polling |
| Backend | FastAPI, Uvicorn, LangGraph | API, multi-agent pipeline, job management |
| Database (prod) | **PostgreSQL (asyncpg)** | **Persistent job and account storage on Railway** |
| Database (local) | SQLite (aiosqlite) | Local dev persistence |
| LLM | Gemini (primary) + OpenAI (fallback) | Agent reasoning and enrichment |
| Search | Tavily API | Web search tool used by agents |

### 9.3 New Section: PostgreSQL Setup on Railway (after §5b)

**Steps to add Railway Postgres:**

1. In the Railway dashboard, click **"New"** → **"Database"** → **"PostgreSQL"**
2. Railway auto-injects `DATABASE_URL=postgres://user:pass@host:5432/railway` as an env var
3. The backend normalizes `postgres://` → `postgresql://` automatically (config.py validator)
4. Tables are created automatically on first startup (`CREATE TABLE IF NOT EXISTS`)
5. No manual migration needed — the schema is applied on boot

**Verifying Postgres is active:**
- Backend logs will show: `Storage : PostgreSQL`
- If it shows `Storage : In-memory`, check that `DATABASE_URL` is set and the Postgres service is running

### 9.4 Updated Railway Env Vars (§5b)

```
GEMINI_API_KEY=AIzaSy...
OPENAI_API_KEY=sk-proj-...
TAVILY_API_KEY=tvly-...
DATABASE_URL=${{Postgres.DATABASE_URL}}    ← Railway reference variable
CORS_ORIGINS=["https://your-frontend.vercel.app"]
PORT=8000
```

**Remove:** `DATABASE_URL=sqlite:////data/fello.db` — this is only for local dev.  
**Remove:** Persistent Volume instructions — no longer needed with Postgres.

### 9.5 SQLite Migration Note

If you previously used SQLite on Railway with a persistent volume:
- Existing SQLite data is not automatically migrated to PostgreSQL
- To migrate: export accounts from the SQLite file, then re-analyze or import into Postgres
- For hackathon scope: re-running analyses is faster than building a migration tool

---

## 10. Future Scalability & Production Architecture

### 10.1 Current Limitations

The system is designed for hackathon-scale workloads (~10 concurrent users). Several architectural decisions that were correct for speed-to-demo become bottlenecks at production scale:

| Limitation | Root Cause | Impact at Scale |
|------------|-----------|-----------------|
| **Single-process job execution** | `asyncio.create_task()` runs pipelines inside the web server process | A burst of 50 analyses saturates the event loop; HTTP latency degrades for all users |
| **No job durability** | In-flight jobs live in-memory as asyncio Tasks | Server restart or OOM kill loses all running analyses; no retry mechanism |
| **Synchronous polling** | Frontend polls `GET /jobs/{id}` every 2 seconds | Wasted bandwidth; delayed user feedback; O(n) polling load with n active jobs |
| **Unbounded LLM concurrency** | No semaphore/throttle on outgoing Gemini/OpenAI calls | 20 parallel analyses × 7 LLM calls each = 140 concurrent API requests → rate limiting, cost spikes |
| **No caching layer** | Tool-level `@cached_call(ttl=300)` is per-process in-memory dict | Each worker/restart starts cold; identical company analyses repeat all external calls |
| **Single Postgres connection pool** | One pool (max 10 conns) shared across HTTP + pipeline writes | Under write-heavy pipeline load, read queries (listing accounts) queue behind pipeline writes |

### 10.2 Proposed Production Architecture

```
                                   ┌─────────────────────────────┐
                                   │       LOAD BALANCER          │
                                   │  (Railway / AWS ALB / nginx) │
                                   └──────────┬──────────────────┘
                                              │
                          ┌───────────────────┼───────────────────┐
                          ▼                                       ▼
               ┌─────────────────────┐                ┌─────────────────────┐
               │   API SERVER (×N)    │                │   API SERVER (×N)    │
               │   FastAPI + Uvicorn  │                │   FastAPI + Uvicorn  │
               │                     │                │                     │
               │   • HTTP only       │                │   • HTTP only       │
               │   • Enqueue jobs    │                │   • Enqueue jobs    │
               │   • Read job status │                │   • Read job status │
               │   • SSE streaming   │                │   • SSE streaming   │
               └────────┬────────────┘                └────────┬────────────┘
                        │                                       │
                        │ enqueue                  read/write   │
                        ▼                                       ▼
           ┌────────────────────────┐             ┌─────────────────────────┐
           │      REDIS              │             │    POSTGRESQL            │
           │  • Job queue (Bull/RQ)  │             │  • Jobs table            │
           │  • Result cache (TTL)   │             │  • Accounts table        │
           │  • Pub/Sub (SSE push)   │             │  • Read replicas (opt.)  │
           │  • Rate limit counters  │             └─────────────────────────┘
           └──────────┬─────────────┘                          ▲
                      │ dequeue                                │
        ┌─────────────┼─────────────────┐                      │
        ▼             ▼                 ▼                      │
 ┌────────────┐┌────────────┐   ┌────────────┐                │
 │  WORKER 1  ││  WORKER 2  │   │  WORKER N  │                │
 │            ││            │   │            │                │
 │ LangGraph  ││ LangGraph  │   │ LangGraph  │                │
 │ pipeline   ││ pipeline   │   │ pipeline   │────────────────┘
 │            ││            │   │            │   write results
 │ Semaphore: ││ Semaphore: │   │ Semaphore: │
 │ 5 LLM max  ││ 5 LLM max  │   │ 5 LLM max  │
 └────────────┘└────────────┘   └────────────┘
        │             │                 │
        └─────────────┼─────────────────┘
                      ▼
           ┌─────────────────────┐
           │  EXTERNAL SERVICES   │
           │  • Gemini API        │
           │  • OpenAI API        │
           │  • Tavily API        │
           │  • ipapi.co          │
           └─────────────────────┘
```

### 10.3 Key Changes from Current System

#### 10.3.1 Job Queue (Redis + Worker Separation)

**Current:** `asyncio.create_task()` inside the API server process.
**Proposed:** API servers enqueue job payloads into a Redis-backed queue (e.g., `arq`, `celery`, or `bullmq` via a thin bridge). Dedicated worker processes dequeue and run the LangGraph pipeline.

```
API Server (fast, stateless):
    POST /analyze/company → serialize CompanyInput → LPUSH redis:job_queue → return 202

Worker (long-running, stateful):
    BRPOP redis:job_queue → deserialize → run compiled_workflow.ainvoke() → write result to Postgres
```

**Benefits:**
- API servers stay responsive under heavy pipeline load
- Workers can be scaled independently (Railway lets you add worker services)
- Crash-resilient: if a worker dies, the job remains in the queue and is picked up by another worker
- Backpressure is natural: queue depth is observable and alertable

**Migration path:** Replace `asyncio.create_task(self._run_pipeline(...))` with `await queue.enqueue(job_id, payload)`. The `_run_pipeline` method moves verbatim into the worker. Zero agent logic changes.

#### 10.3.2 LLM Concurrency Control

**Current:** No limit on parallel LLM calls.
**Proposed:** Each worker holds an `asyncio.Semaphore(5)` that gates all `generate_json()` calls. This caps outgoing LLM API requests per worker.

```python
_llm_semaphore = asyncio.Semaphore(5)

async def generate_json_throttled(...):
    async with _llm_semaphore:
        return await generate_json(...)
```

Combined with per-API-key rate limiting tracked in Redis (`INCR + EXPIRE`), this prevents 429s from Gemini/OpenAI and keeps costs predictable.

#### 10.3.3 Real-Time Updates via SSE (Replace Polling)

**Current:** Frontend polls `GET /jobs/{id}` every 2 seconds.
**Proposed:** Server-Sent Events (SSE) stream pushed from the API server, triggered by Redis Pub/Sub.

```
Worker writes progress → UPDATE jobs SET progress=0.5 → PUBLISH redis:job:{id} {progress: 0.5}

API Server subscribes → SUBSCRIBE redis:job:{id} → push SSE event to connected client
```

Frontend receives progress updates in ~50ms instead of up to 2 seconds, with zero wasted HTTP requests. Graceful fallback to polling if SSE connection drops.

#### 10.3.4 Redis Cache Layer

**Current:** `@cached_call(ttl=300)` is a per-process Python dict, lost on restart.
**Proposed:** Replace the in-memory cache dict with Redis `GET/SETEX`. The `@cached_call` decorator already hashes kwargs to a SHA-256 key — the storage backend changes from `dict` to `redis.get(key)` / `redis.setex(key, ttl, json)`.

**Impact:** If two workers analyze the same company within 5 minutes, the second skips all Tavily/IP-lookup/scraper calls. Cache survives deployments and is shared across all workers.

#### 10.3.5 Database Read Replicas

**Current:** Single Postgres instance handles reads and writes.
**Proposed:** Add a read replica for the `accounts` table queries (`list_accounts`, `get_account`). Pipeline writes go to the primary. API reads go to the replica.

This is only needed at >1000 stored accounts or >50 concurrent dashboard users. For the near term, connection pool tuning (`max_size=20`, separate pools for read vs. write) is sufficient.

### 10.4 Scaling Dimensions

| Dimension | Current Capacity | Scaled Capacity | How |
|-----------|-----------------|-----------------|-----|
| Concurrent analyses | ~5–10 per server | ~50 per worker × N workers | Worker separation + job queue |
| LLM throughput | Unbounded (risk of 429s) | 5 per worker, globally rate-limited | Semaphore + Redis counters |
| Dashboard load | ~20 polling clients | ~500 SSE clients per API server | SSE + Redis Pub/Sub |
| Cache hit rate | 0% after restart | Persistent across deploys | Redis-backed `@cached_call` |
| Data query speed | Single Postgres pool | Read replicas + connection pool split | Separate read/write pools |
| Deployment downtime | Full restart loses in-flight jobs | Zero-downtime rolling deploys | Jobs survive in Redis queue |

### 10.5 What Does NOT Change

The scalability upgrades are purely infrastructure. The following remain untouched:

- **Agent logic:** All 9 agents keep their `run()` / `validate_input()` contracts
- **Pipeline topology:** LangGraph DAG (route → stage1 → stage2 → playbook → summary) is unchanged
- **Tool contracts:** `BaseTool.call() → Optional[dict]` with `@cached_call` decorator
- **Domain models:** All Pydantic models remain frozen, immutable value objects
- **API contracts:** Same endpoints, same request/response schemas
- **Error handling:** Agents still never raise; tools still return `None` on failure

The `_run_pipeline` method moves from the API server process to a worker process — but its code is identical. This is the core design insight: **the pipeline is a pure function of (VisitorSignal | CompanyInput) → AccountIntelligence**, which makes it trivially parallelizable across workers without shared mutable state.

### 10.6 Recommended Implementation Order

| Phase | Effort | Impact | Dependencies |
|-------|--------|--------|--------------|
| 1. Redis job queue + workers | 2–3 days | Removes single-process bottleneck; crash recovery | Redis instance (Railway addon) |
| 2. LLM semaphore | 2 hours | Prevents rate limiting and cost spikes | None |
| 3. Redis cache for tools | 4 hours | Eliminates redundant external API calls | Phase 1 (Redis) |
| 4. SSE streaming | 1 day | Real-time UX; eliminates polling overhead | Phase 1 (Redis Pub/Sub) |
| 5. Read replicas | 1 day | Only needed at scale (>1000 accounts) | Managed Postgres with replicas |

> **Note:** Phase 2 (LLM semaphore) can be implemented immediately in the current architecture — it requires no infrastructure changes and provides immediate cost/reliability benefits.
