# Runbook — Fello AI Account Intelligence System

> **Version**: 1.0  
> **Date**: 2026-03-18  
> **Audience**: Developers running, testing, and debugging the system  
> **Depends on**: [Implementation Status](./implementation-status.md)

---

## 1. Prerequisites

| Requirement | Version | Notes |
|-------------|---------|-------|
| Python | 3.11+ | Used for backend |
| Node.js | 18+ | Used for frontend |
| npm | 9+ | Frontend package manager |
| `GEMINI_API_KEY` | — | Primary LLM (Google AI Studio) |
| `TAVILY_API_KEY` | — | Web search (tavily.com) |
| `OPENAI_API_KEY` | — | Optional LLM fallback |

---

## 2. First-Time Setup

### 2.1 Backend

```powershell
# From project root
cd "Fello Hackathon"

# Install Python dependencies
pip install -r requirements.txt

# Configure environment
# Edit backend/.env with your API keys (copy from .env.example if needed)
```

**`backend/.env` required fields:**

```env
GEMINI_API_KEY=AIzaSy...        # Required — primary LLM
TAVILY_API_KEY=tvly-dev-...     # Required — web search
OPENAI_API_KEY=sk-proj-...      # Optional — LLM fallback

GEMINI_MODEL_NAME=gemini-2.5-flash
MODEL_NAME=gpt-4o-mini

HOST=0.0.0.0
PORT=8000
CORS_ORIGINS=["http://localhost:3000"]

TOOL_TIMEOUT_SECONDS=8
TOOL_MAX_RETRIES=3
CACHE_TTL_SECONDS=300

# Storage — SQLite is the default; set to 'none' for in-memory
DATABASE_URL=sqlite:///data/fello.db
```

### 2.2 Frontend

```powershell
cd frontend
npm install
```

**`frontend/.env.local` required fields:**

```env
NEXT_PUBLIC_API_URL=http://localhost:8000/api/v1
NEXT_PUBLIC_USE_MOCKS=false
```

---

## 3. Starting the System

### 3.1 One-Command Start (Recommended)

**Windows (PowerShell):**
```powershell
.\start.ps1              # Start both backend and frontend
.\start.ps1 -BackendOnly  # Backend only
.\start.ps1 -FrontendOnly # Frontend only
```

**Linux/macOS:**
```bash
chmod +x start.sh
./start.sh              # Start both
./start.sh --backend    # Backend only
./start.sh --frontend   # Frontend only
```

The start script will:
- Check for Python/Node
- Verify `backend/.env` exists (copy from `.env.example` if missing)
- Install dependencies
- Create `data/` directory for SQLite
- Launch backend (port 8000) and/or frontend (port 3000) in separate terminals

**Allow 10–15 seconds** for both services to fully start.

### 3.2 Manual Start — Backend

```powershell
# From project root — DO NOT use --reload (clears in-memory job store)
python -m uvicorn backend.main:app --port 8000
```

Successful startup output:
```
INFO  backend.main    Fello AI Account Intelligence API  v1.0.0
INFO  backend.main    GEMINI key   : AIzaSyCD...
INFO  backend.main    OPENAI key   : sk-proj-...
INFO  backend.main    TAVILY key   : tvly-dev...
INFO  backend.main    LLM primary  : gemini-2.5-flash
INFO  backend.main    LLM fallback : gpt-4o-mini
INFO  backend.main    CORS origins : ['http://localhost:3000']
INFO  backend.storage.sqlite_store  SQLite database initialized at data/fello.db
INFO  backend.main    Storage      : SQLite (sqlite:///data/fello.db)
INFO:     Application startup complete.
INFO:     Uvicorn running on http://127.0.0.1:8000
```

**Do not use `--reload`** — it watches the filesystem and restarts the process, which kills active pipeline runs. With SQLite storage, data persists across restarts, but in-flight jobs will be lost.

### 3.3 Frontend

```powershell
# From frontend/ directory
npm run dev
```

Frontend available at `http://localhost:3000`.

### 3.4 Kill Existing Processes (Windows)

If ports are already in use:

```powershell
# Kill process on port 8000 (backend)
$proc = Get-NetTCPConnection -LocalPort 8000 -ErrorAction SilentlyContinue | Select-Object -First 1 -ExpandProperty OwningProcess
if ($proc) { taskkill /PID $proc /F /T }

# Kill process on port 3000 (frontend)
$proc = Get-NetTCPConnection -LocalPort 3000 -ErrorAction SilentlyContinue | Select-Object -First 1 -ExpandProperty OwningProcess
if ($proc) { taskkill /PID $proc /F /T }
```

---

## 4. Manual Testing

### 4.1 Test via Frontend UI

1. Open `http://localhost:3000`
2. **Company Lookup tab**: type "Salesforce", domain "salesforce.com", click Analyze
3. **Visitor Signal tab**: enter an IP, pages, click Analyze
4. Watch the progress bar update as the pipeline runs
5. Verify the account detail page shows real AI-generated content

### 4.2 Test via curl

**Submit a visitor analysis:**
```bash
curl -X POST http://localhost:8000/api/v1/analyze/visitor \
  -H "Content-Type: application/json" \
  -d '{
    "visitor_id": "test-001",
    "ip_address": "34.201.114.42",
    "pages_visited": ["/pricing", "/case-studies"],
    "time_on_site_seconds": 180,
    "visit_count": 2
  }'
```

Expected response:
```json
{"job_id": "uuid-here", "status": "PENDING", "poll_url": "/jobs/uuid-here", ...}
```

**Poll job status:**
```bash
curl http://localhost:8000/api/v1/jobs/{job_id}
```

Poll until `"status": "COMPLETED"` and `"result_id"` is populated (typically 15–60s).

**Fetch account result:**
```bash
curl http://localhost:8000/api/v1/accounts/{result_id}
```

**Submit a company analysis:**
```bash
curl -X POST http://localhost:8000/api/v1/analyze/company \
  -H "Content-Type: application/json" \
  -d '{"company_name": "HubSpot", "domain": "hubspot.com"}'
```

**List all accounts:**
```bash
curl http://localhost:8000/api/v1/accounts
```

### 4.3 Test Scenarios

| Scenario | Input | Expected Output |
|----------|-------|----------------|
| Private IP | `ip_address: "192.168.1.1"` | Company: "Unknown (Private IP)", confidence < 0.35, empty tech/signals/leaders |
| Cloud provider IP | `ip_address: "8.8.8.8"` | Company: "Unknown", confidence < 0.35, empty tech/signals/leaders |
| Known company | `company_name: "Salesforce"` | Real enrichment, real leaders (Marc Benioff), real signals, confidence > 0.7 |
| High-intent visitor | pages: `["/pricing", "/enterprise", "/demo"]`, visits: 3+ | Intent score > 8.0, stage: PURCHASE |
| Low-intent visitor | pages: `["/blog"]`, visits: 1 | Intent score < 3.0, stage: AWARENESS |

### 4.4 Run Test Scripts

**Windows (PowerShell):**
```powershell
.\run_tests.ps1         # Unit + API tests (fast, ~5s)
.\run_tests.ps1 -Fast   # Domain + storage only (~1s)
.\run_tests.ps1 -E2E    # Full E2E validation (requires running backend, ~3–5 min)
.\run_tests.ps1 -All    # All tests including pipeline (requires API keys, ~5–15 min)
```

**Linux/macOS:**
```bash
./run_tests.sh          # Unit + API tests
./run_tests.sh --fast   # Domain + storage only
./run_tests.sh --e2e    # E2E validation (backend must be running)
./run_tests.sh --all    # Full suite including pipeline
```

**E2E validation** (requires backend on port 8000):
```powershell
# Start backend first, then:
.\run_tests.ps1 -E2E
# Or directly:
python e2e-tests/validate_api.py --base-url http://localhost:8000/api/v1
```

**Persistence verification:**
- `test_sqlite_store.py::TestSQLiteJobStore::test_persistence_across_instances` — data written by one store instance is readable by another (simulates restart)
- `test_sqlite_store.py::TestSQLiteAccountStore::test_persistence_across_instances` — same for accounts
- E2E validation runs multiple analyses; completed results are retrievable via GET /accounts/{id}

**Expected behaviour:**
- **Fast tests**: 91 passed, ~1s — domain models, in-memory storage, SQLite storage, unknown-IP edge cases
- **Default tests**: ~128 passed, ~5s — adds API endpoint tests (health, analyze, jobs, accounts, validation)
- **E2E**: Validates full flows against live backend — company analysis, visitor analysis, unknown IP handling
- **All tests**: Includes pipeline tests that call real LLM; may skip if pipeline does not complete in time

### 4.6 Test via Python Script (Ad-hoc)

```python
import httpx, time, json

BASE = "http://localhost:8000/api/v1"

# Submit
r = httpx.post(f"{BASE}/analyze/company", json={"company_name": "Stripe", "domain": "stripe.com"}, timeout=10)
job_id = r.json()["job_id"]
print(f"Job: {job_id}")

# Poll
while True:
    r = httpx.get(f"{BASE}/jobs/{job_id}", timeout=10)
    job = r.json()
    print(f"  {job['status']} — {round(job['progress']*100)}% — {job.get('current_step')}")
    if job["status"] in ("COMPLETED", "FAILED"):
        break
    time.sleep(3)

# Fetch result
if job.get("result_id"):
    r = httpx.get(f"{BASE}/accounts/{job['result_id']}", timeout=10)
    acct = r.json()
    print(json.dumps({
        "company": acct["company"]["company_name"],
        "confidence": acct["confidence_score"],
        "summary": acct["ai_summary"][:200],
    }, indent=2))
```

---

## 5. Viewing Logs

### 5.1 Backend Logs

The backend logs to stdout. Key log patterns to watch:

```
# LLM calls
INFO  backend.core.llm_service  LLM call [gemini] attempt 1/2 ...
INFO  backend.core.llm_service  [gemini] successfully parsed ...
WARNING  backend.core.llm_service  [gemini] parse failed on attempt 1 ...

# Tool calls
INFO  backend.tools.ip_lookup  ...
WARNING  backend.tools.ip_lookup  ip_lookup ipapi.co failed ...
INFO  backend.tools.web_search  Tavily search returned N results ...

# Agent decisions
INFO  backend.agents.identification  [identification_agent] private/reserved IP ...
INFO  backend.agents.identification  [identification_agent] IP X belongs to cloud/ISP provider ...
INFO  backend.agents.enrichment  [enrichment_agent] enriching {company} via Tavily + LLM
INFO  backend.agents.enrichment  [enrichment_agent] company is Unknown — returning low-confidence profile

# Pipeline progress
INFO  backend.controllers.analysis  Job {id} completed → account {id}
```

### 5.2 Increasing Log Verbosity

To see DEBUG-level logs, set the log level in `backend/main.py` or via environment:

```python
import logging
logging.basicConfig(level=logging.DEBUG)
```

### 5.3 Frontend Logs

Open browser DevTools → Network tab to see:
- `POST /api/v1/analyze/visitor` or `/analyze/company`
- `GET /api/v1/jobs/{id}` (repeated every 2s)
- `GET /api/v1/accounts/{id}` (once on completion)

---

## 6. Common Issues and Fixes

### Port already in use

```
ERROR: [Errno 10048] error while attempting to bind on address ('0.0.0.0', 8000)
```

**Fix:** Kill the existing process (see Section 3.3).

### Job disappears mid-pipeline (404 on poll)

**Cause:** Backend was restarted while a job was running. With SQLite, completed jobs survive restarts, but in-flight jobs (PROCESSING status) may be left in an incomplete state.

**Fix:** Restart backend **without** `--reload`. Do not save Python files while a job is running.

### Gemini JSON truncation

```
WARNING  backend.core.llm_service  [gemini] parse failed: No valid JSON found
raw: {
  "field": "value",
  "another_fi
```

**Cause:** `max_output_tokens` was too low for the thinking model's overhead.

**Fix:** Already applied — token budget is `max(requested * 3, 8192)`. If still occurring, increase the multiplier in `_call_gemini` in `backend/core/llm_service.py`.

### Tavily ImportError

```
WARNING  backend.tools.web_search  web_search failed: ImportError
```

**Cause:** Old code used `AsyncTavilyClient` which doesn't exist in tavily-python v0.3.3.

**Fix:** Already applied — uses `TavilyClient` with `asyncio.to_thread`. If you see this, ensure you have the latest `backend/tools/web_search.py`.

### OpenAI 429 (quota exceeded)

```
WARNING  backend.core.llm_service  OpenAI call failed: Error code: 429 - insufficient_quota
```

**Cause:** OpenAI account has no credits.

**Fix:** Ensure `GEMINI_API_KEY` is set — Gemini is the primary provider and OpenAI is only a fallback. If Gemini also fails, check your Google AI Studio quota.

### Frontend shows "0 analyzed" after backend restart

**Cause (in-memory mode):** In-memory `AccountStore` was cleared on restart.

**Fix:** With SQLite (default), data survives restarts — this issue should not occur. If using in-memory mode (`DATABASE_URL=none`), re-run analyses.

### SQLite database locked

**Cause:** Multiple processes trying to write to `data/fello.db` simultaneously (e.g., two uvicorn instances).

**Fix:** Ensure only one backend process is running. Kill duplicates with the commands in Section 3.3.

### CORS errors in browser

```
Access to fetch at 'http://localhost:8000/...' from origin 'http://localhost:3000' has been blocked by CORS policy
```

**Fix:** Ensure `CORS_ORIGINS=["http://localhost:3000"]` is set in `backend/.env` and the backend was restarted after the change.

---

## 7. API Reference Quick-Links

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/api/v1/analyze/visitor` | POST | Submit visitor signal analysis |
| `/api/v1/analyze/company` | POST | Submit company name analysis |
| `/api/v1/jobs/{id}` | GET | Poll job status and progress |
| `/api/v1/accounts` | GET | List all analyzed accounts |
| `/api/v1/accounts/{id}` | GET | Fetch full account intelligence |
| `/docs` | GET | OpenAPI interactive documentation |
| `/redoc` | GET | ReDoc API documentation |

Full request/response schemas: [api-contracts.md](./api-contracts.md)

---

## 8. OpenAPI Docs

The FastAPI backend auto-generates interactive API docs:

- **Swagger UI**: `http://localhost:8000/docs`
- **ReDoc**: `http://localhost:8000/redoc`

These are useful for manually testing endpoints and inspecting response schemas.

---

## 9. Test Structure and Adding New Tests

### 9.1 Test Directory Layout

```
tests/
  conftest.py           # Shared fixtures: mock_llm_factory, fresh_stores, async_client
  test_domain.py        # Pydantic domain model validation
  test_storage.py       # InMemoryJobStore, InMemoryAccountStore
  test_sqlite_store.py  # SQLite persistence, unknown-IP edge cases
  test_api.py           # HTTP endpoint integration tests
  test_agents.py        # Agent output types, confidence, degraded paths
  test_pipeline.py      # LangGraph workflow end-to-end
e2e-tests/
  validate_api.py       # Programmatic E2E against live backend
```

### 9.2 How Tests Are Structured

| File | Fixtures | What it tests |
|------|----------|---------------|
| `conftest.py` | `mock_llm_factory`, `fresh_stores`, `async_client` | `mock_llm_factory` patches `get_llm` so tests don't call real LLM. `fresh_stores` isolates job/account stores per test. `async_client` mounts FastAPI app directly (no network). |
| `test_domain.py` | `full_intelligence` | Model validation, frozen immutability, score bounds, enum values. |
| `test_storage.py` | per-class `store` fixture | CRUD, pagination, concurrent access. |
| `test_sqlite_store.py` | `db_url`, `job_store`, `account_store` | SQLite equivalents + `TestUnknownIPEdgeCases` for unknown/private IP behaviour. |
| `test_api.py` | `async_client`, `fresh_stores` | All HTTP endpoints: 202/200/404/422, response shape. Pipeline-dependent tests poll with `_wait_for_job()` and skip if timeout. |
| `test_agents.py` | per-agent fixture | Output type, confidence range, invalid-input fallback. Uses real LLM (Gemini) unless mocked. |
| `test_pipeline.py` | none | Calls `compiled_workflow.ainvoke()` directly. Uses real LLM. |

### 9.3 Adding a New Test

1. **Domain model test**: Add to `test_domain.py` under the appropriate `Test*` class. Exercise valid construction, validation errors, and edge cases.

2. **API test**: Add to `test_api.py`. Use `async_client` for HTTP calls. For sync endpoints, assert status and shape. For async (analyze), use `_wait_for_job(client, job_id)` and handle timeout with `pytest.skip()`.

3. **Agent test**: Add to `test_agents.py`. Verify output type, non-empty required fields, confidence in [0,1], and degraded output on invalid input.

4. **E2E check**: Add to `e2e-tests/validate_api.py` in the appropriate `test_*` async function. Use `check(cond, msg)` for assertions; failures append to `failures` list.
