# Evaluation Metrics — Quality, Confidence & Benchmarks

> **Version**: 1.0  
> **Date**: 2026-03-18  
> **Depends on**: [Agent Architecture](./agent-architecture.md), [Data Pipeline](./data-pipeline.md), [API Contracts](./api-contracts.md)

---

## 1. Core Quality Metrics

### 1.1 Company Identification Accuracy

**Source**: IdentificationAgent  
**Field**: `CompanyProfile.confidence_score`

| Quality Level | Score Range | Meaning |
|--------------|------------|---------|
| High | 0.8–1.0 | IP cleanly resolved to a company via reverse lookup |
| Medium | 0.5–0.79 | Resolved via web search fallback or LLM disambiguation |
| Low | 0.2–0.49 | Best-guess match from limited signals |
| Degraded | 0.0–0.19 | Could not identify; `company_name` may be "Unknown" |

**Factors affecting score**:
- IP lookup returned a non-cloud-provider org → +0.4
- Domain confirmed via enrichment API → +0.3
- Multiple data sources agree on company name → +0.2
- Only LLM inference, no tool confirmation → 0.3 max

---

### 1.2 Intent Scoring Quality

**Source**: IntentScorerAgent  
**Field**: `IntentScore.intent_score` (0.0–10.0), `IntentScore.confidence_score` (0.0–1.0)

**Scoring framework** (deterministic weights provided to LLM):

| Signal | Weight | Category |
|--------|--------|----------|
| Pricing page visit | +3.0 | High intent |
| Product/feature page visit | +2.5 | High intent |
| Case study / testimonial page | +2.0 | Late-stage evaluation |
| Documentation / API page | +1.5 | Technical evaluation |
| Blog / resource page | +0.5 | Early research |
| Repeat visits (per visit, max +1.5) | +0.3 | Engagement depth |
| Time on site > 2 min | +0.5 | Engagement depth |
| Time on site > 5 min | +1.0 | Deep engagement |
| Referral from search engine | +0.5 | Active searching |

**Stage mapping**:

| Score Range | Stage | Interpretation |
|------------|-------|---------------|
| 0.0–2.5 | AWARENESS | Casual browsing, no buying signals |
| 2.5–5.0 | CONSIDERATION | Some interest, exploring options |
| 5.0–7.5 | EVALUATION | Actively comparing solutions |
| 7.5–10.0 | PURCHASE | Strong buying intent, ready for outreach |

**Confidence score for intent**:
- Visitor has 3+ pages visited → confidence ≥ 0.7
- Visitor has pricing page → confidence += 0.1
- Visitor has repeat visits → confidence += 0.1
- Company-only flow (no visitor signal) → confidence = 0.0

---

### 1.3 Persona Inference Confidence

**Source**: PersonaAgent  
**Field**: `PersonaInference.confidence_score`

| Quality Level | Score Range | Criteria |
|--------------|------------|---------|
| High | 0.7–1.0 | 3+ strong behavioral signals, clear pattern match |
| Medium | 0.4–0.69 | 1–2 signals, reasonable inference |
| Low | 0.1–0.39 | Weak signals, generic inference |
| None | 0.0 | No visitor signal provided |

**Pattern recognition matrix**:

| Page Pattern | Inferred Persona | Confidence Boost |
|-------------|-----------------|-----------------|
| `/pricing` + `/case-studies` | Decision maker / buyer | +0.3 |
| `/docs` + `/api` + `/integrations` | Technical evaluator | +0.3 |
| `/blog` only | Early researcher | +0.1 |
| `/pricing` + `/product` + `/case-studies` | Sales/RevOps leader evaluating tools | +0.4 |
| Single page visit | Insufficient data | 0.0 |

---

### 1.4 Data Completeness Score

Measures how many fields in the final `AccountIntelligence` are non-null.

**Calculation**:

```
completeness = populated_sections / total_sections

Where sections = [company, persona, intent, tech_stack, business_signals, leadership, playbook]
Each section counted as 1 if non-null and has confidence_score > 0.0
```

| Completeness | Rating | Meaning |
|-------------|--------|---------|
| 7/7 (1.0) | Full intelligence | All sections populated with real data |
| 5–6/7 | Substantial | Most sections present, some gaps |
| 3–4/7 | Partial | Core sections present, secondary gaps |
| 1–2/7 | Minimal | Significant data gaps |
| 0/7 | Failed | Only company name available |

**Minimum viable output** (for a "successful" analysis):
- `company` section is non-null with `company_name` populated
- `ai_summary` is non-empty
- At least 2 other sections are non-null

---

## 2. Confidence Scoring Framework

### 2.1 Per-Agent Confidence

Every agent computes its own `confidence_score` (0.0–1.0) based on:

| Factor | Weight | Description |
|--------|--------|-------------|
| **Data source reliability** | 40% | Clearbit/Apollo > web search > LLM inference |
| **Signal strength** | 30% | Number and quality of input signals available |
| **Consistency** | 20% | Multiple sources agree on the same data |
| **Completeness** | 10% | Fraction of output fields that are non-null |

### 2.2 Data Source Reliability Rankings

| Source | Reliability Score | Rationale |
|--------|------------------|-----------|
| Clearbit API | 0.9 | Curated business database |
| Apollo API | 0.85 | Large professional database |
| Company website (scraped) | 0.7 | First-party but may be outdated |
| Web search results | 0.6 | Aggregated, may contain noise |
| IP reverse lookup | 0.5–0.8 | Depends on IP type (static vs. dynamic) |
| LLM inference (no tools) | 0.3 | Educated guess, no factual grounding |

### 2.3 Aggregate Confidence (AccountIntelligence)

The `SummaryAgent` computes the final `AccountIntelligence.confidence_score` as a weighted average:

```
aggregate_confidence = (
    company.confidence_score   × 0.25 +
    intent.confidence_score    × 0.20 +
    persona.confidence_score   × 0.15 +
    tech_stack.confidence_score × 0.10 +
    signals.confidence_score   × 0.10 +
    leadership.confidence_score × 0.10 +
    playbook.confidence_score  × 0.10
)
```

Null sections are excluded and weights renormalized. For a company-only analysis (no visitor signal), intent and persona have confidence=0.0 and are effectively excluded.

---

## 3. Latency Benchmarks

### 3.1 Per-Stage Expected Latency

| Stage | Agent(s) | Expected Latency | Bottleneck |
|-------|----------|-----------------|-----------|
| Stage 0 | IdentificationAgent | 1.0–2.0s | IP lookup API call |
| Stage 1 (parallel) | Enrichment + Intent + Persona | 2.0–4.0s | Enrichment (3 tool calls + LLM merge) |
| Stage 2 (parallel) | TechStack + Signals + Leadership | 2.0–3.5s | Web search API latency |
| Stage 3 (sequential) | Playbook + Summary | 2.0–3.5s | Two sequential LLM calls |

### 3.2 Total Pipeline Latency

| Flow Type | Expected Total | Worst Case |
|-----------|---------------|------------|
| Visitor signal (full pipeline) | 8–12s | 20s |
| Company name (skip Stage 0) | 6–10s | 18s |
| Company name, cached enrichment | 4–7s | 12s |

### 3.3 Per-Component Latency Budget

| Component | Budget | Hard Timeout |
|-----------|--------|-------------|
| Single tool call (HTTP) | 2–4s | 8s |
| Single LLM call (GPT-4o-mini) | 1–3s | 10s |
| Tool retry (3× with backoff) | 7s max | 8s (total) |
| Full graph execution | 10s target | 30s |
| Job polling (frontend) | 2s interval | 60s warning |

### 3.4 Latency Optimization Strategies

1. **Parallel execution** saves ~5s vs. sequential (Stages 1 and 2 run 3 agents concurrently)
2. **Tool caching** (`@cached_call(ttl=300)`) eliminates redundant API calls for identical inputs
3. **GPT-4o-mini** is 3× faster than GPT-4 for structured outputs
4. **Early termination** — intent/persona agents complete instantly for company-only flow

---

## 4. Success Criteria

### 4.1 Successful Analysis Output

An analysis is considered **successful** when:

| Criterion | Requirement |
|-----------|------------|
| Job completes | `status == "COMPLETED"` (not FAILED) |
| Company identified | `company.company_name` is non-empty and not "Unknown" |
| AI summary generated | `ai_summary` is non-empty (≥ 50 characters) |
| Playbook produced | `playbook` is non-null with ≥ 1 recommended action |
| Confidence above minimum | `confidence_score ≥ 0.3` |

### 4.2 High-Quality Output

An analysis is considered **high-quality** when (in addition to success criteria):

| Criterion | Requirement |
|-----------|------------|
| Data completeness | ≥ 5/7 sections non-null |
| Aggregate confidence | `confidence_score ≥ 0.6` |
| Multiple data sources | `company.data_sources` has ≥ 2 entries |
| Enriched profile | `industry`, `headquarters`, and `company_size_estimate` are all non-null |
| Playbook is actionable | `priority` is HIGH or MEDIUM, with ≥ 2 recommended actions |

### 4.3 Degraded but Acceptable Output

The system is designed to never fail entirely. A **degraded** output is still served:

| Criterion | Meaning |
|-----------|---------|
| `confidence_score < 0.3` | Low confidence — user should verify |
| Some sections are null | Agents couldn't gather data — noted in `reasoning_trace` |
| `company_name == "Unknown"` | Identification failed — only enrichment from IP metadata |

---

## 5. Edge Case Handling

### 5.1 Missing Data Scenarios

| Scenario | Affected Agents | System Behavior |
|----------|----------------|----------------|
| IP resolves to cloud provider (AWS/GCP) | IdentificationAgent | Falls back to web search; if no hints, returns "Unknown" |
| Company has no website | TechStackAgent | Returns empty `TechStack` with `confidence_score=0.0` |
| No hiring/funding news found | SignalsAgent | Returns empty `signals` list — not treated as error |
| No leadership found online | LeadershipAgent | Returns empty `leaders` list |
| Visitor viewed only 1 page | IntentScorer, PersonaAgent | Low scores, low confidence; still produces output |
| Company name is misspelled | EnrichmentAgent | Web search may correct; LLM attempts fuzzy match |

### 5.2 Conflicting Signals

| Conflict | Resolution Strategy |
|----------|-------------------|
| IP says Company A, enrichment says Company B | IdentificationAgent notes both in `reasoning_trace`; uses enrichment result (higher reliability) |
| Clearbit industry ≠ web search industry | EnrichmentAgent LLM resolves; prefers Clearbit (higher source reliability) |
| High intent score but no company identified | Playbook priority capped at MEDIUM (can't act without a target) |
| Multiple people with same title found | LeadershipAgent keeps all; `reasoning_trace` notes ambiguity |

### 5.3 Low-Confidence Outputs

When `confidence_score < 0.3` on the aggregate:

1. `reasoning_trace` explains which agents had low confidence and why
2. `ai_summary` explicitly mentions data uncertainty
3. `playbook.priority` is set to LOW regardless of other signals
4. Frontend renders a "Low confidence — verify data" warning badge
