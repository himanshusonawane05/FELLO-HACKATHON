# Deployment Guide — Fello AI Account Intelligence

> **Version**: 1.0  
> **Date**: 2026-03-18  
> **Audience**: Developers, hackathon judges, demo operators

---

## 1. Architecture Overview

```
┌──────────────────────────────────────────────────────────┐
│              Browser / Demo Operator                     │
└──────────────────────────┬───────────────────────────────┘
                           │ HTTP (port 3000)
                           ▼
┌──────────────────────────────────────────────────────────┐
│           Frontend  (Next.js 14)                         │
│           Served by: next dev (dev) / next start (prod)  │
│           Env: NEXT_PUBLIC_API_URL                       │
└──────────────────────────┬───────────────────────────────┘
                           │ HTTP/JSON (port 8000)
                           ▼
┌──────────────────────────────────────────────────────────┐
│           Backend  (FastAPI + Uvicorn)                   │
│           Env: backend/.env                              │
│           CORS: CORS_ORIGINS must include frontend URL   │
└──────────────────────────┬───────────────────────────────┘
                           │ aiosqlite
                           ▼
┌──────────────────────────────────────────────────────────┐
│           SQLite  (data/fello.db)                        │
│           File on the same host as the backend           │
│           Fallback: in-memory (DATABASE_URL=none)        │
└──────────────────────────────────────────────────────────┘
```

**Component responsibilities:**

| Component | Technology | Role |
|-----------|-----------|------|
| Frontend | Next.js 14, React 18, Tailwind CSS | UI — forms, dashboards, polling |
| Backend | FastAPI, Uvicorn, LangGraph | API, multi-agent pipeline, job management |
| Database | SQLite (aiosqlite) | Persistent job and account storage |
| LLM | Gemini (primary) + OpenAI (fallback) | Agent reasoning and enrichment |
| Search | Tavily API | Web search tool used by agents |

---

## 2. Environment Variables

All backend configuration lives in `backend/.env`. Copy `.env.example` to get started:

```bash
cp .env.example backend/.env
```

### Required variables

| Variable | Description | Example |
|----------|-------------|---------|
| `GEMINI_API_KEY` | Google Gemini API key (primary LLM) | `AIzaSy...` |
| `OPENAI_API_KEY` | OpenAI API key (fallback LLM) | `sk-proj-...` |
| `TAVILY_API_KEY` | Tavily search API key | `tvly-dev-...` |

At least one of `GEMINI_API_KEY` or `OPENAI_API_KEY` must be set. Both together enables automatic fallback.

### Optional variables

| Variable | Default | Description |
|----------|---------|-------------|
| `CLEARBIT_API_KEY` | _(empty)_ | Clearbit enrichment — LLM fallback used if missing |
| `APOLLO_API_KEY` | _(empty)_ | Apollo enrichment — LLM fallback used if missing |
| `DATABASE_URL` | `sqlite:///data/fello.db` | SQLite path. Set to `none` for in-memory only |
| `HOST` | `0.0.0.0` | Uvicorn bind host |
| `PORT` | `8000` | Uvicorn bind port |
| `CORS_ORIGINS` | `["http://localhost:3000"]` | JSON array of allowed frontend origins |
| `MODEL_NAME` | `gpt-4o-mini` | OpenAI model name |
| `GEMINI_MODEL_NAME` | `gemini-2.0-flash` | Gemini model name |
| `TOOL_TIMEOUT_SECONDS` | `8` | Hard timeout per external tool call |
| `TOOL_MAX_RETRIES` | `3` | Retry count per tool call |
| `CACHE_TTL_SECONDS` | `300` | Tool result cache TTL (seconds) |

### Frontend environment

The frontend reads one variable at build time:

| Variable | Default | Description |
|----------|---------|-------------|
| `NEXT_PUBLIC_API_URL` | `http://localhost:8000` | Backend base URL |

Set it in `frontend/.env.local` for local dev or as a build-time env var for cloud deployment.

---

## 3. Local Deployment

### Prerequisites

- Python 3.11+
- Node.js 18+
- API keys for Gemini or OpenAI, and Tavily

### One-command start (recommended)

**Windows (PowerShell):**
```powershell
.\start.ps1
```

**macOS / Linux:**
```bash
./start.sh
```

Both scripts:
1. Check for `backend/.env` and copy from `.env.example` if missing
2. Install Python dependencies from `requirements.txt`
3. Create the `data/` directory for SQLite
4. Start the FastAPI server on `http://localhost:8000`
5. Install Node dependencies and start Next.js on `http://localhost:3000`

### Manual start

**Backend:**
```bash
# From project root
pip install -r requirements.txt
mkdir -p data
python -m uvicorn backend.main:app --host 0.0.0.0 --port 8000 --reload
```

**Frontend:**
```bash
cd frontend
npm install
npm run dev
```

### Verify local setup

| Check | URL |
|-------|-----|
| Backend health | http://localhost:8000/api/v1/health |
| API docs (Swagger) | http://localhost:8000/docs |
| Frontend UI | http://localhost:3000 |

---

## 4. SQLite File Handling

The database file is created automatically at startup.

```
data/
└── fello.db        # Created on first run
```

**Key behaviours:**

- The `data/` directory must exist before starting the backend. The start scripts create it automatically.
- The file path is relative to the project root: `sqlite:///data/fello.db`.
- To use an absolute path: `DATABASE_URL=sqlite:////var/data/fello.db` (four slashes for absolute on Unix).
- To disable persistence and use in-memory storage: `DATABASE_URL=none`.
- Data persists across backend restarts when SQLite is enabled.

**Backup:**
```bash
cp data/fello.db data/fello.db.bak
```

---

## 5. Cloud Deployment

### Recommended platforms

| Component | Recommended Platform | Notes |
|-----------|---------------------|-------|
| Frontend | Vercel | Zero-config Next.js deployment |
| Backend | Railway / Render / Fly.io | Supports persistent disk for SQLite |
| Database | SQLite on persistent disk | Sufficient for demo scale |

---

### 5a. Frontend — Vercel

1. Push the repo to GitHub.
2. Import the project in [Vercel](https://vercel.com/new).
3. Set **Root Directory** to `frontend`.
4. Add environment variable:
   ```
   NEXT_PUBLIC_API_URL=https://your-backend-url.railway.app
   ```
5. Deploy. Vercel auto-detects Next.js and runs `npm run build && npm start`.

---

### 5b. Backend — Railway

1. Create a new Railway project and connect your GitHub repo.
2. Set **Root Directory** to the project root (not `backend/`).
3. Set the **Start Command**:
   ```
   python -m uvicorn backend.main:app --host 0.0.0.0 --port $PORT
   ```
4. Add a **Persistent Volume** mounted at `/data` (Railway dashboard → Volumes).
5. Set environment variables in Railway dashboard:
   ```
   GEMINI_API_KEY=AIzaSy...
   OPENAI_API_KEY=sk-proj-...
   TAVILY_API_KEY=tvly-...
   DATABASE_URL=sqlite:////data/fello.db
   CORS_ORIGINS=["https://your-frontend.vercel.app"]
   PORT=8000
   ```
6. Deploy. Railway installs `requirements.txt` automatically.

---

### 5c. Backend — Render

1. Create a new **Web Service** in [Render](https://render.com).
2. Connect your GitHub repo.
3. Set:
   - **Build Command**: `pip install -r requirements.txt`
   - **Start Command**: `python -m uvicorn backend.main:app --host 0.0.0.0 --port $PORT`
4. Add a **Persistent Disk** mounted at `/data`.
5. Set environment variables (same as Railway above).

---

### 5d. Backend — Fly.io

Create `fly.toml` in the project root:

```toml
app = "fello-ai-backend"
primary_region = "iad"

[build]
  [build.args]

[http_service]
  internal_port = 8000
  force_https = true

[mounts]
  source = "fello_data"
  destination = "/data"
```

Deploy:
```bash
fly launch
fly secrets set GEMINI_API_KEY=AIzaSy... OPENAI_API_KEY=sk-... TAVILY_API_KEY=tvly-...
fly secrets set DATABASE_URL=sqlite:////data/fello.db
fly secrets set CORS_ORIGINS='["https://your-frontend.vercel.app"]'
fly deploy
```

---

## 6. Production Build (Frontend)

For a production build instead of the dev server:

```bash
cd frontend

# Set backend URL before building
echo "NEXT_PUBLIC_API_URL=https://your-backend-url" > .env.local

npm run build   # Outputs to .next/
npm start       # Serves the production build on port 3000
```

The dev server (`npm run dev`) is fine for demos. Use `npm start` only when deploying to a persistent host.

---

## 7. Troubleshooting

### CORS errors in browser

**Symptom:** `Access-Control-Allow-Origin` error in browser console.

**Fix:** Add the frontend URL to `CORS_ORIGINS` in `backend/.env`:
```
CORS_ORIGINS=["http://localhost:3000","https://your-frontend.vercel.app"]
```
Restart the backend after changing this value.

---

### Backend returns 500 on analysis requests

**Symptom:** `POST /api/v1/analyze/visitor` or `/analyze/company` returns 500.

**Checks:**
1. Confirm `GEMINI_API_KEY` or `OPENAI_API_KEY` is set and valid.
2. Confirm `TAVILY_API_KEY` is set and valid.
3. Check backend logs for the specific error — the startup banner logs which keys are loaded.

---

### SQLite `data/fello.db` not found

**Symptom:** Backend fails to start with a path error.

**Fix:** Create the `data/` directory:
```bash
mkdir data        # macOS/Linux
md data           # Windows
```
Or set `DATABASE_URL=none` to use in-memory storage (data will not persist across restarts).

---

### Frontend shows "Failed to connect to API"

**Symptom:** UI loads but all API calls fail.

**Checks:**
1. Confirm the backend is running: `curl http://localhost:8000/api/v1/health`
2. Confirm `NEXT_PUBLIC_API_URL` matches the backend URL (default: `http://localhost:8000`).
3. For cloud deployments, confirm the backend URL is HTTPS and publicly accessible.

---

### Environment variables not loading

**Symptom:** Backend starts but logs show empty API keys.

**Checks:**
1. Confirm `backend/.env` exists (not `.env` in the project root).
2. Confirm the file has no BOM or Windows line endings — use UTF-8.
3. Real shell environment variables override the `.env` file. Check for conflicts:
   ```bash
   echo $GEMINI_API_KEY    # macOS/Linux
   $env:GEMINI_API_KEY     # PowerShell
   ```

---

### Verify the full system is working

Run the E2E validation script (requires backend running on port 8000):

```bash
python e2e-tests/validate_api.py
```

Expected output:
```
[PASS] Health check
[PASS] Company analysis submitted
[PASS] Job polling - completed
[PASS] Account stored and retrievable
[PASS] Visitor analysis with unknown IP
```

---

## 8. Quick Reference

```
Local URLs
  Frontend:   http://localhost:3000
  Backend:    http://localhost:8000
  API docs:   http://localhost:8000/docs
  Health:     http://localhost:8000/api/v1/health

Start (Windows):   .\start.ps1
Start (Unix):      ./start.sh
Tests (Windows):   .\run_tests.ps1 -All
Tests (Unix):      ./run_tests.sh --all
E2E validation:    python e2e-tests/validate_api.py

SQLite file:       data/fello.db
Backend config:    backend/.env
Frontend config:   frontend/.env.local
```
