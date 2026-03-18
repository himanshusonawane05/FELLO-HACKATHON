# Data Pipeline — End-to-End Flow

> **Version**: 1.1  
> **Date**: 2026-03-18  
> **Depends on**: [Agent Architecture](./agent-architecture.md), [LLD](./lld.md), [API Contracts](./api-contracts.md)

> **Implementation Notes (added v1.1):**
> - Pipeline is fully implemented and verified end-to-end
> - See [Implementation Status](./implementation-status.md) for the complete deviation list
> - Key deviations from this document's original design are marked **[ACTUAL]** inline

This document traces the complete path of data through the system — from raw input to structured `AccountIntelligence` output — stage by stage.

---

## 1. Pipeline Overview

```
INPUT                   STAGE 0          STAGE 1 (parallel)              STAGE 2 (parallel)           STAGE 3 (sequential)         OUTPUT
─────                   ───────          ──────────────────              ──────────────────           ────────────────────         ──────

VisitorSignal ──▶ Identification ──┐
                                   ├──▶ ┌─ Enrichment ──────┐     ┌─ TechStack ─────────┐
CompanyInput ──────────────────────┘    │                    ├──▶  │                      ├──▶ Playbook ──▶ Summary ──▶ AccountIntelligence
                                        ├─ IntentScorer ─────┤     ├─ Signals ────────────┤
                                        │                    │     │                      │
                                        └─ Persona ──────────┘     └─ Leadership ─────────┘
```

**Key invariant**: Every path through the pipeline produces an `AccountIntelligence` object. Failures result in degraded output (null sub-fields, `confidence_score=0.0`), never in a missing result.

---

## 2. Stage-by-Stage Breakdown

### Stage 0: Input Routing & Identification

**Triggers only for visitor signal input.** Company input skips directly to Stage 1.

| Property | Value |
|----------|-------|
| **Node** | `route_input` → `identification_node` |
| **Agent** | `IdentificationAgent` |
| **Input** | `VisitorSignal` (from API request) |
| **Output** | `CompanyInput` (written to `state.identified_company`) |
| **Tools** | `ip_lookup` (primary), `web_search` (secondary) |
| **Progress** | 0.05 → 0.15 |

**Data transformation:**

```
VisitorSignal.ip_address
    │
    ├─ private/reserved IP? (10.x, 192.168.x, 127.x, etc.)
    │   └─ YES → CompanyInput(company_name="Unknown (Private IP)")
    │
    ▼ IPLookupTool (ipapi.co → ip-api.com fallback)
    │
    ├─ cloud/ISP provider detected? (Google, Cloudflare, AWS, etc.)
    │   └─ YES → CompanyInput(company_name="Unknown")
    │
    ├─ company resolved?
    │   └─ YES → CompanyInput(company_name=resolved, domain=None)
    │
    └─ total failure?
        └─ CompanyInput(company_name="Unknown")
```

> **[ACTUAL]** The original design called for LLM disambiguation when IP resolves to a cloud provider. In practice, the agent returns "Unknown" directly — Tavily search is called but results are not used for company inference (to avoid fabrication). No LLM is used in this agent.

**Failure handling:**
- Private/reserved IP → `CompanyInput(company_name="Unknown (Private IP)")` immediately
- Cloud provider detected → `CompanyInput(company_name="Unknown")`
- `ip_lookup` returns None → Tavily called, result discarded, returns "Unknown"
- Error recorded in `state.errors` and `state.reasoning_trace`

---

### Stage 1: Parallel Fan-Out (Enrichment + Intent + Persona)

Three agents execute **concurrently** via LangGraph `Send()`. They share no mutable state.

#### 1A: EnrichmentAgent

| Property | Value |
|----------|-------|
| **Node** | `enrichment_node` (inside `stage1_node` via `asyncio.gather`) |
| **Input** | `CompanyInput` (from `state.identified_company` or `state.company_input`) |
| **Output** | `CompanyProfile` (written to `state.company_profile`) |
| **Tools** | `web_search` (Tavily) |
| **Progress** | 0.20 → 0.50 (shared with persona and intent) |

> **[ACTUAL]** `enrichment_apis` (Clearbit/Apollo) and `scraper` are **not used**. Enrichment uses Tavily web search + LLM synthesis only.

**Data transformation:**

```
CompanyInput.company_name + CompanyInput.domain
    │
    ├─ Unknown company? (name is "Unknown" or "Unknown (Private IP)")
    │   └─ YES → CompanyProfile(confidence_score=0.1, all fields null)
    │
    ▼ WebSearchTool (Tavily): "{company_name} company overview industry employees revenue"
    │     └─ [{title, url, snippet}]  (max 5 results)
    │
    ▼ LLM (Gemini) synthesizes profile from search results
    │   (or from general knowledge if Tavily returns nothing)
    │
    CompanyProfile(
        company_name, domain, industry, company_size_estimate,
        headquarters, founding_year, description, annual_revenue_range,
        confidence_score, data_sources=["tavily_search", "llm_synthesis"]
    )
```

**Failure handling:**
- Unknown company → returns minimal profile with `confidence_score=0.1` immediately
- Tavily returns None → LLM uses general knowledge, `confidence_score` reflects uncertainty
- LLM failure → `CompanyProfile(company_name=input.company_name, confidence_score=0.3)`

#### 1B: IntentScorerAgent

| Property | Value |
|----------|-------|
| **Node** | `intent_node` (inside `stage1_node` via `asyncio.gather`) |
| **Input** | `VisitorSignal` (from `state.visitor_signal`) |
| **Output** | `IntentScore` (written to `state.intent`) |
| **Tools** | None |
| **LLM** | None — pure rule-based scoring |
| **Progress** | 0.20 → 0.50 (shared with enrichment and persona) |

> **[ACTUAL]** IntentScorerAgent uses **no LLM**. It applies a deterministic weighted scoring formula in Python. This is faster and more predictable than LLM scoring.

**Data transformation:**

```
VisitorSignal.pages_visited + time_on_site_seconds + visit_count + referral_source
    │
    ▼ LLM applies scoring framework
    │
    ├─ /pricing           → +3.0
    ├─ /ai-sales-agent    → +2.5 (product page)
    ├─ /case-studies       → +2.0
    ├─ repeat visits (3)   → +0.9 (0.3 × 3, capped at 1.5)
    ├─ time > 2min (222s)  → +0.5
    │
    ▼ Sum = 8.9, capped at 10.0 → intent_score = 8.9
    │
    ▼ Stage mapping: 8.9 ≥ 7.5 → PURCHASE
    │
    IntentScore(
        intent_score=8.9,
        intent_stage=PURCHASE,
        signals_detected=["Pricing page visit", "3 visits this week", ...],
        page_score_breakdown={"/pricing": 3.0, "/ai-sales-agent": 2.5, ...},
        confidence_score=0.88
    )
```

**Failure handling:**
- No visitor signal (company-only flow) → `IntentScore(intent_score=0.0, intent_stage=AWARENESS, confidence_score=0.0)`
- LLM failure → same degraded output

#### 1C: PersonaAgent

| Property | Value |
|----------|-------|
| **Node** | `persona_node` |
| **Input** | `VisitorSignal` (from `state.visitor_signal`) |
| **Output** | `PersonaInference` (written to `state.persona`) |
| **Tools** | None (pure LLM reasoning) |
| **Progress** | 0.1 → 0.3 |

**Data transformation:**

```
VisitorSignal.pages_visited + time_on_site_seconds + visit_count
    │
    ▼ LLM maps behavioral patterns to persona
    │
    ├─ /pricing + /case-studies → buyer / decision-maker pattern
    ├─ /ai-sales-agent         → evaluating sales automation
    ├─ 3 visits, 3m42s         → deep engagement, not casual
    │
    ▼ Inferred: sales operations leadership evaluating tools
    │
    PersonaInference(
        likely_role="Head of Sales Operations",
        department="Sales",
        seniority_level=DIRECTOR,
        behavioral_signals=["Pricing page visit", "Product evaluation", ...],
        confidence_score=0.72
    )
```

**Failure handling:**
- No visitor signal → `PersonaInference(likely_role="Unknown", seniority_level=UNKNOWN, confidence_score=0.0)`
- LLM failure → same degraded output

---

### Stage 2: Parallel Fan-Out (TechStack + Signals + Leadership)

Three agents execute **concurrently** via `asyncio.gather` inside `stage2_node`. All depend on `state.company_profile` from Stage 1A.

> **[ACTUAL]** Parallelism uses `asyncio.gather` inside a single LangGraph node, not LangGraph `Send()`. Functionally equivalent.

**Barrier:** Stage 2 waits for Stage 1 to complete — specifically, it needs `company_profile` to be populated. The `intent` and `persona` results are not required for Stage 2.

#### 2A: TechStackAgent

> **[ACTUAL]** `ScraperTool` is **not used**. Uses LLM general knowledge to infer tech stack. Returns empty stack for Unknown/low-confidence companies.

| Property | Value |
|----------|-------|
| **Node** | `tech_stack_node` (inside `stage2_node`) |
| **Input** | `CompanyProfile` (from `state.company_profile`) |
| **Output** | `TechStack` (written to `state.tech_stack`) |
| **Tools** | None |
| **LLM** | Gemini |
| **Progress** | 0.55 → 0.80 (shared) |

**Data transformation:**

```
CompanyProfile.domain
    │
    ├─ domain is None?
    │   └─ YES → TechStack(technologies=[], confidence_score=0.0)
    │
    └─ domain exists?
        │
        ▼ scraper(domain)
        │
        └─ script_sources: [
             "cdn.salesforce.com/...",
             "js.hs-scripts.com/...",
             "www.google-analytics.com/analytics.js",
             "wp-includes/js/..."
           ]
        │
        ▼ LLM maps script URLs → Technology objects
        │
        TechStack(
            technologies=[
                Technology(name="Salesforce", category=CRM, confidence_score=0.9),
                Technology(name="HubSpot", category=MARKETING_AUTOMATION, confidence_score=0.85),
                Technology(name="Google Analytics", category=ANALYTICS, confidence_score=0.92),
                Technology(name="WordPress", category=WEBSITE_PLATFORM, confidence_score=0.95)
            ],
            detection_method="script_analysis",
            confidence_score=0.9
        )
```

**Failure handling:**
- Domain is null → empty TechStack with `confidence_score=0.0`
- Scraper returns None → empty TechStack
- LLM failure → empty TechStack with `confidence_score=0.0`

#### 2B: SignalsAgent

> **[ACTUAL]** Uses Tavily web search for real news + LLM extraction. Returns empty signals for Unknown/low-confidence companies.

| Property | Value |
|----------|-------|
| **Node** | `signals_node` (inside `stage2_node`) |
| **Input** | `CompanyProfile` (from `state.company_profile`) |
| **Output** | `BusinessSignals` (written to `state.business_signals`) |
| **Tools** | `WebSearchTool` (Tavily) |
| **LLM** | Gemini |
| **Progress** | 0.55 → 0.80 (shared) |

**Data transformation:**

```
CompanyProfile.company_name
    │
    ▼ web_search: '"{company_name}" hiring OR funding OR expansion OR launch'
    │
    └─ results: [
         {title: "Acme Mortgage hiring 3 SDRs", url: "linkedin.com/..."},
         {title: "Acme expands to Florida market", url: "businesswire.com/..."}
       ]
    │
    ▼ LLM classifies each result into SignalType
    │
    BusinessSignals(
        signals=[
            Signal(signal_type=HIRING, title="Hiring SDRs", description="...", source_url="..."),
            Signal(signal_type=EXPANSION, title="Florida expansion", description="...", source_url="...")
        ],
        confidence_score=0.7
    )
```

**Failure handling:**
- Web search returns None → `BusinessSignals(signals=[], confidence_score=0.0)`
- No relevant results found → empty signals list (not an error)

#### 2C: LeadershipAgent

> **[ACTUAL]** Uses Tavily web search for leadership data + LLM extraction. Returns empty leadership for Unknown/low-confidence companies.

| Property | Value |
|----------|-------|
| **Node** | `leadership_node` (inside `stage2_node`) |
| **Input** | `CompanyProfile` (from `state.company_profile`) |
| **Output** | `LeadershipProfile` (written to `state.leadership`) |
| **Tools** | `WebSearchTool` (Tavily) |
| **LLM** | Gemini |
| **Progress** | 0.55 → 0.80 (shared) |

**Data transformation:**

```
CompanyProfile.company_name
    │
    ├─▶ web_search: '"{company_name}" CEO OR "VP Sales" site:linkedin.com'
    └─▶ web_search: '"{company_name}" leadership team about'
    │
    ▼ LLM extracts names, titles, LinkedIn URLs from search results
    │
    LeadershipProfile(
        leaders=[
            Leader(name="Jane Smith", title="VP of Sales", department="Sales",
                   linkedin_url="https://linkedin.com/in/janesmith", source_url="..."),
            Leader(name="Bob Johnson", title="CEO", department="Executive",
                   linkedin_url="https://linkedin.com/in/bobjohnson", source_url="...")
        ],
        confidence_score=0.75
    )
```

**Failure handling:**
- Web search returns None → `LeadershipProfile(leaders=[], confidence_score=0.0)`
- LLM fabricates names → caught by requiring `source_url` for every leader

---

### Stage 3: Sequential Synthesis

#### 3A: PlaybookAgent

| Property | Value |
|----------|-------|
| **Node** | `playbook_node` |
| **Input** | All prior state: `company_profile`, `persona`, `intent`, `tech_stack`, `business_signals`, `leadership` |
| **Output** | `SalesPlaybook` (written to `state.playbook`) |
| **Tools** | None (pure LLM reasoning) |
| **Progress** | 0.5 → 0.8 |

**Data transformation:**

```
ALL prior outputs (company + persona + intent + tech + signals + leadership)
    │
    ▼ LLM synthesizes actionable sales strategy
    │
    ├─ Priority determination:
    │   intent_score=8.9 ≥ 7.0 AND business_signals present → HIGH
    │
    ├─ Recommended actions:
    │   leadership data → "Research VP Sales Jane Smith on LinkedIn"
    │   signals data   → "Reference Florida expansion as growth trigger"
    │   intent data    → "Send outreach referencing case studies they viewed"
    │
    ├─ Talking points:
    │   Drawn from specific intelligence across all sub-results
    │
    └─ Outreach template:
        Personalized email referencing discovered intelligence
    │
    SalesPlaybook(
        priority=HIGH,
        recommended_actions=[...],
        talking_points=[...],
        outreach_template="Hi Jane, I noticed Acme Mortgage is expanding...",
        confidence_score=0.82
    )
```

**Failure handling:**
- Insufficient data → `SalesPlaybook(priority=LOW, recommended_actions=[generic action], confidence_score=0.0)`
- LLM failure → same degraded output

#### 3B: SummaryAgent

| Property | Value |
|----------|-------|
| **Node** | `summary_node` |
| **Input** | All prior state including `playbook` |
| **Output** | `AccountIntelligence` (written to `state.intelligence`) |
| **Tools** | None (pure LLM reasoning) |
| **Progress** | 0.8 → 1.0 |

**Data transformation:**

```
ALL state (company + persona + intent + tech + signals + leadership + playbook)
    │
    ▼ LLM writes 3–5 sentence executive briefing
    │
    ├─ Aggregate confidence = weighted average of sub-scores
    │   weights: company(0.25) + intent(0.2) + persona(0.15)
    │          + tech(0.1) + signals(0.1) + leadership(0.1) + playbook(0.1)
    │
    ├─ Merge all reasoning_trace entries from all sub-agents
    │
    └─ Assemble final AccountIntelligence aggregate root
    │
    AccountIntelligence(
        company=state.company_profile,
        persona=state.persona,          # nullable
        intent=state.intent,            # nullable
        tech_stack=state.tech_stack,     # nullable
        business_signals=state.business_signals,  # nullable
        leadership=state.leadership,    # nullable
        playbook=state.playbook,        # nullable
        ai_summary="Acme Mortgage is a mid-sized lender...",
        confidence_score=0.82,
        reasoning_trace=[...all merged traces...]
    )
```

**Failure handling:**
- LLM failure → assemble AccountIntelligence with `ai_summary=""` and `confidence_score=0.0`
- Missing sub-results → set to `None` (never fabricated)

---

## 3. Parallel Execution Diagram

```
Time ──────────────────────────────────────────────────────────────────▶

     │ Stage 0 │         Stage 1              │         Stage 2              │  Stage 3      │
     │         │                              │                              │               │
     │ Ident.  │  ┌─ Enrichment ──────────┐   │  ┌─ TechStack ──────────┐   │               │
     │  Agent  │  │  (3 tool calls + LLM) │   │  │  (scraper + LLM)     │   │               │
     │         │  └────────────────────────┘   │  └──────────────────────┘   │               │
     │ 0.0-0.1 │                              │                              │  Playbook     │
     │         │  ┌─ IntentScorer ─────────┐  │  ┌─ Signals ────────────┐   │  0.5-0.8      │
     │         │  │  (LLM only, fast)      │  │  │  (web_search + LLM)  │   │       │       │
     │         │  └────────────────────────┘  │  └──────────────────────┘   │       ▼       │
     │         │                              │                              │  Summary      │
     │         │  ┌─ Persona ──────────────┐  │  ┌─ Leadership ─────────┐   │  0.8-1.0      │
     │         │  │  (LLM only, fast)      │  │  │  (web_search + LLM)  │   │               │
     │         │  └────────────────────────┘  │  └──────────────────────┘   │               │
     │         │          0.1 - 0.3           │          0.3 - 0.5          │               │

     ▲                    ▲                            ▲                           ▲
     │                    │                            │                           │
  BARRIER             BARRIER                      BARRIER                     BARRIER
  (route)         (all Stage 1 done)          (all Stage 2 done)           (playbook done)
```

---

## 4. Data Shape Transformations Summary

| Stage | Input Shape | Output Shape | Key Transformation |
|-------|------------|-------------|-------------------|
| 0 | `VisitorSignal` | `CompanyInput` | IP address → company identity |
| 1A | `CompanyInput` | `CompanyProfile` | Name → full enriched profile (multi-source) |
| 1B | `VisitorSignal` | `IntentScore` | Page visits → buying intent score (0–10) |
| 1C | `VisitorSignal` | `PersonaInference` | Page visits → likely buyer persona |
| 2A | `CompanyProfile` | `TechStack` | Domain scripts → detected technologies |
| 2B | `CompanyProfile` | `BusinessSignals` | Company name → growth/opportunity signals |
| 2C | `CompanyProfile` | `LeadershipProfile` | Company name → key decision makers |
| 3A | All prior | `SalesPlaybook` | All intelligence → prioritized sales actions |
| 3B | All prior | `AccountIntelligence` | All data → final aggregate + AI summary |

---

## 5. Example Pipeline Execution — Visitor Signal

### Input

```json
{
  "visitor_id": "v-001",
  "ip_address": "34.201.114.42",
  "pages_visited": ["/pricing", "/ai-sales-agent", "/case-studies"],
  "time_on_site_seconds": 222,
  "visit_count": 3,
  "referral_source": "google"
}
```

### Execution Trace

```
[T+0.0s] route_input: visitor_signal present → route to identification_node
[T+0.0s] Job progress: 0.0, step: "Identifying company from visitor signal"

[T+0.5s] identification_node: ip_lookup(34.201.114.42)
         → {company_name: "Acme Mortgage", domain: "acmemortgage.com", confidence: 0.8}
         → CompanyInput(company_name="Acme Mortgage", domain="acmemortgage.com")
[T+1.2s] Job progress: 0.1, step: "Enriching company profile"

[T+1.2s] PARALLEL START — Stage 1:
         ├─ enrichment_node: enrichment_apis("Acme Mortgage") + web_search + scraper
         ├─ intent_node: LLM scoring visitor pages
         └─ persona_node: LLM inferring persona from pages

[T+2.0s] intent_node COMPLETE: IntentScore(score=8.9, stage=PURCHASE)
[T+2.3s] persona_node COMPLETE: PersonaInference(role="Head of Sales Ops", confidence=0.72)
[T+4.5s] enrichment_node COMPLETE: CompanyProfile(industry="Mortgage Lending", size="200-500")
[T+4.5s] Job progress: 0.3, step: "Detecting technology stack"

[T+4.5s] PARALLEL START — Stage 2:
         ├─ tech_stack_node: scraper(acmemortgage.com) → script analysis
         ├─ signals_node: web_search("Acme Mortgage" hiring OR funding)
         └─ leadership_node: web_search("Acme Mortgage" CEO OR VP Sales)

[T+6.0s] tech_stack_node COMPLETE: TechStack(4 technologies detected)
[T+6.5s] signals_node COMPLETE: BusinessSignals(2 signals: hiring + expansion)
[T+7.0s] leadership_node COMPLETE: LeadershipProfile(2 leaders found)
[T+7.0s] Job progress: 0.5, step: "Generating sales playbook"

[T+7.0s] playbook_node: LLM synthesizes → SalesPlaybook(priority=HIGH, 3 actions)
[T+9.0s] Job progress: 0.8, step: "Creating intelligence summary"

[T+9.0s] summary_node: LLM writes narrative → AccountIntelligence assembled
[T+10.5s] Job progress: 1.0, step: null

[T+10.5s] PIPELINE COMPLETE
         → AccountIntelligence saved to AccountStore
         → Job marked COMPLETED with result_id
```

**Total wall-clock time**: ~10–12 seconds (parallelism saves ~5s vs. sequential)

---

## 6. Example Pipeline Execution — Company Name

### Input

```json
{
  "company_name": "Redfin",
  "domain": "redfin.com"
}
```

### Execution Trace

```
[T+0.0s] route_input: company_input present, no visitor_signal → skip to parallel_stage_1
[T+0.0s] Job progress: 0.1, step: "Enriching company profile"

[T+0.0s] PARALLEL START — Stage 1:
         ├─ enrichment_node: enrichment_apis("Redfin") + web_search + scraper(redfin.com)
         ├─ intent_node: no visitor_signal → IntentScore(score=0.0, stage=AWARENESS)
         └─ persona_node: no visitor_signal → PersonaInference(role="Unknown", confidence=0.0)

[T+0.1s] intent_node COMPLETE (instant — no visitor data)
[T+0.1s] persona_node COMPLETE (instant — no visitor data)
[T+3.5s] enrichment_node COMPLETE: CompanyProfile(industry="Real Estate Technology")
[T+3.5s] Job progress: 0.3, step: "Detecting technology stack"

[T+3.5s] PARALLEL START — Stage 2:
         ├─ tech_stack_node: scraper(redfin.com) → script analysis
         ├─ signals_node: web_search("Redfin" hiring OR funding)
         └─ leadership_node: web_search("Redfin" CEO OR VP Sales)

[T+6.0s] All Stage 2 agents complete
[T+6.0s] Job progress: 0.5

[T+6.0s] playbook_node → summary_node
[T+8.5s] PIPELINE COMPLETE (faster — no identification stage, instant intent/persona)
```

**Total wall-clock time**: ~8–10 seconds (no identification stage, instant persona/intent)

---

## 7. PipelineState at Each Barrier

| Barrier Point | Populated Fields | Still Null |
|--------------|-----------------|-----------|
| After Stage 0 | `visitor_signal`, `identified_company`, `job_id` | everything else |
| After Stage 1 | + `company_profile`, `intent`, `persona` | tech, signals, leadership, playbook, intelligence |
| After Stage 2 | + `tech_stack`, `business_signals`, `leadership` | playbook, intelligence |
| After Stage 3 | + `playbook`, `intelligence` | (all populated) |

External Data Sources:
- IP lookup: ipapi.co (primary) → ip-api.com (fallback) — real API calls, no mock
- Web search: Tavily v0.3.3 via `TavilyClient` + `asyncio.to_thread` — real API calls
- Enrichment: Tavily search + Gemini LLM synthesis — Clearbit/Apollo not wired