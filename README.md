# Fello AI — Account Intelligence System

> Convert visitor signals and company names into structured B2B sales intelligence using a multi-agent AI pipeline.

Built for a 48-hour hackathon. Fully operational end-to-end system with real LLM integration, SQLite persistence, and a polished dark-theme UI.

---

## Table of Contents

1. [Project Overview](#project-overview)
2. [System Architecture](#system-architecture)
3. [Prerequisites](#prerequisites)
4. [Setup](#setup)
5. [Running the System](#running-the-system)
6. [Testing](#testing)
7. [Example Usage](#example-usage)
8. [API Reference](#api-reference)
9. [Project Structure](#project-structure)
10. [Troubleshooting](#troubleshooting)

---

## Project Overview

Fello AI takes two types of inputs and produces structured sales intelligence:

| Input | Description |
|---|---|
| **Visitor Signal** | IP address + page visit behavior from a website visitor |
| **Company Name** | Direct company name/domain for enrichment |

**Output** — `AccountIntelligence` containing:
- Company profile (industry, size, HQ, revenue range)
- Buyer persona inference (role, seniority, behavioral signals)
- Intent score (0–10) and stage (Awareness → Purchase)
- Technology stack detection
- Business signals (hiring, funding, expansion, etc.)
- Leadership profiles
- AI-generated sales playbook with outreach template
- Executive summary with reasoning trace

---

## System Architecture

```
┌─────────────────────────────────────────────────────────┐
│                    Frontend (Next.js)                    │
│  Dashboard · Visitor Scenarios · Account Detail Pages   │
└────────────────────────┬────────────────────────────────┘
                         │ REST API
┌────────────────────────▼────────────────────────────────┐
│                  FastAPI Backend                         │
│  POST /analyze/visitor  POST /analyze/company           │
│  GET  /jobs/{id}        GET  /accounts/{id}             │
└────────────────────────┬────────────────────────────────┘
                         │
┌────────────────────────▼────────────────────────────────┐
│              LangGraph Multi-Agent Pipeline              │
│                                                         │
│  IdentificationAgent → EnrichmentAgent                  │
│       ↓                    ↓                            │
│  PersonaAgent         TechStackAgent                    │
│  IntentScorerAgent    SignalsAgent                      │
│  PlaybookAgent        LeadershipAgent                   │
│       ↓                    ↓                            │
│              SummaryAgent (final assembly)              │
└────────────────────────┬────────────────────────────────┘
                         │
┌────────────────────────▼────────────────────────────────┐
│              Tools (External I/O)                       │
│  IPLookupTool (ipapi.co)  WebSearchTool (Tavily)        │
└────────────────────────┬────────────────────────────────┘
                         │
┌────────────────────────▼────────────────────────────────┐
│              Storage (SQLite / In-Memory)               │
│  jobs table · accounts table                            │
└─────────────────────────────────────────────────────────┘
```

**LLM Providers:** Google Gemini (primary) → OpenAI GPT-4o-mini (fallback)

---

## Prerequisites

| Requirement | Version | Notes |
|---|---|---|
| Python | 3.11+ | Backend runtime |
| Node.js | 18+ | Frontend runtime |
| npm | 9+ | Frontend package manager |
| Google Gemini API key | — | Primary LLM (free tier available) |
| OpenAI API key | — | Fallback LLM (optional but recommended) |
| Tavily API key | — | Web search for enrichment (free tier available) |

**Get API keys:**
- Gemini: https://aistudio.google.com/app/apikey
- OpenAI: https://platform.openai.com/api-keys
- Tavily: https://tavily.com (free tier: 1000 searches/month)

---

## Setup

### 1. Clone and enter the project

```bash
git clone <repo-url>
cd "Fello Hackathon"
```

### 2. Configure environment variables

```bash
# Copy the example env file
cp .env.example backend/.env

# Edit backend/.env and fill in your API keys
# Required: GEMINI_API_KEY or OPENAI_API_KEY
# Required: TAVILY_API_KEY
```

`backend/.env` should look like:

```env
GEMINI_API_KEY=AIza...
OPENAI_API_KEY=sk-...         # optional but recommended as fallback
TAVILY_API_KEY=tvly-...

HOST=0.0.0.0
PORT=8000
CORS_ORIGINS=["http://localhost:3000"]
MODEL_NAME=gpt-4o-mini
GEMINI_MODEL_NAME=gemini-2.0-flash
DATABASE_URL=sqlite:///data/fello.db
```

### 3. Install Python dependencies

```bash
pip install -r requirements.txt -r requirements-dev.txt
```

### 4. Install Node dependencies

```bash
cd frontend
npm install
cd ..
```

---

## Running the System

### Option A — One-command start (Windows)

```powershell
.\start.ps1
```

This opens two terminal windows: one for the backend, one for the frontend.

### Option B — One-command start (Linux/macOS)

```bash
chmod +x start.sh
./start.sh
```

### Option C — Manual start

**Terminal 1 — Backend:**
```bash
python -m uvicorn backend.main:app --host 0.0.0.0 --port 8000 --reload
```

**Terminal 2 — Frontend:**
```bash
cd frontend
npm run dev
```

### Verify it's running

| Service | URL |
|---|---|
| Frontend UI | http://localhost:3000 |
| Backend API | http://localhost:8000 |
| API Docs (Swagger) | http://localhost:8000/docs |
| Health check | http://localhost:8000/api/v1/health |

Expected backend startup log:
```
INFO  Fello AI Account Intelligence API
INFO  Version      : 1.0.0
INFO  LLM          : Gemini (gemini-2.0-flash)
INFO  Storage      : SQLite (sqlite:///data/fello.db)
INFO  Uvicorn running on http://0.0.0.0:8000
```

---

## Testing

### Fast tests (no LLM/network required)

Runs domain model, storage, and SQLite persistence tests. Completes in ~1 second.

```bash
# Windows
.\run_tests.ps1 -Fast

# Linux/macOS
./run_tests.sh --fast

# Direct pytest
python -m pytest tests/test_domain.py tests/test_storage.py tests/test_sqlite_store.py -v
```

### Default tests (unit + API, no pipeline wait)

Runs all unit tests plus API endpoint tests. Completes in ~5 seconds.

```bash
# Windows
.\run_tests.ps1

# Linux/macOS
./run_tests.sh

# Direct pytest
python -m pytest tests/test_domain.py tests/test_storage.py tests/test_sqlite_store.py tests/test_api.py -v
```

### All tests including pipeline (requires API keys)

Runs the full suite including LangGraph pipeline tests. Takes 5–15 minutes.

```bash
# Windows
.\run_tests.ps1 -All

# Linux/macOS
./run_tests.sh --all

# Direct pytest
python -m pytest tests/ -v
```

### End-to-end API validation (requires running backend)

Validates all API endpoints against a live backend. Takes 3–5 minutes.

```bash
# Start backend first, then:

# Windows
.\run_tests.ps1 -E2E

# Linux/macOS
./run_tests.sh --e2e

# Direct Python
python e2e-tests/validate_api.py --base-url http://localhost:8000/api/v1
```

### Test coverage by file

| File | What it tests |
|---|---|
| `tests/test_domain.py` | Pydantic models, validation, immutability |
| `tests/test_storage.py` | InMemory job/account stores |
| `tests/test_sqlite_store.py` | SQLite persistence, restart survival, unknown IP edge cases |
| `tests/test_api.py` | All HTTP endpoints (202/200/404/422 responses) |
| `tests/test_agents.py` | Each agent's output type, confidence, graceful degradation |
| `tests/test_pipeline.py` | Full LangGraph workflow end-to-end |
| `e2e-tests/validate_api.py` | Live API validation with real pipeline |

---

## Example Usage

### Via the UI

1. Open http://localhost:3000
2. **Dashboard tab** — Enter a company name (e.g. "Stripe") and click Analyze
3. Watch the pipeline progress bar as each agent completes
4. View the full intelligence report on the account detail page
5. **Visitor Scenarios tab** — Test pre-built visitor signal scenarios

### Via the API

**Analyze a company:**
```bash
curl -X POST http://localhost:8000/api/v1/analyze/company \
  -H "Content-Type: application/json" \
  -d '{"company_name": "Stripe", "domain": "stripe.com"}'
```

Response:
```json
{
  "job_id": "abc123...",
  "status": "PENDING",
  "analysis_type": "company",
  "poll_url": "/api/v1/jobs/abc123..."
}
```

**Poll for completion:**
```bash
curl http://localhost:8000/api/v1/jobs/abc123...
```

**Get the result:**
```bash
curl http://localhost:8000/api/v1/accounts/{result_id}
```

**Analyze a visitor signal:**
```bash
curl -X POST http://localhost:8000/api/v1/analyze/visitor \
  -H "Content-Type: application/json" \
  -d '{
    "visitor_id": "v-001",
    "ip_address": "34.201.114.42",
    "pages_visited": ["/pricing", "/case-studies", "/demo"],
    "time_on_site_seconds": 300,
    "visit_count": 3
  }'
```

### Unknown/Private IP behavior

Private IPs (192.168.x.x, 10.x.x.x) and cloud provider IPs return:
```json
{
  "company": {
    "company_name": "Unknown (Private IP)",
    "confidence_score": 0.1
  },
  "ai_summary": "The visitor's company could not be identified from their IP address...",
  "confidence_score": 0.05
}
```

No data is fabricated for unresolved IPs.

---

## API Reference

| Method | Endpoint | Description |
|---|---|---|
| `GET` | `/api/v1/health` | Health check |
| `POST` | `/api/v1/analyze/visitor` | Submit visitor signal for analysis |
| `POST` | `/api/v1/analyze/company` | Submit company name for enrichment |
| `POST` | `/api/v1/analyze/batch` | Submit up to 20 companies at once |
| `GET` | `/api/v1/jobs/{job_id}` | Poll job status and progress |
| `GET` | `/api/v1/accounts` | List all analyzed accounts (paginated) |
| `GET` | `/api/v1/accounts/{account_id}` | Get full intelligence for one account |

Full interactive docs: http://localhost:8000/docs

---

## Project Structure

```
Fello Hackathon/
├── backend/
│   ├── agents/          # LLM-powered agents (persona, enrichment, playbook, etc.)
│   ├── api/             # FastAPI routes and response schemas
│   ├── controllers/     # Business logic bridging routes and pipeline
│   ├── core/            # LLM service (Gemini + OpenAI)
│   ├── domain/          # Pydantic domain models (immutable value objects)
│   ├── graph/           # LangGraph workflow definition and nodes
│   ├── storage/         # SQLite and in-memory stores
│   ├── tools/           # External API wrappers (IP lookup, Tavily)
│   ├── config.py        # Settings (reads from backend/.env)
│   └── main.py          # FastAPI app entry point
├── frontend/
│   ├── app/             # Next.js app router pages
│   ├── components/      # React UI components
│   ├── hooks/           # useAccountAnalysis, useJobPoller
│   ├── lib/             # api.ts (all backend calls)
│   └── types/           # TypeScript type definitions
├── tests/               # Backend test suite (pytest)
├── e2e-tests/           # End-to-end API validation script
├── docs/                # Architecture and design documentation
├── data/                # SQLite database (auto-created, gitignored)
├── .env.example         # Environment variable template
├── requirements.txt     # Python dependencies
├── requirements-dev.txt # Python dev/test dependencies
├── start.ps1            # Windows start script
├── start.sh             # Linux/macOS start script
├── run_tests.ps1        # Windows test runner
└── run_tests.sh         # Linux/macOS test runner
```

---

## Troubleshooting

### Backend won't start

**"No module named backend"** — Run from the project root, not from inside `backend/`:
```bash
cd "Fello Hackathon"
python -m uvicorn backend.main:app ...
```

**"GEMINI_API_KEY not set"** — Ensure `backend/.env` exists and has valid keys.

**"SQLite database locked"** — Only one backend instance can run at a time with `--reload`. Stop the existing process first.

### Frontend won't connect to backend

Check that:
1. Backend is running on port 8000
2. `NEXT_PUBLIC_API_URL` in `frontend/.env.local` is not overriding the default
3. CORS is configured: `CORS_ORIGINS=["http://localhost:3000"]` in `backend/.env`

### Pipeline returns Unknown company

This is correct behavior for:
- Private/RFC1918 IPs (192.168.x.x, 10.x.x.x, 172.16.x.x)
- Cloud provider IPs (AWS, GCP, Azure, Cloudflare)
- IPs with no reverse DNS or company mapping

The system intentionally returns `confidence_score < 0.3` rather than fabricating data.

### Tests failing with "LLM/network timeout"

Pipeline tests that call real LLM APIs are skipped (not failed) when the pipeline doesn't complete in time. This is expected in environments without API keys. Run `--fast` for tests that don't require API keys.

### Logs and debugging

Backend logs are printed to stdout. Set `log_cli_level = DEBUG` in `pytest.ini` for verbose test output.

To see backend logs in real time:
```bash
python -m uvicorn backend.main:app --port 8000 --log-level debug
```
