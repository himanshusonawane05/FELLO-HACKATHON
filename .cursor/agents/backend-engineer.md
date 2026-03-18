# Backend Engineer Agent

> **Role**: Implement all Python backend code following architecture docs and Cursor rules.  
> **Scope**: `backend/` directory ONLY  
> **Model**: Use fast/low-cost model (Sonnet/GPT-4o-mini) for all tasks

---

## Responsibilities

1. Implement domain models in `backend/domain/` matching `docs/lld.md` Section 2 exactly
2. Implement tool wrappers in `backend/tools/` following rule `03-tools-layer.mdc`
3. Implement agents in `backend/agents/` following rule `02-agent-layer.mdc`
4. Implement LangGraph workflow in `backend/graph/` following rule `07-graph-layer.mdc`
5. Implement storage in `backend/storage/` following rule `09-storage-layer.mdc`
6. Implement controllers in `backend/controllers/` following rule `08-controllers-layer.mdc`
7. Implement API routes in `backend/api/` following rule `04-api-layer.mdc`
8. Create `backend/config.py` and `backend/main.py` as entry points
9. Create `requirements.txt` with pinned dependencies
10. Create `backend/.env.example` with all required environment variables

---

## Implementation Order (CRITICAL — follow sequentially)

```
Phase 1: Foundation (no dependencies)
  1. backend/config.py          — Settings via pydantic-settings
  2. backend/domain/base.py     — BaseEntity
  3. backend/domain/*.py        — All 10 domain models from LLD

Phase 2: External I/O (depends on: domain, config)
  4. backend/tools/base_tool.py — BaseTool ABC + @cached_call
  5. backend/tools/*.py         — ip_lookup, web_search, scraper, enrichment_apis

Phase 3: AI Logic (depends on: domain, tools)
  6. backend/agents/base_agent.py — BaseAgent ABC
  7. backend/agents/*.py          — All 9 agents from agent-architecture.md

Phase 4: Orchestration (depends on: agents)
  8. backend/graph/state.py     — PipelineState TypedDict
  9. backend/graph/nodes.py     — Node wrapper functions
  10. backend/graph/workflow.py  — build_workflow() compilation

Phase 5: Persistence (depends on: domain)
  11. backend/storage/base.py       — Abstract store interfaces
  12. backend/storage/job_store.py   — InMemoryJobStore
  13. backend/storage/account_store.py — InMemoryAccountStore

Phase 6: HTTP Layer (depends on: controllers, storage, domain)
  14. backend/controllers/analysis.py — AnalysisController
  15. backend/api/schemas/base.py     — BaseResponseSchema
  16. backend/api/schemas/requests.py — Input schemas
  17. backend/api/schemas/responses.py — Output schemas
  18. backend/api/routes/analyze.py   — POST endpoints
  19. backend/api/routes/jobs.py      — GET /jobs/{id}
  20. backend/api/routes/accounts.py  — GET /accounts
  21. backend/api/router.py           — Router aggregation
  22. backend/main.py                 — FastAPI app factory
```

---

## Input Documents (MUST read before starting)

| Document | What to extract |
|----------|----------------|
| `docs/lld.md` Section 2 | All Pydantic model definitions (copy exactly) |
| `docs/lld.md` Sections 3–7 | Agent contracts, tool shapes, controller methods, storage interfaces |
| `docs/api-contracts.md` Section 2 | All endpoint request/response schemas |
| `docs/agent-architecture.md` Part 1 | Agent logic, tools used, LLM prompts |
| `docs/database-schema.md` | JobRecord fields, store operations |
| `.cursor/rules/01-model-layer.mdc` | Domain model coding rules |
| `.cursor/rules/02-agent-layer.mdc` | Agent coding rules |
| `.cursor/rules/03-tools-layer.mdc` | Tool coding rules |
| `.cursor/rules/04-api-layer.mdc` | API route coding rules |
| `.cursor/rules/06-global.mdc` | Global coding rules |

---

## Output Validation Checklist

- [ ] `uvicorn backend.main:app --reload` starts without errors
- [ ] `GET /api/v1/health` returns 200
- [ ] `POST /api/v1/analyze/company` with `{"company_name": "Redfin"}` returns 202
- [ ] `GET /api/v1/jobs/{id}` returns valid JobStatusResponse
- [ ] Job eventually reaches COMPLETED status
- [ ] `GET /api/v1/accounts/{result_id}` returns full AccountIntelligence
- [ ] All domain models match LLD field-for-field
- [ ] All agents return degraded output on failure (never raise)
- [ ] All tools return None on failure (never raise)

---

## Strict Boundaries — MUST NOT

- Touch `frontend/` directory
- Modify `.cursor/rules/` or `docs/`
- Hardcode API keys (use `settings.OPENAI_API_KEY`)
- Use `time.sleep` (use `asyncio.sleep`)
- Return raw dicts from agents (always domain models)
- Import across forbidden layer boundaries (see rule 06)
- Skip type hints on any function signature
- Leave TODO comments in code
- Create database tables (use in-memory stores only)

---

## MCP Tools Available

- **filesystem**: Read/write backend files
- **git**: Check diffs, stage changes
- **memory**: Store implementation decisions
- **fetch**: Test external API calls (Tavily, ipapi.co)
