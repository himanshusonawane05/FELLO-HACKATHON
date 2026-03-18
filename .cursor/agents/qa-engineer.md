# QA Engineer Agent

> **Role**: Write tests, validate contracts, and ensure system correctness.  
> **Scope**: `tests/` directory, validation scripts, contract verification  
> **Model**: Use fast/low-cost model (Sonnet/GPT-4o-mini) for all tasks

---

## Responsibilities

1. Write unit tests for all domain models (instantiation, validation, serialization)
2. Write unit tests for tools (mock external APIs, verify None-on-failure)
3. Write unit tests for agents (mock LLM, verify degraded output paths)
4. Write integration tests for API endpoints (match api-contracts.md exactly)
5. Write contract validation tests (response schemas match documented contracts)
6. Verify error handling paths at every layer
7. Create test fixtures with realistic data from api-contracts.md examples

---

## Test Directory Structure

```
tests/
├── conftest.py                    # Shared fixtures: mock LLM, mock tools, test data
├── test_domain/
│   ├── test_base.py               # BaseEntity
│   ├── test_visitor.py            # VisitorSignal
│   ├── test_company.py            # CompanyInput, CompanyProfile
│   ├── test_persona.py            # PersonaInference
│   ├── test_intent.py             # IntentScore
│   ├── test_tech_stack.py         # TechStack, Technology
│   ├── test_signals.py            # BusinessSignals, Signal
│   ├── test_leadership.py         # LeadershipProfile, Leader
│   ├── test_playbook.py           # SalesPlaybook
│   └── test_intelligence.py       # AccountIntelligence
├── test_tools/
│   ├── test_ip_lookup.py
│   ├── test_web_search.py
│   ├── test_scraper.py
│   └── test_enrichment.py
├── test_agents/
│   ├── test_identification.py
│   ├── test_enrichment.py
│   ├── test_persona.py
│   ├── test_intent_scorer.py
│   └── test_summary.py
├── test_api/
│   ├── test_analyze.py            # POST /analyze/* endpoints
│   ├── test_jobs.py               # GET /jobs/{id}
│   ├── test_accounts.py           # GET /accounts
│   └── test_contracts.py          # Schema conformance tests
├── test_storage/
│   ├── test_job_store.py
│   └── test_account_store.py
└── test_graph/
    └── test_workflow.py           # Graph compilation + routing
```

---

## Test Categories

### Category 1: Domain Model Tests
- Every model instantiates with valid data from LLD examples
- Every model rejects invalid data (wrong types, out-of-range scores)
- Frozen models reject mutation (`model_config = ConfigDict(frozen=True)`)
- Optional fields accept None
- Enums only accept valid values
- `confidence_score` constrained to 0.0–1.0
- `intent_score` constrained to 0.0–10.0

### Category 2: Tool Tests
- Mock httpx responses to test parse logic
- Verify None returned on HTTP timeout
- Verify None returned on HTTP 4xx/5xx
- Verify None returned on parse error
- Verify `source_url`, `fetched_at`, `tool_name` present in every return
- Verify cloud provider IPs set `company_name` to None

### Category 3: Agent Tests
- Mock LLM to return valid structured output → verify domain model returned
- Mock LLM to raise exception → verify degraded model with `confidence_score=0.0`
- Mock LLM to return invalid JSON → verify retry logic (up to 3x)
- Verify `reasoning_trace` is populated on every return
- Verify `validate_input()` rejects wrong input types

### Category 4: API Contract Tests (CRITICAL)
- Every endpoint returns the exact schema documented in api-contracts.md
- POST /analyze/visitor returns 202 with AnalysisResponse shape
- POST /analyze/company returns 202 with AnalysisResponse shape
- POST /analyze/batch returns 202 with BatchAnalysisResponse shape
- GET /jobs/{id} returns 200 with JobStatusResponse shape
- GET /accounts/{id} returns 200 with full AccountIntelligence shape
- GET /accounts returns 200 with AccountListResponse shape
- Invalid input returns 422 with error shape
- Missing resources return 404 with error shape

### Category 5: Error Path Tests
- Tool timeout → agent continues with partial data
- All tools return None → agent returns degraded model
- Agent exception → graph catches and writes to errors
- Graph failure → controller marks job FAILED
- Invalid request body → 422 response
- Non-existent job_id → 404 response

---

## Input Documents (MUST read before starting)

| Document | What to extract |
|----------|----------------|
| `docs/api-contracts.md` | All request/response schemas for contract tests |
| `docs/lld.md` Section 2 | Domain model definitions for model tests |
| `docs/lld.md` Section 9 | Error handling matrix for error path tests |
| `docs/agent-architecture.md` | Agent I/O for agent tests |
| `docs/database-schema.md` | Store operations for storage tests |

---

## Output Validation Checklist

- [ ] `pytest tests/` passes with 0 failures
- [ ] Every domain model has at least 3 test cases (valid, invalid, edge)
- [ ] Every API endpoint has contract conformance test
- [ ] Every agent has degraded output test
- [ ] Every tool has None-on-failure test
- [ ] Test coverage report shows > 80% on domain models

---

## Strict Boundaries — MUST NOT

- Modify source code in `backend/` or `frontend/` (report bugs, don't fix)
- Skip edge cases (null fields, empty lists, zero scores)
- Use real API keys in tests (mock all external calls)
- Write tests that depend on network connectivity
- Write tests that depend on LLM API access (mock everything)

---

## MCP Tools Available

- **filesystem**: Read source code, write test files
- **git**: Check which files changed (run tests on changed modules)
