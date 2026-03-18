# High-Level Design — Fello AI Account Intelligence System

> **Version**: 1.0  
> **Date**: 2026-03-18  
> **Status**: Architecture Phase — No implementation code exists yet

---

## 1. System Purpose

Convert raw visitor signals (IP, page views, behavior) and minimal company inputs (name, domain) into structured, sales-ready account intelligence using a multi-agent AI pipeline.

**Two input modes:**
- **Visitor Signal Analysis** — IP + behavior → company identification → full enrichment
- **Company Name Analysis** — company name/domain → full enrichment

Both converge into the same enrichment pipeline after company identification.

---

## 2. Architecture Overview

```
┌─────────────────────────────────────────────────────────────────────┐
│                        FRONTEND (Next.js 14)                        │
│                                                                     │
│  ┌──────────┐  ┌──────────────┐  ┌───────────┐  ┌──────────────┐  │
│  │Dashboard │  │AnalysisForm  │  │AccountView│  │ BatchInput   │  │
│  │  (list)  │  │(visitor/co.) │  │  (detail) │  │ (CSV/multi)  │  │
│  └──────────┘  └──────────────┘  └───────────┘  └──────────────┘  │
│                         │ via lib/api.ts                            │
└─────────────────────────┼───────────────────────────────────────────┘
                          │ HTTP (JSON)
                          ▼
┌─────────────────────────────────────────────────────────────────────┐
│                      API LAYER (FastAPI)                             │
│                                                                     │
│  POST /analyze/visitor  │  POST /analyze/company                    │
│  POST /analyze/batch    │  GET  /jobs/{id}                          │
│  GET  /accounts         │  GET  /accounts/{id}                      │
│                                                                     │
│  Routes → Controllers (thin delegation)                             │
└─────────────────────────┼───────────────────────────────────────────┘
                          │
                          ▼
┌─────────────────────────────────────────────────────────────────────┐
│                    CONTROLLER LAYER                                  │
│                                                                     │
│  AnalysisController                                                 │
│  ├── Validates input                                                │
│  ├── Creates job record                                             │
│  ├── Dispatches to LangGraph workflow (background task)             │
│  └── Returns job_id immediately (202 Accepted)                      │
└─────────────────────────┼───────────────────────────────────────────┘
                          │
                          ▼
┌─────────────────────────────────────────────────────────────────────┐
│                  GRAPH ORCHESTRATOR (LangGraph)                      │
│                                                                     │
│  ┌─────────────┐                                                    │
│  │    START     │                                                    │
│  └──────┬──────┘                                                    │
│         │                                                           │
│         ▼                                                           │
│  ┌─────────────────┐     (only for visitor input)                   │
│  │ Identification   │────────────────────────┐                      │
│  │ Agent            │                        │                      │
│  └─────────────────┘                         │                      │
│         │ (company input skips here)         │                      │
│         ▼                                    ▼                      │
│  ┌──────────────────────────────────────────────┐                   │
│  │          PARALLEL FAN-OUT (Send)             │                   │
│  │                                              │                   │
│  │  ┌────────────┐ ┌───────────┐ ┌───────────┐ │                   │
│  │  │ Enrichment │ │  Intent   │ │  Persona  │ │                   │
│  │  │   Agent    │ │  Scorer   │ │   Agent   │ │                   │
│  │  └────────────┘ └───────────┘ └───────────┘ │                   │
│  └──────────────────────────────────────────────┘                   │
│         │                                                           │
│         ▼                                                           │
│  ┌──────────────────────────────────────────────┐                   │
│  │          PARALLEL FAN-OUT (Send)             │                   │
│  │                                              │                   │
│  │  ┌────────────┐ ┌───────────┐ ┌───────────┐ │                   │
│  │  │ TechStack  │ │  Signals  │ │Leadership │ │                   │
│  │  │   Agent    │ │   Agent   │ │   Agent   │ │                   │
│  │  └────────────┘ └───────────┘ └───────────┘ │                   │
│  └──────────────────────────────────────────────┘                   │
│         │                                                           │
│         ▼                                                           │
│  ┌─────────────────┐                                                │
│  │ Playbook Agent  │                                                │
│  └────────┬────────┘                                                │
│           ▼                                                         │
│  ┌─────────────────┐                                                │
│  │ Summary Agent   │                                                │
│  └────────┬────────┘                                                │
│           ▼                                                         │
│  ┌─────────────────┐                                                │
│  │      END        │──── Writes AccountIntelligence to store        │
│  └─────────────────┘                                                │
└─────────────────────────────────────────────────────────────────────┘
                          │
                          ▼
┌─────────────────────────────────────────────────────────────────────┐
│                       TOOLS LAYER                                    │
│  (Called by agents — never call agents or LLM)                      │
│                                                                     │
│  ┌─────────────┐  ┌─────────────┐  ┌───────────┐  ┌────────────┐  │
│  │ IP Lookup   │  │ Web Search  │  │  Scraper  │  │Enrichment  │  │
│  │ (ipapi.co)  │  │ (Tavily)    │  │ (httpx)   │  │(Clearbit/  │  │
│  │             │  │             │  │           │  │ Apollo/LLM)│  │
│  └─────────────┘  └─────────────┘  └───────────┘  └────────────┘  │
└─────────────────────────────────────────────────────────────────────┘
                          │
                          ▼
┌─────────────────────────────────────────────────────────────────────┐
│                    DOMAIN MODELS (Pydantic)                          │
│  Pure value objects — no I/O, no LLM, no HTTP                       │
│                                                                     │
│  VisitorSignal · CompanyInput · CompanyProfile · PersonaInference   │
│  IntentScore · TechStack · BusinessSignals · LeadershipProfile      │
│  SalesPlaybook · AccountIntelligence (aggregate root)               │
└─────────────────────────────────────────────────────────────────────┘
                          │
                          ▼
┌─────────────────────────────────────────────────────────────────────┐
│                    STORAGE (In-Memory)                               │
│                                                                     │
│  JobStore      — tracks analysis jobs (status, progress, result)    │
│  AccountStore  — persists AccountIntelligence results               │
│                                                                     │
│  (Dict-based for hackathon; interface supports future DB migration) │
└─────────────────────────────────────────────────────────────────────┘
```

---

## 3. Module Inventory

| Module | Technology | Responsibility | Boundary Rule |
|--------|-----------|---------------|---------------|
| **Frontend** | Next.js 14, TypeScript, Tailwind, shadcn/ui | UI rendering, user input, polling | No business logic, no direct fetch |
| **API** | FastAPI, Pydantic | HTTP routing, request validation, response shaping | No agents, no LLM calls |
| **Controllers** | Plain Python async | Job creation, graph dispatch, result retrieval | No HTTP concerns, no LLM calls |
| **Graph** | LangGraph | Agent orchestration, parallel fan-out, state management | No HTTP, no direct tool calls |
| **Agents** | LangChain/OpenAI | LLM reasoning, domain model production | No HTTP, no DB, no tool instantiation |
| **Tools** | httpx, Tavily SDK | External API calls, web scraping | No LLM, no domain logic |
| **Domain** | Pydantic v2 | Data contracts, validation, serialization | No imports from any other layer |
| **Storage** | Python dicts (async-safe) | Job tracking, result persistence | No business logic |

---

## 4. Data Flow

### 4.1 Visitor Signal Flow

```
User submits visitor signal (IP, pages, behavior)
    │
    ▼
API validates → Controller creates job → returns 202 + job_id
    │
    ▼ (background)
IdentificationAgent: IP → company name via ip_lookup tool
    │
    ▼
PARALLEL: EnrichmentAgent + IntentScorerAgent + PersonaAgent
    │
    ▼
PARALLEL: TechStackAgent + SignalsAgent + LeadershipAgent
    │
    ▼
PlaybookAgent: synthesizes all data → sales recommendations
    │
    ▼
SummaryAgent: generates AI narrative → AccountIntelligence
    │
    ▼
Result stored → job marked complete
    │
    ▼
Frontend polls job → gets result_id → fetches full account
```

### 4.2 Company Name Flow

```
User submits company name (+ optional domain)
    │
    ▼
API validates → Controller creates job → returns 202 + job_id
    │
    ▼ (background)
(Skip identification — company already known)
    │
    ▼
PARALLEL: EnrichmentAgent + IntentScorerAgent + PersonaAgent
    │  (IntentScorer uses default signals; PersonaAgent skips or uses generic)
    │
    ▼
PARALLEL: TechStackAgent + SignalsAgent + LeadershipAgent
    │
    ▼
PlaybookAgent → SummaryAgent → AccountIntelligence
    │
    ▼
Result stored → job marked complete
```

### 4.3 Batch Flow

```
User submits list of company names
    │
    ▼
Controller creates one job per company + batch_id
    │
    ▼
Each company processed independently (same as 4.2)
    │
    ▼
Frontend polls batch status → lists results as they complete
```

---

## 5. Communication Patterns

| Pattern | Where Used | Details |
|---------|-----------|---------|
| **Async job + polling** | API → Frontend | POST returns 202 + job_id; GET /jobs/{id} polled every 2s |
| **Background tasks** | Controller → Graph | FastAPI BackgroundTasks or asyncio.create_task |
| **LangGraph Send()** | Graph → Agents | Parallel fan-out to independent agents |
| **Tool delegation** | Agent → Tool | Agent calls tool via injected reference; tool returns Optional[dict] |
| **Domain model passing** | All layers | Pydantic models are the universal data contract |

---

## 6. Technology Stack

| Layer | Technology | Version | Rationale |
|-------|-----------|---------|-----------|
| Frontend | Next.js | 14.x | App router, server components, fast DX |
| UI Kit | shadcn/ui + Tailwind | latest | Composable, dark-theme-ready, accessible |
| Backend | FastAPI | 0.110+ | Async-native, auto OpenAPI, Pydantic integration |
| Orchestration | LangGraph | 0.2+ | Stateful agent graphs with parallel execution |
| LLM | OpenAI GPT-4o-mini | — | Structured outputs, fast, cost-effective for hackathon |
| Search | Tavily API | — | AI-optimized search, clean results |
| HTTP Client | httpx | 0.27+ | Async, timeout support, connection pooling |
| IP Lookup | ipapi.co + ip-api.com | — | Free tier, fallback pattern |
| Enrichment | Clearbit + Apollo | — | Company data APIs with LLM fallback |
| Storage | In-memory (dict) | — | Hackathon scope; interface supports future DB |

---

## 7. Security & Configuration

- All API keys via environment variables (`.env` file, never committed)
- CORS configured for frontend origin only
- No authentication for hackathon (noted as future extension)
- Rate limiting on external tool calls (built into tool layer)
- Input sanitization via Pydantic validation

---

## 8. Deployment Architecture (Hackathon)

```
┌──────────────────────┐    ┌──────────────────────┐
│  Frontend (Vercel)   │───▶│  Backend (Railway/    │
│  Next.js             │◀───│  Render/local)        │
│  Port 3000           │    │  FastAPI              │
└──────────────────────┘    │  Port 8000            │
                            └──────────────────────┘
```

- Frontend: `npm run dev` (local) or Vercel deploy
- Backend: `uvicorn backend.main:app` (local) or Railway/Render
- Both connect via `NEXT_PUBLIC_API_URL` environment variable

---

## 9. Key Architectural Decisions

| Decision | Choice | Rationale |
|----------|--------|-----------|
| In-memory storage | Dict-based stores | 48-hour hackathon; no DB setup overhead |
| Async job pattern | 202 + polling | Agent pipeline takes 10-30s; can't block HTTP |
| LangGraph over raw asyncio | LangGraph Send() | Built-in parallel fan-out, state management, retries |
| GPT-4o-mini over GPT-4 | Cost + speed | 10x cheaper, 3x faster, sufficient for structured outputs |
| Separate controller layer | Controllers between API and Graph | Keeps API routes thin; testable orchestration logic |
| Two parallel stages | Fan-out twice | Stage 2 agents depend on Stage 1 enrichment data |
