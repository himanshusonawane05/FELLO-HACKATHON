# Agent Architecture — Fello AI Account Intelligence System

> **Version**: 1.0  
> **Date**: 2026-03-18  
> **Depends on**: [HLD](./hld.md), [LLD](./lld.md), [API Contracts](./api-contracts.md)

This document defines two categories of agents:

1. **System Agents** — AI agents that run inside the backend pipeline (LangGraph nodes)
2. **Development Agents** — Cursor agent personas for building the system in parallel

---

## PART 1: SYSTEM AGENTS (LangGraph Pipeline)

---

### 1.1 IdentificationAgent

**Purpose:** Resolve anonymous visitor signals into a concrete company identity.

| Property | Value |
|----------|-------|
| **Class** | `IdentificationAgent` |
| **File** | `backend/agents/identification.py` |
| **Input** | `VisitorSignal` |
| **Output** | `CompanyInput` |
| **Tools** | `ip_lookup`, `web_search` |
| **LLM Task** | Disambiguate when IP lookup returns ambiguous results |
| **Max iterations** | 3 |

**Logic:**
1. Call `ip_lookup` with visitor IP
2. If `is_cloud_provider` is true → use `web_search` with any available referral/domain hints
3. If IP resolves to a company → return `CompanyInput(company_name=..., domain=...)`
4. If ambiguous → ask LLM to pick best match from web search results
5. On failure → return `CompanyInput(company_name="Unknown", domain=None)` with `confidence_score=0.0`

**Boundary Rules:**
- MUST NOT access HTTP layer
- MUST NOT score intent or infer persona
- MUST NOT persist results — only returns domain model

---

### 1.2 EnrichmentAgent

**Purpose:** Build a comprehensive company profile from multiple data sources.

| Property | Value |
|----------|-------|
| **Class** | `EnrichmentAgent` |
| **File** | `backend/agents/enrichment.py` |
| **Input** | `CompanyInput` |
| **Output** | `CompanyProfile` |
| **Tools** | `enrichment_apis`, `web_search`, `scraper` |
| **LLM Task** | Merge and normalize conflicting data from multiple sources |
| **Max iterations** | 3 |

**Logic:**
1. Call `enrichment_apis` (Clearbit → Apollo → LLM fallback)
2. Call `web_search` for company + "about company size headquarters"
3. Call `scraper` on company domain (if known)
4. LLM merges all sources, resolves conflicts, normalizes fields
5. Returns `CompanyProfile` with `data_sources` listing which APIs contributed

**Boundary Rules:**
- MUST NOT score intent or infer persona
- MUST NOT generate sales recommendations
- MUST populate `data_sources` field accurately

---

### 1.3 PersonaAgent

**Purpose:** Infer the likely role and seniority of the website visitor from behavioral patterns.

| Property | Value |
|----------|-------|
| **Class** | `PersonaAgent` |
| **File** | `backend/agents/persona.py` |
| **Input** | `VisitorSignal` (from graph state) |
| **Output** | `PersonaInference` |
| **Tools** | None |
| **LLM Task** | Map page visit patterns to likely buyer personas |
| **Max iterations** | 1 |

**Logic:**
1. Extract behavioral signals from `pages_visited`, `time_on_site_seconds`, `visit_count`
2. LLM maps page patterns to persona:
   - `/pricing` → buyer/decision-maker
   - `/docs`, `/api` → technical evaluator
   - `/blog`, `/resources` → researcher/early-stage
   - `/case-studies` → late-stage evaluator
3. Returns `PersonaInference` with `behavioral_signals` list

**Boundary Rules:**
- MUST NOT call any tools — pure LLM reasoning
- MUST NOT access company data (that's EnrichmentAgent's job)
- If no visitor signal provided (company-only flow), return degraded result

---

### 1.4 IntentScorerAgent

**Purpose:** Score the buying intent of the visitor on a 0–10 scale.

| Property | Value |
|----------|-------|
| **Class** | `IntentScorerAgent` |
| **File** | `backend/agents/intent_scorer.py` |
| **Input** | `VisitorSignal` (from graph state) |
| **Output** | `IntentScore` |
| **Tools** | None |
| **LLM Task** | Score intent based on weighted behavioral signals |
| **Max iterations** | 1 |

**Scoring Framework (provided to LLM as system context):**

| Signal | Weight |
|--------|--------|
| Pricing page visit | +3.0 |
| Product/feature page | +2.5 |
| Case study / testimonial | +2.0 |
| Documentation / API page | +1.5 |
| Blog / resource page | +0.5 |
| Repeat visits (this week) | +0.3 per visit (max +1.5) |
| Time on site > 2 min | +0.5 |
| Time on site > 5 min | +1.0 |
| Referral from search engine | +0.5 |

**Stage Mapping:**
- 0.0–2.5 → AWARENESS
- 2.5–5.0 → CONSIDERATION
- 5.0–7.5 → EVALUATION
- 7.5–10.0 → PURCHASE

**Boundary Rules:**
- MUST NOT call any tools
- MUST NOT infer persona or enrich company
- MUST populate `page_score_breakdown` with per-page scores
- If no visitor signal, return `IntentScore(intent_score=0.0, intent_stage=AWARENESS)`

---

### 1.5 TechStackAgent

**Purpose:** Detect technologies used by the target company.

| Property | Value |
|----------|-------|
| **Class** | `TechStackAgent` |
| **File** | `backend/agents/tech_stack.py` |
| **Input** | `CompanyProfile` (from graph state, needs `domain`) |
| **Output** | `TechStack` |
| **Tools** | `scraper` |
| **LLM Task** | Map script sources and page content to known technologies |
| **Max iterations** | 2 |

**Logic:**
1. If `domain` is available, call `scraper` on the domain
2. Extract `script_sources` from scraper result
3. LLM maps script URLs to known technologies:
   - `salesforce.com` scripts → Salesforce CRM
   - `hs-scripts.com`, `hubspot.com` → HubSpot
   - `google-analytics.com`, `gtag` → Google Analytics
   - `wp-content`, `wp-includes` → WordPress
   - etc.
4. Returns `TechStack` with categorized technologies

**Boundary Rules:**
- MUST NOT make up technologies — only report what evidence supports
- If domain is null, return empty TechStack with `confidence_score=0.0`
- MUST categorize each technology into a `TechCategory`

---

### 1.6 SignalsAgent

**Purpose:** Discover business signals indicating growth or opportunity.

| Property | Value |
|----------|-------|
| **Class** | `SignalsAgent` |
| **File** | `backend/agents/signals.py` |
| **Input** | `CompanyProfile` (from graph state) |
| **Output** | `BusinessSignals` |
| **Tools** | `web_search` |
| **LLM Task** | Classify search results into business signal categories |
| **Max iterations** | 2 |

**Logic:**
1. Search: `"{company_name}" hiring OR funding OR expansion OR launch`
2. LLM filters results for genuine business signals
3. Classifies each into `SignalType` enum
4. Returns `BusinessSignals` with source URLs

**Boundary Rules:**
- MUST include `source_url` for every signal
- MUST NOT fabricate signals without search evidence
- If no signals found, return empty list (not an error)

---

### 1.7 LeadershipAgent

**Purpose:** Discover key decision makers at the target company.

| Property | Value |
|----------|-------|
| **Class** | `LeadershipAgent` |
| **File** | `backend/agents/leadership.py` |
| **Input** | `CompanyProfile` (from graph state) |
| **Output** | `LeadershipProfile` |
| **Tools** | `web_search` |
| **LLM Task** | Extract leadership names/titles from search results |
| **Max iterations** | 2 |

**Logic:**
1. Search: `"{company_name}" CEO OR "VP Sales" OR "Head of" site:linkedin.com`
2. Search: `"{company_name}" leadership team about`
3. LLM extracts names, titles, and LinkedIn URLs from results
4. Returns `LeadershipProfile` with source URLs

**Boundary Rules:**
- MUST include `source_url` for every leader discovered
- MUST NOT fabricate leader names
- Prefer C-level, VP, and Director-level contacts

---

### 1.8 PlaybookAgent

**Purpose:** Synthesize all intelligence into actionable sales recommendations.

| Property | Value |
|----------|-------|
| **Class** | `PlaybookAgent` |
| **File** | `backend/agents/playbook.py` |
| **Input** | All prior outputs from graph state |
| **Output** | `SalesPlaybook` |
| **Tools** | None |
| **LLM Task** | Generate prioritized sales actions based on complete intelligence |
| **Max iterations** | 1 |

**Priority Logic:**
- Intent >= 7.0 AND business signals present → HIGH
- Intent >= 4.0 OR business signals present → MEDIUM
- Otherwise → LOW

**Boundary Rules:**
- MUST NOT call any tools
- MUST reference specific data points in `rationale` fields
- MUST generate at least 1 recommended action
- If insufficient data, return LOW priority with generic recommendations

---

### 1.9 SummaryAgent

**Purpose:** Generate a concise AI narrative and assemble the final `AccountIntelligence` aggregate.

| Property | Value |
|----------|-------|
| **Class** | `SummaryAgent` |
| **File** | `backend/agents/summary.py` |
| **Input** | All prior outputs from graph state |
| **Output** | `AccountIntelligence` |
| **Tools** | None |
| **LLM Task** | Write a 3–5 sentence executive briefing and compute aggregate confidence |
| **Max iterations** | 1 |

**Logic:**
1. LLM generates `ai_summary` from all available intelligence
2. Computes aggregate `confidence_score` as weighted average of sub-scores
3. Merges all `reasoning_trace` entries from sub-agents
4. Assembles and returns `AccountIntelligence` aggregate root

**Boundary Rules:**
- MUST NOT call any tools
- MUST assemble ALL available sub-results into `AccountIntelligence`
- Summary should be actionable, not just descriptive
- Missing sub-results should be omitted (null), not fabricated

---

## PART 2: DEVELOPMENT AGENTS (Cursor Workflow)

These are personas/instructions for humans or AI agents working in Cursor to build the system in parallel.

---

### 2.1 System Architect (this agent)

**Responsibilities:**
- Design system architecture before implementation
- Define API contracts and data models
- Create and maintain documentation in `docs/`
- Define .cursor/rules and agent coordination strategy

**Scope Boundaries:**
- DO: Architecture docs, API contracts, data model design, rules
- DON'T: Write implementation code, UI components, business logic

**When to invoke:** At project start and when architecture changes are needed.

---

### 2.2 Backend Engineer

**Responsibilities:**
- Implement all Python code: domain models, agents, tools, graph, controllers, API routes
- Follow all .cursor/rules strictly (01 through 06 + new rules)
- Ensure all domain models match `docs/lld.md` schemas exactly
- Ensure all API routes match `docs/api-contracts.md` exactly
- Implement tool integrations with proper error handling

**Scope Boundaries:**
- DO: `backend/` directory only
- DON'T: Touch `frontend/`, create documentation, modify `.cursor/rules`
- DON'T: Hardcode API keys, skip type hints, return raw dicts from agents

**Input:** Architecture docs (hld.md, lld.md, api-contracts.md)
**Output:** Working backend with all endpoints functional

**Implementation Order:**
1. `backend/config.py` + `backend/main.py` (skeleton)
2. `backend/domain/` (all models — this unblocks everything)
3. `backend/tools/` (external integrations)
4. `backend/agents/` (LLM logic)
5. `backend/graph/` (LangGraph workflow)
6. `backend/storage/` (in-memory stores)
7. `backend/controllers/` (orchestration)
8. `backend/api/` (routes + schemas)

**MCP Tools Available:** filesystem, git, memory, fetch, browser

---

### 2.3 Frontend Engineer

**Responsibilities:**
- Implement Next.js frontend following `docs/api-contracts.md`
- Build all components defined in `.cursor/rules/05-frontend.mdc`
- Use TypeScript interfaces from `docs/api-contracts.md` Section 4
- Implement polling logic per `docs/api-contracts.md` Section 3

**Scope Boundaries:**
- DO: `frontend/` directory only
- DON'T: Touch `backend/`, implement business logic, call APIs directly (use `lib/api.ts`)
- DON'T: Use `any` types, hardcode API URLs, skip loading/error states

**Input:** API contracts (api-contracts.md Section 4 for types, Section 2 for endpoints)
**Output:** Working frontend that can connect to backend via API

**Implementation Order:**
1. `frontend/` scaffold (Next.js + Tailwind + shadcn/ui)
2. `frontend/types/intelligence.ts` (copy from api-contracts.md)
3. `frontend/lib/api.ts` (API client with all endpoints)
4. `frontend/hooks/` (useJobPoller, useAccountAnalysis)
5. `frontend/components/` (all UI components)
6. `frontend/app/` (pages wiring components together)

**Can build independently** using mock data that conforms to `AccountIntelligence` interface.

**MCP Tools Available:** filesystem, git, memory, browser

---

### 2.4 QA Engineer

**Responsibilities:**
- Write tests for domain models, agents, tools, API routes
- Validate API responses match contracts exactly
- Test error handling paths (tool failures, LLM failures)
- Test frontend components render all states (loading, data, error)

**Scope Boundaries:**
- DO: `tests/` directory, test scripts
- DON'T: Modify source code (report issues instead)
- DON'T: Skip edge cases (null fields, degraded outputs)

**Validation Checklist:**
- [ ] Every domain model instantiates correctly with example data from LLD
- [ ] Every API endpoint returns schema matching api-contracts.md
- [ ] Every agent returns degraded output on LLM failure
- [ ] Every tool returns None on external API failure
- [ ] Frontend renders correctly with complete, partial, and null data
- [ ] Job polling works: PENDING → PROCESSING → COMPLETED flow
- [ ] Job polling works: PENDING → PROCESSING → FAILED flow

**MCP Tools Available:** filesystem, git, browser

---

### 2.5 Integration Engineer

**Responsibilities:**
- Connect frontend to backend
- Verify end-to-end flow works
- Configure CORS, environment variables, deployment
- Create demo data and test scenarios

**Scope Boundaries:**
- DO: `.env` files, docker configs, integration tests, demo scripts
- DON'T: Refactor architecture, change API contracts unilaterally

**Integration Checklist:**
- [ ] Frontend can submit visitor analysis and see results
- [ ] Frontend can submit company analysis and see results
- [ ] Frontend can submit batch analysis and see results
- [ ] Polling works correctly with progress updates
- [ ] Error states display properly
- [ ] CORS configured correctly
- [ ] Environment variables documented in README

**MCP Tools Available:** filesystem, git, memory, fetch, browser

---

## PART 3: AGENT EXECUTION GRAPH (LangGraph)

### 3.1 Node-to-Agent Mapping

| Node Name | Agent | Graph State Read | Graph State Write |
|-----------|-------|-----------------|-------------------|
| `route_input` | (conditional) | `visitor_signal`, `company_input` | — |
| `identification_node` | IdentificationAgent | `visitor_signal` | `identified_company` |
| `enrichment_node` | EnrichmentAgent | `identified_company` or `company_input` | `company_profile` |
| `intent_node` | IntentScorerAgent | `visitor_signal` | `intent` |
| `persona_node` | PersonaAgent | `visitor_signal` | `persona` |
| `tech_stack_node` | TechStackAgent | `company_profile` | `tech_stack` |
| `signals_node` | SignalsAgent | `company_profile` | `business_signals` |
| `leadership_node` | LeadershipAgent | `company_profile` | `leadership` |
| `playbook_node` | PlaybookAgent | all prior state | `playbook` |
| `summary_node` | SummaryAgent | all prior state | `intelligence` |

### 3.2 Parallel Execution Groups

**Stage 1 (after identification):**
- `enrichment_node` + `intent_node` + `persona_node` → execute via `Send()` concurrently

**Stage 2 (after enrichment complete):**
- `tech_stack_node` + `signals_node` + `leadership_node` → execute via `Send()` concurrently

**Stage 3 (sequential):**
- `playbook_node` → `summary_node` → END

### 3.3 Progress Tracking

Each node updates the job progress when it starts/completes:

| Node | Progress Range | Step Label |
|------|---------------|------------|
| `identification_node` | 0.0 → 0.1 | "Identifying company from visitor signal" |
| `enrichment_node` | 0.1 → 0.3 | "Enriching company profile" |
| `intent_node` | 0.1 → 0.3 | "Scoring buying intent" |
| `persona_node` | 0.1 → 0.3 | "Inferring visitor persona" |
| `tech_stack_node` | 0.3 → 0.5 | "Detecting technology stack" |
| `signals_node` | 0.3 → 0.5 | "Discovering business signals" |
| `leadership_node` | 0.3 → 0.5 | "Finding decision makers" |
| `playbook_node` | 0.5 → 0.8 | "Generating sales playbook" |
| `summary_node` | 0.8 → 1.0 | "Creating intelligence summary" |
