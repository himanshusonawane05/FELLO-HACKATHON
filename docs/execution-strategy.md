# Execution Strategy — Parallel Development Plan

> **Version**: 1.0  
> **Date**: 2026-03-18  
> **Depends on**: [Agent Architecture](./agent-architecture.md), [Model Strategy](./model-strategy.md)

---

## 1. Execution Phases

### Phase 0: Foundation (Sequential — 30 min)

**Agent**: backend-engineer  
**Model**: Tier 2 (fast)  
**Blocking**: All other phases depend on this

```
Tasks:
  1. backend/config.py (Settings)
  2. backend/domain/base.py (BaseEntity)
  3. backend/domain/*.py (ALL 10 domain models)
  4. backend/__init__.py files
  5. requirements.txt

Output:
  - All Pydantic models importable
  - requirements.txt with pinned versions
```

**Why sequential**: Domain models are the universal contract. Every other agent needs them.

---

### Phase 1: Parallel Build (3 parallel tracks — 2-3 hours)

Once domain models exist, three agents work simultaneously:

```
┌─────────────────────────┐  ┌─────────────────────────┐  ┌─────────────────────────┐
│   TRACK A: Backend      │  │   TRACK B: Frontend     │  │   TRACK C: AI Agents    │
│   (backend-engineer)    │  │   (frontend-engineer)   │  │   (ai-agent-engineer)   │
│   Model: Tier 2         │  │   Model: Tier 2         │  │   Model: Tier 1 + 2     │
│                         │  │                         │  │                         │
│   1. tools/base_tool.py │  │   1. Scaffold Next.js   │  │   1. agents/base_agent  │
│   2. tools/ip_lookup.py │  │   2. types/intelligence │  │   2. System prompts     │
│   3. tools/web_search   │  │   3. lib/api.ts (mocks) │  │      (Tier 1)           │
│   4. tools/scraper.py   │  │   4. lib/mock-data.ts   │  │   3. Agent classes      │
│   5. tools/enrichment   │  │   5. hooks/useJobPoller  │  │      (Tier 2)           │
│   6. storage/base.py    │  │   6. hooks/useAnalysis   │  │   4. graph/state.py     │
│   7. storage/job_store  │  │   7. components/*        │  │   5. graph/nodes.py     │
│   8. storage/account    │  │   8. app/layout.tsx      │  │   6. graph/workflow.py  │
│   9. controllers/       │  │   9. app/page.tsx        │  │                         │
│  10. api/schemas/*      │  │  10. app/account/[id]    │  │                         │
│  11. api/routes/*       │  │                         │  │                         │
│  12. api/router.py      │  │                         │  │                         │
│  13. main.py            │  │                         │  │                         │
└─────────────────────────┘  └─────────────────────────┘  └─────────────────────────┘
         │                            │                            │
         ▼                            ▼                            ▼
   Backend on :8000            Frontend on :3000           Agents importable
   All endpoints live          Renders with mocks          Graph compiles
```

**Why parallel**: 
- Track A (Backend) and Track B (Frontend) share NO files — only the contract doc
- Track C (AI Agents) works on `backend/agents/` and `backend/graph/` — no overlap with Track A's work on `backend/tools/`, `backend/storage/`, `backend/api/`

**Coordination point**: Track A needs Track C's agents to be importable before wiring them into controllers. If Track C is slower, Track A can stub the graph call.

---

### Phase 2: Integration (Sequential — 1 hour)

**Agent**: integration-engineer  
**Model**: Tier 2 (fast)  
**Blocking**: Requires Phase 1 tracks A+B+C complete

```
Tasks:
  1. Configure CORS (backend .env)
  2. Set NEXT_PUBLIC_API_URL (frontend .env.local)
  3. Switch NEXT_PUBLIC_USE_MOCKS=false
  4. Test: visitor analysis end-to-end
  5. Test: company analysis end-to-end
  6. Test: batch analysis end-to-end
  7. Test: error paths (invalid input, failed jobs)
  8. Fix any schema mismatches

Output:
  - Frontend talks to real backend
  - All 3 analysis flows work end-to-end
```

---

### Phase 3: QA (Can overlap with Phase 2 — 1 hour)

**Agent**: qa-engineer  
**Model**: Tier 2 (fast)  
**Can start**: As soon as backend code exists (Phase 1 Track A)

```
Tasks:
  1. Domain model tests (can start during Phase 1)
  2. Tool tests with mocked HTTP
  3. Agent tests with mocked LLM
  4. API contract tests
  5. Storage tests
  6. Error path tests

Output:
  - tests/ directory with comprehensive test suite
  - pytest passes with 0 failures
```

---

### Phase 4: Polish & Demo (1 hour)

**Agents**: integration-engineer + documentation-writer skill  
**Model**: Tier 2 (fast)

```
Tasks:
  1. Create demo script with Problem.md companies
  2. Create sample visitor signal data
  3. Write README.md
  4. Create .gitignore
  5. Deploy frontend to Vercel
  6. Deploy backend to Railway/Render
  7. Verify deployed system works

Output:
  - Working deployed prototype
  - README with setup instructions
  - Demo-ready system
```

---

## 2. Dependency Graph

```
Phase 0: Domain Models
    │
    ├──────────────┬──────────────┐
    ▼              ▼              ▼
Phase 1A:     Phase 1B:     Phase 1C:
Backend       Frontend      AI Agents
(tools,api)   (UI,mocks)    (agents,graph)
    │              │              │
    └──────────────┼──────────────┘
                   ▼
              Phase 2:
              Integration
                   │
                   ▼
              Phase 3:
              QA Tests
                   │
                   ▼
              Phase 4:
              Polish & Demo
```

---

## 3. Communication Between Agents

Agents communicate ONLY through:

1. **Documentation** (`docs/`) — the source of truth
2. **Domain models** (`backend/domain/`) — shared type system
3. **API contracts** (`docs/api-contracts.md`) — interface between backend and frontend
4. **MCP memory** — persistent decisions across sessions
5. **Git history** — what changed and why

Agents NEVER communicate by:
- Modifying each other's files
- Leaving TODO comments for other agents
- Making assumptions about undocumented behavior

---

## 4. File Ownership Matrix

Every file has exactly ONE owning agent. No shared writes.

| Directory | Owner | Other Agents |
|-----------|-------|-------------|
| `backend/domain/` | backend-engineer | Read-only for all others |
| `backend/tools/` | backend-engineer | Read-only for ai-agent-engineer |
| `backend/agents/` | ai-agent-engineer | Read-only for backend-engineer |
| `backend/graph/` | ai-agent-engineer | Read-only for backend-engineer |
| `backend/storage/` | backend-engineer | Read-only for all others |
| `backend/controllers/` | backend-engineer | Read-only for all others |
| `backend/api/` | backend-engineer | Read-only for all others |
| `backend/config.py` | backend-engineer | Read-only for all others |
| `backend/main.py` | backend-engineer | Read-only for integration-engineer |
| `frontend/` | frontend-engineer | Read-only for integration-engineer |
| `tests/` | qa-engineer | Read-only for all others |
| `docs/` | system-architect | Read-only for all others |
| `.cursor/` | system-architect | Read-only for all others |
| `scripts/` | integration-engineer | Read-only for all others |
| `README.md` | integration-engineer | — |
| `.gitignore` | integration-engineer | — |
| `.env*` | integration-engineer | — |

---

## 5. Handoff Checkpoints

At each phase boundary, verify these before proceeding:

### Phase 0 → Phase 1

- [ ] All domain models import without errors: `python -c "from backend.domain import *"`
- [ ] Every model instantiates with example data from LLD
- [ ] `requirements.txt` exists with all dependencies

### Phase 1 → Phase 2

- [ ] Backend: `uvicorn backend.main:app` starts on :8000
- [ ] Backend: `GET /api/v1/health` returns 200
- [ ] Backend: `POST /api/v1/analyze/company` returns 202
- [ ] Frontend: `npm run dev` starts on :3000
- [ ] Frontend: Dashboard renders with mock data
- [ ] Graph: `build_workflow()` returns compiled graph without error

### Phase 2 → Phase 3

- [ ] Frontend submits company analysis → sees real results
- [ ] Frontend submits visitor analysis → sees real results
- [ ] Polling progress bar updates in real-time
- [ ] Error states render (invalid input, failed job)

### Phase 3 → Phase 4

- [ ] `pytest tests/` passes with 0 failures
- [ ] All API contract tests pass
- [ ] All error path tests pass

---

## 6. Risk Mitigation

| Risk | Likelihood | Mitigation |
|------|-----------|------------|
| LLM API quota exceeded | Medium | Use GPT-4o-mini (cheap), cache tool results |
| External API (Tavily/ipapi) down | Medium | LLM fallback in enrichment tool |
| Agent produces wrong output shape | High | Pydantic validation catches at every boundary |
| Frontend-backend schema mismatch | Medium | Contract tests catch; api-contracts.md is source of truth |
| LangGraph parallel execution issues | Medium | Each node has try/except; graph never crashes |
| Time overrun on implementation | High | Phase 1 tracks can parallelize; frontend mocks work independently |

---

## 7. Time Budget (48-hour hackathon)

| Phase | Duration | Cumulative |
|-------|----------|-----------|
| Phase 0: Foundation | 0.5 hr | 0.5 hr |
| Phase 1: Parallel Build | 3 hr | 3.5 hr |
| Phase 2: Integration | 1 hr | 4.5 hr |
| Phase 3: QA | 1 hr (overlaps Phase 2) | 5 hr |
| Phase 4: Polish & Demo | 1 hr | 6 hr |
| **Total active dev time** | | **~6 hours** |

Remaining time available for: iteration, debugging, demo recording, presentation prep.
