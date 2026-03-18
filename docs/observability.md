# Observability — Logging, Tracing & Debugging

> **Version**: 1.0  
> **Date**: 2026-03-18  
> **Depends on**: [Data Pipeline](./data-pipeline.md), [LLD](./lld.md), [Agent Architecture](./agent-architecture.md)

---

## 1. Logging Strategy

### 1.1 Logger Hierarchy

Every module uses Python's `logging` with a structured hierarchy:

```
backend                          # root logger
├── backend.api                  # HTTP request/response
├── backend.controllers          # job lifecycle
├── backend.graph                # pipeline execution
├── backend.agents               # per-agent reasoning
│   ├── backend.agents.identification
│   ├── backend.agents.enrichment
│   ├── backend.agents.persona
│   ├── backend.agents.intent_scorer
│   ├── backend.agents.tech_stack
│   ├── backend.agents.signals
│   ├── backend.agents.leadership
│   ├── backend.agents.playbook
│   └── backend.agents.summary
├── backend.tools                # external API calls
│   ├── backend.tools.ip_lookup
│   ├── backend.tools.web_search
│   ├── backend.tools.scraper
│   └── backend.tools.enrichment_apis
└── backend.storage              # store operations
```

### 1.2 Log Levels by Layer

| Layer | DEBUG | INFO | WARNING | ERROR |
|-------|-------|------|---------|-------|
| **API** | Request headers, body size | Request received, response sent | Slow response (>5s) | Unhandled exception |
| **Controllers** | Job state transitions | Job created, job completed | Job taking >20s | Job failed |
| **Graph** | Node entry/exit with state keys | Stage boundaries, parallel fan-out | Node retry | Node exception caught |
| **Agents** | LLM prompt/response (truncated) | Agent start/complete with confidence | Tool returned None | LLM failure, degraded output |
| **Tools** | HTTP request URL, response status | Tool call success with latency | Retry triggered | All retries exhausted |
| **Storage** | Dict operations | Record created/updated | — | — |

### 1.3 Structured Log Format

Every log entry includes these fields for machine parseability:

```json
{
  "timestamp": "2026-03-18T10:05:12.345Z",
  "level": "INFO",
  "logger": "backend.agents.enrichment",
  "job_id": "550e8400-e29b-41d4-a716-446655440000",
  "agent": "EnrichmentAgent",
  "event": "agent_complete",
  "confidence_score": 0.85,
  "duration_ms": 3200,
  "data_sources": ["clearbit", "web_search", "scraper"],
  "message": "Company profile enriched for Acme Mortgage"
}
```

**Required context fields per layer**:

| Layer | Required Fields |
|-------|----------------|
| API | `request_id`, `method`, `path`, `status_code`, `duration_ms` |
| Controller | `job_id`, `analysis_type`, `event` |
| Graph | `job_id`, `node_name`, `event`, `duration_ms` |
| Agent | `job_id`, `agent`, `event`, `confidence_score`, `duration_ms` |
| Tool | `job_id`, `tool_name`, `event`, `duration_ms`, `source_url` |

### 1.4 Sensitive Data Rules

- **Never log**: API keys, full IP addresses (mask last octet), raw LLM prompts in production
- **Truncate**: LLM responses to first 200 chars in DEBUG; omit in INFO+
- **Hash**: Tool input parameters logged as SHA-256 hash (not raw values)
- **Allowed**: Company names, domains, page URLs, scores, tool names

---

## 2. Execution Tracing

### 2.1 Pipeline Trace via `reasoning_trace`

Every `AccountIntelligence` output contains a complete `reasoning_trace` — a chronological list of decisions made across all agents during the pipeline execution.

**Example trace for a completed analysis**:

```json
[
  "IP 34.201.114.42 resolved to Acme Mortgage via ipapi.co (confidence: 0.8)",
  "Company enriched via Clearbit + web search + scraper (3 sources)",
  "Intent scored at 8.9/10 based on pricing+case study+repeat visit signals",
  "Persona inferred as Head of Sales Operations from page pattern (confidence: 0.72)",
  "Tech stack detected: 4 technologies via script tag analysis on acmemortgage.com",
  "2 business signals found: hiring SDRs + Florida expansion",
  "2 leadership contacts discovered: VP Sales Jane Smith, CEO Bob Johnson",
  "Playbook generated with HIGH priority based on intent 8.9 + hiring signals",
  "Aggregate confidence: 0.82 (weighted average of 7 sub-scores)"
]
```

This trace is:
- Stored in `AccountIntelligence.reasoning_trace` (persisted in AccountStore)
- Returned in the API response at `GET /accounts/{id}`
- Viewable by the end user in the frontend
- The primary debugging artifact for understanding any analysis result

### 2.2 Stage-by-Stage Job Tracking

The `JobStore` tracks progress in real-time via `progress` (0.0–1.0) and `current_step`:

| Progress | Step Label | What's Happening |
|----------|-----------|-----------------|
| 0.0 | `null` | Job created, waiting for pipeline start |
| 0.0 → 0.1 | "Identifying company from visitor signal" | Stage 0: IdentificationAgent running |
| 0.1 → 0.3 | "Enriching company profile" | Stage 1: parallel fan-out active |
| 0.3 → 0.5 | "Detecting technology stack" | Stage 2: parallel fan-out active |
| 0.5 → 0.8 | "Generating sales playbook" | Stage 3A: PlaybookAgent running |
| 0.8 → 1.0 | "Creating intelligence summary" | Stage 3B: SummaryAgent running |
| 1.0 | `null` | Pipeline complete, result stored |

The frontend polls `GET /jobs/{job_id}` every 2 seconds and displays this progression as a live progress bar.

### 2.3 Error Accumulation in Graph State

The `PipelineState.errors` field (type: `Annotated[list[str], operator.add]`) accumulates non-fatal errors from every node:

```python
# In any graph node:
try:
    result = await agent.run(input_data)
    return {"company_profile": result}
except Exception as e:
    logger.error(f"EnrichmentAgent failed: {e}", extra={"job_id": state["job_id"]})
    return {"errors": [f"EnrichmentAgent failed: {str(e)}"]}
```

These errors are:
- Merged into the final `AccountIntelligence.reasoning_trace`
- Available for debugging without stopping the pipeline
- Distinct from the `JobRecord.error` field (which only records fatal failures)

---

## 3. Failure Handling & Graceful Degradation

### 3.1 Degradation Hierarchy

The system follows a strict degradation hierarchy — each layer absorbs failures and passes partial results upward:

```
Level 0: Tool failure
  └─ Tool returns None
     └─ Agent continues with remaining tools

Level 1: Agent partial failure
  └─ Some tools returned None
     └─ Agent produces output with lower confidence_score
        └─ Error noted in reasoning_trace

Level 2: Agent total failure
  └─ LLM call fails after 3 retries
     └─ Agent returns degraded domain model (confidence_score=0.0)
        └─ Graph node catches exception, writes to state.errors

Level 3: Graph stage failure
  └─ One agent in parallel group throws unrecoverable exception
     └─ Graph catches at node level
        └─ State field set to None for that agent's output
           └─ Downstream agents work with partial state

Level 4: Pipeline failure (rare)
  └─ SummaryAgent cannot assemble any output
     └─ Controller marks job as FAILED
        └─ JobRecord.error populated with message
           └─ Frontend shows error UI with retry button
```

### 3.2 Partial Output Handling

When some agents succeed and others fail:

| Failed Agent | Impact on Output | `AccountIntelligence` State |
|-------------|-----------------|---------------------------|
| IdentificationAgent | Company unknown, enrichment uses "Unknown" | `company.company_name = "Unknown"` |
| EnrichmentAgent | No rich profile, only input name/domain | `company` has minimal fields, null industry/size |
| PersonaAgent | No persona insight | `persona = null` |
| IntentScorerAgent | No intent data | `intent = null` |
| TechStackAgent | No tech detection | `tech_stack = null` |
| SignalsAgent | No business signals | `business_signals = null` |
| LeadershipAgent | No leader discovery | `leadership = null` |
| PlaybookAgent | No sales recommendations | `playbook = null` |
| SummaryAgent | No narrative (assembly still happens) | `ai_summary = ""`, manual assembly |

**Critical invariant**: The pipeline ALWAYS produces an `AccountIntelligence` object. The only scenario where the job is marked FAILED is if the controller itself throws an exception or the graph cannot start at all.

---

## 4. Metrics Tracking

### 4.1 Request Metrics (API Layer)

| Metric | Type | Granularity |
|--------|------|------------|
| `api.requests.total` | Counter | Per endpoint, per method |
| `api.requests.duration_ms` | Histogram | Per endpoint |
| `api.requests.errors` | Counter | Per endpoint, per status code |
| `api.jobs.created` | Counter | Per analysis_type (visitor/company/batch) |

### 4.2 Pipeline Metrics (Graph Layer)

| Metric | Type | Granularity |
|--------|------|------------|
| `pipeline.executions.total` | Counter | Per flow type (visitor/company) |
| `pipeline.executions.duration_ms` | Histogram | Per flow type |
| `pipeline.executions.success` | Counter | Completed vs. failed |
| `pipeline.stage.duration_ms` | Histogram | Per stage (0, 1, 2, 3) |

### 4.3 Agent Metrics

| Metric | Type | Granularity |
|--------|------|------------|
| `agent.calls.total` | Counter | Per agent name |
| `agent.calls.duration_ms` | Histogram | Per agent name |
| `agent.calls.degraded` | Counter | Per agent name (confidence_score=0.0) |
| `agent.confidence_score` | Histogram | Per agent name |

### 4.4 Tool Metrics

| Metric | Type | Granularity |
|--------|------|------------|
| `tool.calls.total` | Counter | Per tool name |
| `tool.calls.duration_ms` | Histogram | Per tool name |
| `tool.calls.failures` | Counter | Per tool name, per error type |
| `tool.calls.retries` | Counter | Per tool name |
| `tool.calls.cache_hits` | Counter | Per tool name |

### 4.5 Hackathon Implementation

For the hackathon, these metrics are tracked via simple Python counters and logged at INFO level. No external metrics system is required.

```python
# In-memory metrics singleton (hackathon scope)
class Metrics:
    def __init__(self):
        self._counters: dict[str, int] = defaultdict(int)
        self._histograms: dict[str, list[float]] = defaultdict(list)

    def increment(self, name: str, labels: dict = {}) -> None: ...
    def observe(self, name: str, value: float, labels: dict = {}) -> None: ...
    def summary(self) -> dict: ...
```

Accessible via `GET /api/v1/health` (extended to include basic stats) or logged on shutdown.

---

## 5. Debugging Workflow

### 5.1 Tracing a Failed Request

When a user reports a problem or a job fails, follow this sequence:

```
Step 1: Get the job_id
  └─ From the frontend error display or API response

Step 2: Check job status
  └─ GET /api/v1/jobs/{job_id}
  └─ Look at: status, error, progress, current_step

Step 3: If FAILED — read the error field
  └─ error: "EnrichmentAgent failed: LLM timeout"
  └─ progress: 0.15 → failed during Stage 1

Step 4: If COMPLETED but wrong data — read the reasoning_trace
  └─ GET /api/v1/accounts/{result_id}
  └─ reasoning_trace shows exactly what each agent decided and why

Step 5: Check logs filtered by job_id
  └─ grep/filter for job_id in application logs
  └─ Every log entry from every layer includes job_id

Step 6: Identify the failing component
  └─ Which agent/tool had an error or unexpected result?
  └─ Check the tool logs for HTTP errors, timeouts, parse failures
  └─ Check the agent logs for LLM failures, degraded outputs
```

### 5.2 Identifying Which Agent Failed

The `reasoning_trace` and `progress` fields together pinpoint the failure:

| Progress When Failed | Stage | Likely Failing Agent |
|---------------------|-------|---------------------|
| 0.0–0.1 | Stage 0 | IdentificationAgent (IP lookup or web search) |
| 0.1–0.3 | Stage 1 | EnrichmentAgent (most likely — has 3 tool calls) |
| 0.3–0.5 | Stage 2 | TechStack/Signals/Leadership (check which is null) |
| 0.5–0.8 | Stage 3A | PlaybookAgent (LLM synthesis failure) |
| 0.8–1.0 | Stage 3B | SummaryAgent (LLM summary failure) |

### 5.3 Common Issues & Resolution

| Symptom | Root Cause | Resolution |
|---------|-----------|------------|
| Job stuck at PROCESSING, progress=0.0 | Graph never started | Check controller logs; likely asyncio.create_task failed |
| Job COMPLETED but company="Unknown" | IP resolved to cloud provider | Expected for VPN/cloud IPs; check `reasoning_trace` for details |
| Job COMPLETED but most sections null | Tools returned None (API keys invalid) | Verify `TAVILY_API_KEY`, `OPENAI_API_KEY` in `.env` |
| Job COMPLETED, low confidence (<0.3) | Limited data available for this company | Not a bug; small/private companies have less public data |
| Job FAILED with "LLM timeout" | OpenAI API slow or down | Retry; check OpenAI status page |
| Job FAILED with "Rate limited" | Too many concurrent requests | Built-in backoff should handle; check if keys are valid |
| Intent score is 0.0 for visitor analysis | IntentScorerAgent returned degraded | Check if `pages_visited` contained recognized page patterns |
| TechStack empty for known company | Scraper blocked by CDN/firewall | Some sites block automated scraping; expected for some domains |

### 5.4 Debug Logging Toggle

Set `LOG_LEVEL=DEBUG` in the backend `.env` to enable verbose logging:

```env
LOG_LEVEL=DEBUG    # Shows LLM prompts (truncated), tool request URLs, full state transitions
LOG_LEVEL=INFO     # Default — shows start/complete events with key metrics
LOG_LEVEL=WARNING  # Minimal — only issues and errors
```

---

## 6. Future Monitoring Integration (Post-Hackathon)

### 6.1 Dashboard Candidates

| Tool | Purpose | Integration Point |
|------|---------|------------------|
| **Grafana + Prometheus** | Metrics dashboards (latency, success rate, agent performance) | Export metrics via `/metrics` endpoint |
| **Langfuse / LangSmith** | LLM observability (prompt/response tracking, cost, latency) | Wrap LLM calls with tracing SDK |
| **Sentry** | Error tracking with stack traces | Add Sentry SDK to FastAPI |
| **Datadog / New Relic** | Full-stack APM | Add APM agent to FastAPI process |

### 6.2 Recommended Dashboard Panels

```
┌────────────────────────────────────────────────────────────────┐
│  Pipeline Overview                                              │
│                                                                 │
│  Total Analyses: 142    Success Rate: 94.4%    Avg Latency: 9.2s │
│                                                                 │
│  ┌─────────────┐  ┌─────────────┐  ┌─────────────────────────┐│
│  │ Jobs by     │  │ Avg Latency │  │ Confidence Distribution  ││
│  │ Status      │  │ by Stage    │  │                          ││
│  │ ████ 134 OK │  │ S0: 1.2s    │  │  ▁▂▃▅▇█▇▅▃▂            ││
│  │ ░░░░   8 Fail│  │ S1: 3.1s   │  │  0.0     0.5     1.0   ││
│  └─────────────┘  │ S2: 2.5s    │  └─────────────────────────┘│
│                    │ S3: 2.4s    │                              │
│  ┌─────────────┐  └─────────────┘  ┌─────────────────────────┐│
│  │ Agent       │                    │ Tool Health              ││
│  │ Degradation │                    │                          ││
│  │ Enrichment 2%│                   │ ip_lookup    ✅ 99.2%    ││
│  │ Intent    0%│                    │ web_search   ✅ 97.8%    ││
│  │ Persona   0%│                    │ scraper      ⚠️ 92.1%    ││
│  │ TechStack 5%│                    │ enrichment   ✅ 96.5%    ││
│  └─────────────┘                    └─────────────────────────┘│
└────────────────────────────────────────────────────────────────┘
```

### 6.3 Alerting Rules (Future)

| Alert | Condition | Severity |
|-------|-----------|----------|
| High failure rate | Job failure rate > 10% over 5 min | Critical |
| Slow pipeline | P95 latency > 25s over 10 min | Warning |
| Agent degradation spike | Any agent degraded rate > 20% over 10 min | Warning |
| Tool exhaustion | Any tool None rate > 50% over 5 min | Critical |
| LLM cost spike | Estimated token cost > $10/hour | Warning |
