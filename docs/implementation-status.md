# Implementation Status — Fello AI Account Intelligence System

> **Version**: 2.0  
> **Date**: 2026-03-18  
> **Status**: Fully implemented and integration-verified  
> **Depends on**: [HLD](./hld.md), [LLD](./lld.md), [Data Pipeline](./data-pipeline.md)

This document describes what is **actually built** as of the current codebase, what deviates from the original design, and what remains to be done. Use this as the ground truth when onboarding or continuing development.

---

## 1. Overall Status

| Layer | Status | Notes |
|-------|--------|-------|
| Domain models | ✅ Complete | All 11 Pydantic models implemented, frozen, typed |
| API routes | ✅ Complete | `/analyze/visitor`, `/analyze/company`, `/jobs/{id}`, `/accounts`, `/accounts/{id}` |
| Controllers | ✅ Complete | `AnalysisController` with full job lifecycle |
| LangGraph pipeline | ✅ Complete | 5-stage graph with asyncio.gather parallelism |
| Storage | ✅ Complete | SQLite (default) with in-memory fallback; `aiosqlite` async driver |
| LLM service | ✅ Complete | Gemini primary, OpenAI fallback, structured JSON output |
| IP Lookup tool | ✅ Complete | ipapi.co primary, ip-api.com fallback, cloud-provider detection |
| Web search tool | ✅ Complete | Tavily via sync `TavilyClient` + `asyncio.to_thread` |
| Scraper tool | ✅ Present | `ScraperTool` implemented but **not called by any agent** |
| Enrichment APIs tool | ⚠️ Stub | `EnrichmentAPITool` file exists; Clearbit/Apollo not wired |
| Frontend | ✅ Complete | Next.js 14, dark theme, all components, real API calls |
| Frontend ↔ Backend | ✅ Integrated | Mocks removed; response transformation layer in `api.ts` |
| Batch analysis | ❌ Not implemented | `/analyze/batch` endpoint does not exist |
| Authentication | ❌ Not implemented | No auth; noted as future work |
| Persistent storage | ✅ Implemented | SQLite via `aiosqlite`; data survives restarts |

---

## 2. Backend — What Is Built

### 2.1 LLM Service (`backend/core/llm_service.py`)

The system uses a **centralized LLM service** (not per-agent LLM instances). All structured JSON generation goes through `generate_json()`.

**Provider chain:**
1. **Gemini** (`gemini-2.5-flash`) — primary; configured via `GEMINI_API_KEY`
2. **OpenAI** (`gpt-4o-mini`) — fallback; configured via `OPENAI_API_KEY`

**Key implementation details:**
- Gemini is called via `google.genai` SDK with `response_mime_type="application/json"`
- Gemini token budget is set to `max(requested_tokens * 3, 8192)` to accommodate thinking-model overhead
- OpenAI is called via LangChain with `response_format={"type": "json_object"}`
- Both providers retry up to 2 times before falling through to the next provider
- JSON extraction handles markdown fences, prose prefixes, and brace-depth matching

**Important deviation from LLD:** The LLD specifies per-agent LLM injection via `BaseAgent.__init__(llm=...)`. In practice, agents call `generate_json()` directly from `backend/core/llm_service` rather than using `self._llm`. The `llm` parameter is accepted by `BaseAgent` but is not the actual call path.

### 2.2 Agent Implementation Status

| Agent | LLM Used | Tools Used | Actual Behavior |
|-------|----------|-----------|-----------------|
| **IdentificationAgent** | ❌ No LLM | ✅ `IPLookupTool`, `WebSearchTool` | Real IP lookup → cloud-provider check → "Unknown" if unresolvable |
| **EnrichmentAgent** | ✅ Gemini | ✅ `WebSearchTool` | Tavily search + LLM synthesis; returns low-confidence profile for Unknown companies |
| **PersonaAgent** | ✅ Gemini | ❌ None | LLM infers role from page patterns; rule-based fallback on LLM failure |
| **IntentScorerAgent** | ❌ No LLM | ❌ None | Pure rule-based scoring (weighted page scores + visit/time bonuses) |
| **TechStackAgent** | ✅ Gemini | ❌ None | LLM infers tech stack from company profile; empty result for Unknown companies |
| **SignalsAgent** | ✅ Gemini | ✅ `WebSearchTool` | Tavily search for recent news + LLM extraction; empty for Unknown companies |
| **LeadershipAgent** | ✅ Gemini | ✅ `WebSearchTool` | Tavily search for leadership + LLM extraction; empty for Unknown companies |
| **PlaybookAgent** | ✅ Gemini | ❌ None | Full LLM synthesis; minimal "identify company first" playbook for Unknown |
| **SummaryAgent** | ✅ Gemini | ❌ None | Full LLM narrative; uncertainty-aware template for Unknown companies |

### 2.3 Unknown Company Handling

When `IdentificationAgent` cannot resolve an IP (private IP, cloud provider, or unrecognized), the pipeline **does not fabricate data**. The behavior is:

| Agent | Unknown Company Behavior |
|-------|--------------------------|
| EnrichmentAgent | Returns `CompanyProfile(confidence_score=0.1)` with null fields |
| TechStackAgent | Returns `TechStack(technologies=[], confidence_score=0.0)` |
| SignalsAgent | Returns `BusinessSignals(signals=[], confidence_score=0.0)` |
| LeadershipAgent | Returns `LeadershipProfile(leaders=[], confidence_score=0.0)` |
| PlaybookAgent | Returns single action: "Identify the visitor's company through follow-up engagement" |
| SummaryAgent | Returns template: "The visitor's company could not be identified from their IP address..." |

The threshold for "unknown" is `company_name.lower() in ("unknown", "unknown (private ip)", "none", "")` or `confidence_score < 0.3`.

### 2.4 Tool Implementation Status

**IPLookupTool** (`backend/tools/ip_lookup.py`):
- Primary: `ipapi.co/{ip}/json/` (HTTP GET, 8s timeout)
- Fallback: `ip-api.com/json/{ip}` (HTTP GET, 8s timeout)
- Cloud provider detection: checks `org` + `isp` fields against known provider names
- Returns `None` if both providers fail; `company_name=None` if cloud provider detected
- Results cached for 300s by input hash

**WebSearchTool** (`backend/tools/web_search.py`):
- Uses `tavily.TavilyClient` (sync) wrapped in `asyncio.to_thread`
- Filters out `reddit.com`, `quora.com`, `pinterest.com`
- Returns up to 5 results with title, URL, snippet, rank, domain
- Results cached for 300s by query hash

**ScraperTool** (`backend/tools/scraper.py`):
- Implemented with `httpx`, 8s timeout, extracts title/meta/text/scripts
- **Not currently called by any agent** — TechStackAgent uses LLM knowledge instead of scraping

**EnrichmentAPITool** (`backend/tools/enrichment_apis.py`):
- File exists with Clearbit → Apollo → LLM fallback structure
- **Not called** — EnrichmentAgent uses WebSearchTool + LLM directly

### 2.5 Graph Implementation

The LangGraph graph (`backend/graph/`) uses **`asyncio.gather` inside nodes** rather than LangGraph `Send()` for parallelism. This is simpler and avoids fan-in edge complications.

```
START → route_input
  ├─ (visitor_signal) → identification_node → stage1_node
  └─ (company_input)  → stage1_node
stage1_node → stage2_node → playbook_node → summary_node → END
```

- `stage1_node`: runs `enrichment`, `persona`, `intent_scorer` concurrently via `asyncio.gather`
- `stage2_node`: runs `tech_stack`, `signals`, `leadership` concurrently via `asyncio.gather`
- Progress updates written to `job_store` inside each node

**Deviation from HLD:** HLD specifies LangGraph `Send()` for fan-out. Actual implementation uses `asyncio.gather` within single nodes. Functionally equivalent; simpler to reason about.

### 2.6 Storage

The system supports two storage backends, selected by the `DATABASE_URL` config setting:

**SQLite (default)** — `backend/storage/sqlite_store.py`:
- Uses `aiosqlite` for async SQLite access
- `jobs` table stores flat job records; `accounts` table stores full `AccountIntelligence` as a JSON blob plus denormalized columns for listing/filtering
- Database file at `data/fello.db` (created automatically on startup)
- Data persists across server restarts

**In-memory (fallback)** — `backend/storage/job_store.py` + `backend/storage/account_store.py`:
- Python dicts with `asyncio.Lock` for thread safety
- Data is lost on server restart
- Activated by setting `DATABASE_URL=none` or `DATABASE_URL=`

Both implementations inherit from `AbstractJobStore` / `AbstractAccountStore` in `backend/storage/base.py`, ensuring the controller and graph code work identically with either backend.

---

## 3. Frontend — What Is Built

### 3.1 Pages

| Page | File | Status | Notes |
|------|------|--------|-------|
| Dashboard | `app/page.tsx` | ✅ Complete | Analysis form + recent accounts list |
| Account Detail | `app/account/[id]/page.tsx` | ✅ Complete | Full intelligence view |

### 3.2 Components

| Component | Status | Notes |
|-----------|--------|-------|
| `AnalysisForm` | ✅ Complete | Visitor Signal + Company Lookup tabs |
| `AccountCard` | ✅ Complete | Summary card with intent score bar |
| `IntentMeter` | ✅ Complete | Animated progress bar, color-coded by score |
| `PersonaBadge` | ✅ Complete | Role + seniority + confidence pill |
| `CompanyProfileCard` | ✅ Complete | Industry, size, HQ, description |
| `TechStackGrid` | ✅ Complete | Technology pills with category labels |
| `LeadershipList` | ✅ Complete | Leader cards with LinkedIn links |
| `SignalsFeed` | ✅ Complete | Business signals with source links |
| `SalesPlaybook` | ✅ Complete | Priority badge, actions, talking points, outreach template |
| `AISummary` | ✅ Complete | Green-bordered narrative block |
| `VisitorScenarios` | ✅ Present | Demo scenario selector component |

### 3.3 API Client (`frontend/lib/api.ts`)

All backend calls go through this file. **Mocks have been fully removed.**

The client includes three response transformers that bridge the backend's nested Pydantic schema to the frontend's flat `AccountIntelligenceResponse` interface:

| Transformer | Purpose |
|-------------|---------|
| `transformAccountResponse` | Flattens nested `company`, `intent`, `persona`, `tech_stack`, etc. into flat fields |
| `transformJobStatus` | Scales `progress` from `0.0–1.0` (backend) to `0–100` (frontend), adds `success: true` |
| `transformAccountList` | Adds `success: true` to list response and each account summary |

**Environment variables:**
```env
NEXT_PUBLIC_API_URL=http://localhost:8000/api/v1   # backend base URL
NEXT_PUBLIC_USE_MOCKS=false                         # mocks disabled
```

### 3.4 Hooks

**`useAccountAnalysis`** (`frontend/hooks/useAccountAnalysis.ts`):
- Calls `api.analyzeVisitor` or `api.analyzeCompany`
- Starts `useJobPoller` with returned `job_id`
- On completion, fetches full account via `api.getAccount(result_id)`
- Navigates to `/account/{id}` on success

**`useJobPoller`** (`frontend/hooks/useJobPoller.ts`):
- Polls `api.getJobStatus(jobId)` every 2 seconds
- Stops on `COMPLETED`, `FAILED`, or component unmount
- Exposes `{ status, progress, currentStep, resultId, error }`

### 3.5 Schema Mismatch Resolution

The backend returns `AccountIntelligence` as a nested Pydantic model. The frontend `AccountIntelligenceResponse` type expects a flat structure. This mismatch is resolved entirely in `frontend/lib/api.ts` via `transformAccountResponse` — neither the backend schema nor the frontend type was changed.

---

## 4. Integration Notes

### 4.1 Known Limitations

| Limitation | Impact | Workaround |
|-----------|--------|-----------|
| ~~In-memory storage~~ | ~~Data lost on server restart~~ | **Fixed:** SQLite persistence is now the default; data survives restarts |
| `--reload` clears jobs | Jobs disappear mid-pipeline | Run uvicorn **without** `--reload` in integration testing |
| Gemini thinking-model token overhead | JSON truncation if `max_output_tokens` is too low | Fixed: budget = `max(requested * 3, 8192)` |
| OpenAI quota exceeded | Falls through to no LLM | Ensure `GEMINI_API_KEY` is set as primary |
| ipapi.co rate limit (free tier) | Falls back to ip-api.com | Both providers in fallback chain |
| Tavily v0.3.3 has no `AsyncTavilyClient` | Was causing `ImportError` | Fixed: uses sync `TavilyClient` + `asyncio.to_thread` |
| Batch analysis not implemented | No `/analyze/batch` endpoint | Submit companies individually |

### 4.2 Confidence Score Behavior

The overall `confidence_score` on `AccountIntelligence` is computed by `SummaryAgent` as a weighted average:

| Component | Weight |
|-----------|--------|
| Company enrichment | 0.25 |
| Intent scoring | 0.20 |
| Persona inference | 0.15 |
| Tech stack | 0.10 |
| Business signals | 0.10 |
| Leadership | 0.10 |
| Playbook | 0.10 |

For **Unknown companies**, the overall confidence is typically 0.20–0.35 (driven only by intent/persona from behavioral signals).

For **known companies**, confidence is typically 0.70–0.95 depending on Tavily result quality and LLM confidence.

### 4.3 LLM Failure Fallbacks

| Agent | LLM Failure Behavior |
|-------|---------------------|
| PersonaAgent | Rule-based fallback: maps page patterns to roles deterministically |
| EnrichmentAgent | Returns minimal `CompanyProfile` with `confidence_score=0.3` |
| TechStackAgent | Returns empty `TechStack` |
| SignalsAgent | Returns empty `BusinessSignals` |
| LeadershipAgent | Returns empty `LeadershipProfile` |
| PlaybookAgent | Rule-based fallback: generates generic LOW-priority playbook |
| SummaryAgent | Template fallback: `"{company} is a {size} {industry} based in {hq}..."` |

### 4.4 Pipeline Timing (Observed)

| Scenario | Typical Wall-Clock Time |
|----------|------------------------|
| Private/unknown IP | 15–20s (LLM calls for persona, playbook, summary) |
| Cloud provider IP (8.8.8.8) | 15–20s |
| Known company (Salesforce) | 45–65s (Tavily + multiple LLM calls for all agents) |

The bottleneck is Gemini API latency (~8–15s per call). Stage 1 and Stage 2 agents run in parallel, but each stage waits for all agents to complete before proceeding.

---

## 5. Identified Gaps (Gap Analysis — 2026-03-18)

### 5.1 Missing or Incomplete

| Gap | Severity | Detail |
|-----|----------|--------|
| **Persistent storage** | High | In-memory only; data lost on restart. Primary gap. |
| **`reasoning_trace` not shown in UI** | Low | Stored in backend but no frontend component displays it. Evaluators cannot see chain-of-thought. |
| **Batch analysis untested** | Medium | Route, schema, and controller method exist but have not been end-to-end tested. |
| **Scraper tool unused** | Low | `ScraperTool` is implemented but TechStackAgent uses LLM knowledge instead. |
| **Clearbit/Apollo enrichment** | Low | `EnrichmentAPITool` is a stub; Tavily + LLM is the actual enrichment path. |

### 5.2 API Contract Deviations

| Contract Field | Documented (database-schema.md) | Actual Implementation |
|----------------|--------------------------------|----------------------|
| `JobRecord.analysis_type` | Defined | **Not present** in actual `JobRecord` Pydantic model |
| `JobRecord.batch_id` | Defined | **Not present** in actual `JobRecord` Pydantic model |
| `AbstractJobStore.create` signature | `(job_id, analysis_type, batch_id)` | Actual: `(job_id: str)` only |
| `AbstractJobStore.get_batch_jobs` | Defined | **Not implemented** |
| `PersonaInferenceResponse.reasoning` | Defined in responses.py | **Not populated** by PersonaAgent |
| `InMemoryJobStore`/`InMemoryAccountStore` | Should inherit abstract bases | **Do not inherit** from `storage/base.py` ABCs |

### 5.3 Frontend Display Gaps

| Gap | Detail |
|-----|--------|
| `reasoning_trace` not rendered | Available from API but no component displays it |
| `PersonaInference.department` not shown | Backend produces it; frontend `PersonaBadge` ignores it |
| `IntentScore.signals_detected` not shown | Backend produces per-signal labels; frontend only shows score bar |
| `Leader.source_url` not mapped | Backend returns it; frontend `LeaderSchema` omits it |
| `TechStack.detection_method` not shown | Backend returns it; not mapped to frontend |

---

## 6. What Remains

### 6.1 Not Implemented (Hackathon Scope)

- **Batch analysis** (`POST /analyze/batch`) — endpoint not created
- ~~**Persistent storage**~~ — **Implemented** (SQLite via `aiosqlite`)
- **Authentication** — API key or JWT
- **Rate limiting** — per-IP or per-key request throttling
- **Clearbit/Apollo enrichment** — `EnrichmentAPITool` is a stub
- **Website scraper in pipeline** — `ScraperTool` exists but is not called by any agent
- **CSV upload** — batch input via file upload

### 6.2 Partially Implemented

- **`EnrichmentAPITool`** — file exists with correct interface; Clearbit/Apollo API calls not wired
- **`ScraperTool`** — fully implemented; not integrated into any agent's call chain
- **Tavily in IdentificationAgent** — search is called but results are not used to infer company (returns `None` conservatively to avoid fabrication)

### 6.3 Deviations from Architecture Docs

| Doc | Designed | Actual |
|-----|---------|--------|
| HLD | LangGraph `Send()` for parallelism | `asyncio.gather` inside nodes |
| HLD | Clearbit/Apollo enrichment | Tavily + LLM only |
| LLD | `BaseAgent.__init__(llm=...)` as call path | `generate_json()` called directly |
| data-pipeline.md | `scraper` used by TechStackAgent | LLM knowledge used instead |
| data-pipeline.md | `enrichment_apis` used by EnrichmentAgent | WebSearchTool + LLM used instead |
| integration.md | `NEXT_PUBLIC_USE_MOCKS` toggle | Mocks fully removed; flag is vestigial |
