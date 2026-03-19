# Visitor Pipeline Validation — Real IP Testing & Debug Guide

> **Purpose**: Verify real-world IP/domain enrichment, validate Tavily integration, and debug "Unknown" company identification.

---

## 1. Pipeline Flow Summary

After a visitor signal hits `POST /api/v1/analyze/visitor`:

```
VisitorSignal (visitor_id, ip_address, pages_visited, ...)
        │
        ▼ route_input → identification_node (visitor path only)
        │
        ├─ Private IP? (10.x, 192.168.x, 127.x, etc.) → CompanyInput("Unknown (Private IP)")
        │
        ├─ IPLookupTool: ipapi.co → ip-api.com fallback
        │     └─ Returns org/isp; if org+isp contains cloud keywords → company_name=None
        │
        ├─ Cloud provider? (AWS, GCP, Azure, Cloudflare, Google, etc.) → CompanyInput("Unknown")
        │
        ├─ Company resolved? → CompanyInput(company_name, domain)
        │
        └─ Else → Tavily search "what company uses IP X" (result never used; avoids fabrication)
                    → CompanyInput("Unknown")
        │
        ▼ Stage 1 (parallel: asyncio.gather)
        │
        ├─ EnrichmentAgent: CompanyInput → CompanyProfile
        │     • Unknown? → minimal profile (confidence 0.1)
        │     • Else: Tavily search "{company_name} company overview..." + LLM synthesis
        │
        ├─ IntentScorerAgent: VisitorSignal → IntentScore (rule-based, no LLM)
        │
        └─ PersonaAgent: VisitorSignal → PersonaInference (LLM)
        │
        ▼ Stage 2 (parallel)
        │
        ├─ TechStackAgent: CompanyProfile → TechStack (LLM; no scraper for Unknown)
        ├─ SignalsAgent: Tavily search "{company_name}" hiring/funding → BusinessSignals
        └─ LeadershipAgent: Tavily search "{company_name}" CEO/VP → LeadershipProfile
        │
        ▼ Stage 3 (sequential)
        │
        ├─ PlaybookAgent: all prior → SalesPlaybook
        └─ SummaryAgent: all prior → AccountIntelligence (final output)
```

**Key**: If identification returns "Unknown", Enrichment returns a minimal profile immediately (no Tavily for company overview). Downstream agents (TechStack, Signals, Leadership) receive low-confidence company and typically return empty or minimal data.

---

## 2. Real IP Test Scenarios (Visitor Scenarios Tab)

The Visitor Scenarios tab uses **real IPs** that resolve via ipapi.co or ip-api.com:

| Scenario         | IP Address     | Expected org from lookup                     | Expected company_name |
|------------------|---------------|----------------------------------------------|------------------------|
| High-Intent      | 208.80.154.1  | Wikimedia Foundation Inc                     | Wikimedia Foundation Inc |
| Technical Eval   | 193.63.75.1   | Imperial College of Science / Jisc          | Imperial College of Science |
| Early Researcher | 147.252.1.1   | Technological University Dublin / HEAnet    | Technological University Dublin |
| Cloud (Unknown)  | 34.201.45.12  | Amazon / AWS (cloud provider)                | Unknown |

**Cloud providers filtered** (from `backend/tools/ip_lookup.py`): amazon, aws, google, gcp, microsoft, azure, cloudflare, digitalocean, linode, vultr, fastly.

---

## 3. Debug Checklist — Company is "Unknown"

When the identified company is "Unknown", trace in this order:

| Step | Check | Where | Action |
|------|-------|-------|--------|
| 1 | Is IP private/reserved? | `identification.py` `_PRIVATE_PREFIXES` | 10.x, 192.168.x, 127.x → "Unknown (Private IP)" |
| 2 | IP lookup returns None? | `ip_lookup.py` → ipapi.co, then ip-api.com | Check network; ipapi.co may rate-limit or 403 |
| 3 | Org/ISP is cloud provider? | `ip_lookup.py` `CLOUD_PROVIDERS` | AWS, GCP, Cloudflare, etc. → company_name=None |
| 4 | Tavily used for IP? | `identification.py` `_tavily_search` | Tavily results are **not** used (intentionally) — avoids fabrication |
| 5 | Enrichment for Unknown? | `enrichment.py` `_is_unknown_company` | Skips Tavily; returns minimal profile (confidence 0.1) |

**TL;DR**: "Unknown" usually means (a) cloud provider IP, (b) private IP, or (c) IP lookup failed.

---

## 4. Tavily Integration Validation

TAVILY_API_KEY is used by:

| Agent/Tool      | Purpose | Query pattern |
|-----------------|---------|---------------|
| IdentificationAgent | IP→company (unused) | "what company uses IP address {ip}" |
| EnrichmentAgent | Company overview | "{company_name} company overview industry employees revenue" |
| SignalsAgent    | Business signals  | '"{company_name}" hiring OR funding OR expansion OR launch' |
| LeadershipAgent | Leadership        | '"{company_name}" CEO OR "VP Sales" site:linkedin.com' |
| WebSearchTool   | Generic search     | Used by above agents |

**Validation steps:**

1. Ensure `TAVILY_API_KEY` is set in `backend/.env`.
2. Run a **company lookup** (not visitor) — e.g. "Salesforce" — and confirm enriched industry, HQ, description.
3. Check backend logs for: `Tavily search returned N results for '...'`.
4. If Tavily returns no results: `[EnrichmentAgent] Tavily returned no results for {company_name}` — verify key, quota, and query.

**Without Tavily**: Enrichment falls back to LLM general knowledge; Signals and Leadership return empty. The pipeline still completes but with lower-confidence, sparser data.

---

## 5. Validation Results (2026-03-19)

| IP | Scenario | Identified Company | Enrichment | Verified |
|----|----------|--------------------|-----------|----------|
| 208.80.154.1 | High-Intent (Wikimedia) | Wikimedia Foundation Inc. | Full (industry, HQ, signals, leadership, playbook) | ✓ |
| 34.201.45.12 | Cloud (AWS) | Unknown | Minimal (confidence 0.1, no data_sources) | ✓ |

**Conclusion**: IP lookup correctly resolves real org IPs to company names; cloud provider IPs are filtered and return Unknown. Tavily integration is effective for enrichment, signals, and leadership when company is identified.

---

## 6. API Response & UI Validation

### Submit via UI (Visitor Scenarios tab)

1. Open frontend → Visitor Scenarios tab.
2. Click "Run Analysis →" on a scenario.
3. Observe:
   - API returns 202 + `job_id`.
   - Poll `/api/v1/jobs/{job_id}` until `status=COMPLETED`.
   - `result_id` = account_id for the final report.
   - Navigate to `/account/{result_id}` to view full intelligence.

### Expected outcomes by scenario

| Scenario  | Company name in result | Enrichment | Persona / Intent |
|-----------|------------------------|-----------|------------------|
| High-Intent (Wikimedia) | Wikimedia Foundation Inc | Full (industry, HQ, etc.) | From page signals |
| Technical (Imperial)   | Imperial College of Science | Full | From page signals |
| Research (TU Dublin)   | Technological University Dublin | Full | From page signals |
| Cloud (AWS)           | Unknown | Minimal (confidence 0.1) | From page signals |

---

## 7. Quick IP Lookup Test (curl)

To validate IP lookup independently:

```bash
# ipapi.co (primary)
curl -s "https://ipapi.co/208.80.154.1/json/" | jq .

# ip-api.com (fallback)
curl -s "http://ip-api.com/json/208.80.154.1" | jq .
```

Interpretation:

- `org` or `isp` contains cloud keywords → pipeline returns Unknown.
- `org`/`isp` is a real org name → pipeline should identify that company.

---

## 8. References

- [Data Pipeline](./data-pipeline.md) — Full stage-by-stage flow.
- [Agent Architecture](./agent-architecture.md) — Agent contracts.
- [API Contracts](./api-contracts.md) — Endpoint specs.
