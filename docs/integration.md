# Integration Document — Fello AI Account Intelligence System

> **Version**: 1.0  
> **Date**: 2026-03-18  
> **Depends on**: [API Contracts](./api-contracts.md), [Agent Architecture](./agent-architecture.md)

---

## 1. Parallel Development Strategy

Backend and frontend are designed to be built **independently and simultaneously**. The API contract is the binding interface.

### 1.1 What Backend Can Build Independently

| Component | Dependencies | Mock Needed? |
|-----------|-------------|-------------|
| Domain models (`backend/domain/`) | None | No |
| Configuration (`backend/config.py`) | None | No |
| Storage layer (`backend/storage/`) | Domain models | No |
| Tool wrappers (`backend/tools/`) | External APIs (can test with real calls) | No |
| Agents (`backend/agents/`) | Domain models, tools, LLM API key | No |
| Graph workflow (`backend/graph/`) | Agents, domain models | No |
| Controllers (`backend/controllers/`) | Graph, storage | No |
| API routes (`backend/api/`) | Controllers, schemas | No |

**Backend builds bottom-up:** domain → tools → agents → graph → controllers → API.  
No frontend dependency at any stage.

### 1.2 What Frontend Can Build Independently

| Component | Dependencies | Mock Strategy |
|-----------|-------------|---------------|
| TypeScript types (`types/intelligence.ts`) | API contracts doc | Copy from api-contracts.md Section 4 |
| API client (`lib/api.ts`) | Type definitions | Return mock data |
| Hooks (`hooks/`) | API client | Use mock API client |
| Components (`components/`) | Type definitions | Storybook-style with mock props |
| Pages (`app/`) | Hooks, components | Full mock integration |

**Frontend builds with mocks:** Types → API client (mock mode) → hooks → components → pages.

### 1.3 Mock Data for Frontend Development

The frontend MUST include a mock mode that returns realistic data without hitting the backend. This mock data lives in `frontend/lib/mock-data.ts` and uses the exact types from `intelligence.ts`.

**Mock API client pattern:**

```typescript
// frontend/lib/api.ts
const USE_MOCKS = process.env.NEXT_PUBLIC_USE_MOCKS === "true";

export async function submitVisitorAnalysis(
  request: VisitorAnalysisRequest
): Promise<AnalysisResponse> {
  if (USE_MOCKS) return mockAnalysisResponse();
  return fetch(`${API_URL}/api/v1/analyze/visitor`, { ... });
}
```

**When to use mocks:**
- During frontend development before backend is ready
- For demo/presentation if backend is unstable
- For component testing and storybook

**When to stop using mocks:**
- Once backend endpoints are functional
- Set `NEXT_PUBLIC_USE_MOCKS=false` in `.env.local`

---

## 2. Integration Sequence

### 2.1 Phase 1: Independent Development (Hours 0–24)

```
Backend Engineer                    Frontend Engineer
─────────────────                   ─────────────────
domain models                       TypeScript types
   ↓                                   ↓
tools + agents                      mock API client
   ↓                                   ↓
graph workflow                      hooks + components
   ↓                                   ↓
controllers + API routes            pages with mocks
   ↓                                   ↓
Backend runs on :8000               Frontend runs on :3000
```

### 2.2 Phase 2: Integration (Hours 24–36)

```
Integration Engineer
────────────────────
1. Configure CORS on backend (allow localhost:3000)
2. Set NEXT_PUBLIC_API_URL=http://localhost:8000 in frontend
3. Set NEXT_PUBLIC_USE_MOCKS=false
4. Test: submit visitor analysis → poll job → view result
5. Test: submit company analysis → poll job → view result
6. Test: submit batch → poll → view all results
7. Fix any schema mismatches (both sides update to match api-contracts.md)
```

### 2.3 Phase 3: Polish & Demo (Hours 36–48)

```
All Engineers
─────────────
- Fix edge cases (null fields, long processing, errors)
- Add demo data / demo script
- Deploy (Vercel + Railway/Render)
- Record Loom demo
- Write README
```

---

## 3. Backend ↔ Frontend Interaction Rules

### 3.1 API Client Architecture

All frontend API calls go through `frontend/lib/api.ts`:

```typescript
// Base configuration
const API_URL = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";

// Every function:
// 1. Takes typed input
// 2. Calls fetch with proper headers
// 3. Validates response shape (runtime check)
// 4. Returns typed output or throws ApiError
```

**Fetch wrapper requirements:**
- Always set `Content-Type: application/json`
- Always handle non-2xx responses by parsing error body
- Always throw `ApiError` (not raw Response) on failure
- Never use raw `fetch()` outside this file

### 3.2 Polling Implementation

```typescript
// frontend/hooks/useJobPoller.ts
function useJobPoller(jobId: string | null) {
  // Poll every 2 seconds
  // Stop on: COMPLETED, FAILED, or component unmount
  // Return: { status, progress, currentStep, resultId, error }
}

// frontend/hooks/useAccountAnalysis.ts
function useAccountAnalysis() {
  // 1. Submit analysis → get job_id
  // 2. Start polling with useJobPoller
  // 3. On complete → fetch account data
  // Return: { submit, isLoading, progress, account, error }
}
```

### 3.3 State Machine for Analysis Flow

```
                 submit()
                    │
                    ▼
              ┌──────────┐
              │   IDLE    │
              └─────┬─────┘
                    │ POST /analyze/*
                    ▼
              ┌──────────┐
              │ SUBMITTING│
              └─────┬─────┘
                    │ 202 Accepted (got job_id)
                    ▼
              ┌──────────┐
         ┌───▶│ POLLING  │◀───┐
         │    └─────┬─────┘    │
         │          │          │
         │    GET /jobs/{id}   │
         │          │          │
         │    ┌─────▼─────┐   │
         └────│ PROCESSING │───┘  (poll again in 2s)
              └─────┬─────┘
                    │
           ┌────────┼────────┐
           │                  │
     COMPLETED              FAILED
           │                  │
           ▼                  ▼
  ┌─────────────┐    ┌──────────┐
  │  FETCHING   │    │  ERROR   │
  │  account    │    │  (show   │
  └──────┬──────┘    │   retry) │
         │           └──────────┘
         ▼
  ┌──────────┐
  │ COMPLETE │
  │ (render  │
  │  data)   │
  └──────────┘
```

---

## 4. Error Handling Across the Stack

### 4.1 Backend Error Responses

Every error response uses this shape:

```json
{
  "error": {
    "code": "NOT_FOUND",
    "message": "Job abc-123 not found",
    "details": null
  }
}
```

### 4.2 Frontend Error Handling

```typescript
// In lib/api.ts - every API call catches errors:
try {
  const response = await fetch(url, options);
  if (!response.ok) {
    const body = await response.json();
    throw new ApiError(body.error.code, body.error.message, body.error.details);
  }
  return await response.json();
} catch (e) {
  if (e instanceof ApiError) throw e;
  throw new ApiError("NETWORK_ERROR", "Unable to reach server", null);
}
```

### 4.3 Error State Rendering

Every component that displays async data MUST handle 3 states:

| State | UI |
|-------|-----|
| **Loading** | Skeleton placeholder (shadcn/ui `Skeleton`) |
| **Data** | Full content render |
| **Error** | Error message + retry button |

Specific error UIs:

| Error Code | Frontend Behavior |
|------------|------------------|
| `NETWORK_ERROR` | "Unable to connect to server. Check your connection." + retry |
| `NOT_FOUND` | "Analysis not found." (redirect to dashboard) |
| `VALIDATION_ERROR` | Inline form validation messages |
| `INTERNAL_ERROR` | "Something went wrong. Please try again." + retry |
| `RATE_LIMITED` | "Too many requests. Please wait a moment." + auto-retry in 5s |

---

## 5. Environment Variables

### 5.1 Backend (`.env`)

```env
# Required
OPENAI_API_KEY=sk-...
TAVILY_API_KEY=tvly-...

# Optional (LLM fallback used if missing)
CLEARBIT_API_KEY=
APOLLO_API_KEY=

# Server
HOST=0.0.0.0
PORT=8000
CORS_ORIGINS=["http://localhost:3000"]

# Tuning
MODEL_NAME=gpt-4o-mini
TOOL_TIMEOUT_SECONDS=8
TOOL_MAX_RETRIES=3
CACHE_TTL_SECONDS=300
```

### 5.2 Frontend (`.env.local`)

```env
NEXT_PUBLIC_API_URL=http://localhost:8000
NEXT_PUBLIC_USE_MOCKS=false
```

### 5.3 Production Override

```env
# Frontend (Vercel)
NEXT_PUBLIC_API_URL=https://fello-api.railway.app
NEXT_PUBLIC_USE_MOCKS=false

# Backend (Railway/Render)
HOST=0.0.0.0
PORT=$PORT
CORS_ORIGINS=["https://fello-ai.vercel.app"]
```

---

## 6. Versioning Strategy

For the hackathon (48 hours), a simple strategy:

- **No API versioning** beyond the `/api/v1/` prefix already in place
- **No database migrations** (in-memory storage resets on restart)
- **Schema changes** during development: update `api-contracts.md` first, then update both backend schemas and frontend types

**Contract change protocol:**
1. Proposer updates `docs/api-contracts.md`
2. Backend updates `backend/api/schemas/` + domain models to match
3. Frontend updates `frontend/types/intelligence.ts` to match
4. Integration engineer verifies both sides work

---

## 7. Development Commands

### 7.1 Backend

```bash
cd backend
python -m venv venv
source venv/bin/activate  # or venv\Scripts\activate on Windows
pip install -r requirements.txt
cp .env.example .env  # fill in API keys
uvicorn backend.main:app --reload --port 8000
```

### 7.2 Frontend

```bash
cd frontend
npm install
cp .env.example .env.local  # configure API URL
npm run dev  # starts on :3000
```

### 7.3 Both (Integration Testing)

```bash
# Terminal 1: Backend
cd backend && uvicorn backend.main:app --reload --port 8000

# Terminal 2: Frontend
cd frontend && npm run dev

# Terminal 3: Test
curl -X POST http://localhost:8000/api/v1/analyze/company \
  -H "Content-Type: application/json" \
  -d '{"company_name": "Redfin"}'
```

---

## 8. Integration Test Scenarios

### 8.1 Happy Path — Visitor Analysis

1. POST `/analyze/visitor` with sample visitor signal
2. Assert: 202 response with `job_id`
3. GET `/jobs/{job_id}` until `status == "COMPLETED"`
4. Assert: `result_id` is not null
5. GET `/accounts/{result_id}`
6. Assert: response matches `AccountIntelligence` schema
7. Assert: `company` field is non-null with `company_name`
8. Assert: `intent.intent_score` > 0

### 8.2 Happy Path — Company Analysis

1. POST `/analyze/company` with `{"company_name": "Redfin"}`
2. Assert: 202 response
3. Poll until complete
4. Assert: `company.industry` is populated
5. Assert: `persona` is null (no visitor signal)
6. Assert: `playbook` is non-null

### 8.3 Happy Path — Batch Analysis

1. POST `/analyze/batch` with 3 companies
2. Assert: 202 response with `batch_id` and 3 `job_ids`
3. Poll each job independently
4. Assert: all 3 complete successfully

### 8.4 Error Path — Invalid Input

1. POST `/analyze/visitor` with missing `ip_address`
2. Assert: 422 response with validation error details

### 8.5 Error Path — Degraded Output

1. POST `/analyze/visitor` with IP resolving to cloud provider
2. Assert: job completes (not fails)
3. Assert: `company.company_name` may be "Unknown"
4. Assert: `confidence_score` is low

### 8.6 Error Path — Job Not Found

1. GET `/jobs/nonexistent-id`
2. Assert: 404 response with error shape

---

## 9. Demo Checklist

For the Loom demo (5–10 minutes):

- [ ] Show the architecture diagram (from HLD)
- [ ] Submit a visitor analysis with realistic data
- [ ] Show the polling progress in the UI
- [ ] Walk through the full AccountIntelligence result
- [ ] Submit a batch of 5 companies from the problem statement
- [ ] Show how intent scoring works with page-level breakdown
- [ ] Show the AI summary and sales playbook
- [ ] Briefly show the agent architecture (LangGraph parallel execution)
- [ ] Mention tech stack choices and why
