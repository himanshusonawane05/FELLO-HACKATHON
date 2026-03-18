# API Contracts — Single Source of Truth

> **Version**: 1.0  
> **Date**: 2026-03-18  
> **Base URL**: `{API_URL}/api/v1`  
> **Content-Type**: `application/json`  
> **Depends on**: [HLD](./hld.md), [LLD](./lld.md)

This document is the **binding contract** between backend and frontend. Both sides MUST conform to these schemas exactly. Any change here MUST be reflected in both `backend/api/schemas/` and `frontend/types/intelligence.ts`.

---

## 1. Common Types

### 1.1 Error Response (all error endpoints)

```json
{
  "error": {
    "code": "string",
    "message": "string",
    "details": "object | null"
  }
}
```

| Field | Type | Description |
|-------|------|-------------|
| `error.code` | `string` | Machine-readable error code: `VALIDATION_ERROR`, `NOT_FOUND`, `INTERNAL_ERROR`, `RATE_LIMITED` |
| `error.message` | `string` | Human-readable description |
| `error.details` | `object \| null` | Pydantic validation errors (422) or null |

### 1.2 Enums (shared between backend and frontend)

```typescript
type JobStatus = "PENDING" | "PROCESSING" | "COMPLETED" | "FAILED"
type IntentStage = "AWARENESS" | "CONSIDERATION" | "EVALUATION" | "PURCHASE"
type Priority = "HIGH" | "MEDIUM" | "LOW"
type SeniorityLevel = "C_LEVEL" | "VP" | "DIRECTOR" | "MANAGER" | "INDIVIDUAL_CONTRIBUTOR" | "UNKNOWN"
type SignalType = "HIRING" | "FUNDING" | "EXPANSION" | "PRODUCT_LAUNCH" | "PARTNERSHIP" | "LEADERSHIP_CHANGE" | "OTHER"
type TechCategory = "CRM" | "MARKETING_AUTOMATION" | "ANALYTICS" | "WEBSITE_PLATFORM" | "CLOUD_INFRASTRUCTURE" | "COMMUNICATION" | "OTHER"
type AnalysisType = "visitor" | "company" | "batch"
```

---

## 2. Endpoints

---

### 2.1 POST `/api/v1/analyze/visitor`

Submit a visitor signal for analysis. Returns immediately with a job ID.

**Request Body:**

```json
{
  "visitor_id": "v-001",
  "ip_address": "34.201.114.42",
  "pages_visited": ["/pricing", "/ai-sales-agent", "/case-studies"],
  "time_on_site_seconds": 222,
  "visit_count": 3,
  "referral_source": "google",
  "device_type": "desktop",
  "location": "New York, USA",
  "timestamps": ["2026-03-18T10:00:00Z", "2026-03-17T14:30:00Z"]
}
```

| Field | Type | Required | Constraints |
|-------|------|----------|-------------|
| `visitor_id` | `string` | yes | Non-empty |
| `ip_address` | `string` | yes | Valid IPv4/IPv6 |
| `pages_visited` | `string[]` | yes | Min 1 item |
| `time_on_site_seconds` | `integer` | no | >= 0, default 0 |
| `visit_count` | `integer` | no | >= 1, default 1 |
| `referral_source` | `string \| null` | no | |
| `device_type` | `string \| null` | no | |
| `location` | `string \| null` | no | |
| `timestamps` | `string[]` | no | ISO 8601 format |

**Response: `202 Accepted`**

```json
{
  "job_id": "550e8400-e29b-41d4-a716-446655440000",
  "status": "PENDING",
  "analysis_type": "visitor",
  "message": "Visitor analysis started",
  "poll_url": "/api/v1/jobs/550e8400-e29b-41d4-a716-446655440000",
  "created_at": "2026-03-18T10:05:00Z"
}
```

**Errors:** `422 Validation Error`

---

### 2.2 POST `/api/v1/analyze/company`

Submit a company name for enrichment analysis.

**Request Body:**

```json
{
  "company_name": "BrightPath Lending",
  "domain": "brightpathlending.com"
}
```

| Field | Type | Required | Constraints |
|-------|------|----------|-------------|
| `company_name` | `string` | yes | Non-empty, max 200 chars |
| `domain` | `string \| null` | no | Valid domain format if provided |

**Response: `202 Accepted`**

```json
{
  "job_id": "660e8400-e29b-41d4-a716-446655440001",
  "status": "PENDING",
  "analysis_type": "company",
  "message": "Company analysis started",
  "poll_url": "/api/v1/jobs/660e8400-e29b-41d4-a716-446655440001",
  "created_at": "2026-03-18T10:06:00Z"
}
```

**Errors:** `422 Validation Error`

---

### 2.3 POST `/api/v1/analyze/batch`

Submit multiple companies for batch analysis.

**Request Body:**

```json
{
  "companies": [
    { "company_name": "BrightPath Lending", "domain": "brightpathlending.com" },
    { "company_name": "Summit Realty Group", "domain": null },
    { "company_name": "Rocket Mortgage" },
    { "company_name": "Redfin" },
    { "company_name": "Compass Real Estate" }
  ]
}
```

| Field | Type | Required | Constraints |
|-------|------|----------|-------------|
| `companies` | `CompanyInput[]` | yes | Min 1, max 20 items |
| `companies[].company_name` | `string` | yes | Non-empty, max 200 chars |
| `companies[].domain` | `string \| null` | no | Valid domain if provided |

**Response: `202 Accepted`**

```json
{
  "batch_id": "770e8400-e29b-41d4-a716-446655440002",
  "job_ids": [
    "770e8400-e29b-41d4-a716-446655440003",
    "770e8400-e29b-41d4-a716-446655440004",
    "770e8400-e29b-41d4-a716-446655440005",
    "770e8400-e29b-41d4-a716-446655440006",
    "770e8400-e29b-41d4-a716-446655440007"
  ],
  "status": "PENDING",
  "analysis_type": "batch",
  "message": "Batch analysis started for 5 companies",
  "poll_url": "/api/v1/jobs/770e8400-e29b-41d4-a716-446655440002",
  "created_at": "2026-03-18T10:07:00Z"
}
```

**Errors:** `422 Validation Error`

---

### 2.4 GET `/api/v1/jobs/{job_id}`

Poll the status of an analysis job.

**Path Parameters:**

| Parameter | Type | Description |
|-----------|------|-------------|
| `job_id` | `string (UUID)` | The job ID returned from an analyze endpoint |

**Response: `200 OK`**

```json
{
  "job_id": "550e8400-e29b-41d4-a716-446655440000",
  "status": "PROCESSING",
  "progress": 0.45,
  "current_step": "Enriching company profile",
  "result_id": null,
  "error": null,
  "created_at": "2026-03-18T10:05:00Z",
  "updated_at": "2026-03-18T10:05:12Z"
}
```

When **completed**:

```json
{
  "job_id": "550e8400-e29b-41d4-a716-446655440000",
  "status": "COMPLETED",
  "progress": 1.0,
  "current_step": null,
  "result_id": "880e8400-e29b-41d4-a716-446655440010",
  "error": null,
  "created_at": "2026-03-18T10:05:00Z",
  "updated_at": "2026-03-18T10:05:28Z"
}
```

When **failed**:

```json
{
  "job_id": "550e8400-e29b-41d4-a716-446655440000",
  "status": "FAILED",
  "progress": 0.3,
  "current_step": null,
  "result_id": null,
  "error": "Company identification failed: unable to resolve IP to company",
  "created_at": "2026-03-18T10:05:00Z",
  "updated_at": "2026-03-18T10:05:15Z"
}
```

| Field | Type | Description |
|-------|------|-------------|
| `job_id` | `string` | UUID of the job |
| `status` | `JobStatus` | PENDING, PROCESSING, COMPLETED, FAILED |
| `progress` | `number` | 0.0–1.0 progress indicator |
| `current_step` | `string \| null` | Human-readable current operation |
| `result_id` | `string \| null` | Account ID when completed (use with GET /accounts/{id}) |
| `error` | `string \| null` | Error message when failed |
| `created_at` | `string` | ISO 8601 timestamp |
| `updated_at` | `string` | ISO 8601 timestamp |

**Errors:** `404 Not Found`

---

### 2.5 GET `/api/v1/accounts/{account_id}`

Retrieve full account intelligence.

**Path Parameters:**

| Parameter | Type | Description |
|-----------|------|-------------|
| `account_id` | `string (UUID)` | The result_id from a completed job |

**Response: `200 OK`**

```json
{
  "account_id": "880e8400-e29b-41d4-a716-446655440010",
  "company": {
    "company_name": "Acme Mortgage",
    "domain": "acmemortgage.com",
    "industry": "Mortgage Lending",
    "company_size_estimate": "200-500 employees",
    "headquarters": "Dallas, Texas, USA",
    "founding_year": 2005,
    "description": "Acme Mortgage is a mid-sized residential mortgage lender specializing in first-time homebuyer programs across the southern United States.",
    "annual_revenue_range": "$50M-$100M",
    "confidence_score": 0.85,
    "data_sources": ["clearbit", "web_search", "scraper"]
  },
  "persona": {
    "likely_role": "Head of Sales Operations",
    "department": "Sales",
    "seniority_level": "DIRECTOR",
    "behavioral_signals": [
      "Visited pricing page (buyer intent)",
      "Viewed AI sales agent page (product evaluation)",
      "Read case studies (social proof seeking)"
    ],
    "confidence_score": 0.72,
    "reasoning": "Pricing + product + case study pattern indicates sales leadership evaluating automation tools"
  },
  "intent": {
    "intent_score": 8.4,
    "intent_stage": "EVALUATION",
    "signals_detected": [
      "Pricing page visit (high intent)",
      "3 visits this week (repeat engagement)",
      "Case study consumption (late-stage evaluation)",
      "3m42s dwell time (deep engagement)"
    ],
    "page_score_breakdown": {
      "/pricing": 3.0,
      "/ai-sales-agent": 2.5,
      "/case-studies": 2.0,
      "repeat_visit_bonus": 0.9
    },
    "confidence_score": 0.88
  },
  "tech_stack": {
    "technologies": [
      { "name": "Salesforce", "category": "CRM", "confidence_score": 0.9 },
      { "name": "HubSpot", "category": "MARKETING_AUTOMATION", "confidence_score": 0.85 },
      { "name": "WordPress", "category": "WEBSITE_PLATFORM", "confidence_score": 0.95 },
      { "name": "Google Analytics", "category": "ANALYTICS", "confidence_score": 0.92 }
    ],
    "detection_method": "script_analysis",
    "confidence_score": 0.9
  },
  "business_signals": {
    "signals": [
      {
        "signal_type": "HIRING",
        "title": "Hiring Sales Development Representatives",
        "description": "3 open SDR positions on LinkedIn indicate sales team expansion",
        "source_url": "https://linkedin.com/company/acme-mortgage/jobs"
      },
      {
        "signal_type": "EXPANSION",
        "title": "Expanding to Florida Market",
        "description": "Recent press release announced entry into Florida residential mortgage market",
        "source_url": "https://businesswire.com/acme-florida-expansion"
      }
    ],
    "confidence_score": 0.7
  },
  "leadership": {
    "leaders": [
      {
        "name": "Jane Smith",
        "title": "VP of Sales",
        "department": "Sales",
        "linkedin_url": "https://linkedin.com/in/janesmith",
        "source_url": "https://acmemortgage.com/about"
      },
      {
        "name": "Bob Johnson",
        "title": "CEO",
        "department": "Executive",
        "linkedin_url": "https://linkedin.com/in/bobjohnson",
        "source_url": "https://acmemortgage.com/about"
      }
    ],
    "confidence_score": 0.75
  },
  "playbook": {
    "priority": "HIGH",
    "recommended_actions": [
      {
        "action": "Research VP Sales Jane Smith on LinkedIn",
        "rationale": "Direct decision maker for sales automation tools",
        "priority": "HIGH"
      },
      {
        "action": "Add to outbound campaign with mortgage vertical messaging",
        "rationale": "Industry-specific positioning increases response rate",
        "priority": "HIGH"
      },
      {
        "action": "Send personalized outreach referencing case studies",
        "rationale": "Visitor already consumed case studies — reference them to show awareness",
        "priority": "MEDIUM"
      }
    ],
    "talking_points": [
      "Mention their Florida expansion as a growth trigger for sales automation",
      "Reference SDR hiring — position product as force multiplier for new reps",
      "Lead with mortgage-specific case studies they already viewed"
    ],
    "outreach_template": "Hi Jane, I noticed Acme Mortgage is expanding into Florida — congrats! When scaling into new markets, having your SDR team equipped with AI-powered prospecting can accelerate pipeline. We've helped similar lenders like [Case Study] increase qualified meetings by 40%. Would you be open to a quick call?"
  },
  "ai_summary": "Acme Mortgage is a mid-sized residential lender based in Dallas, TX with 200-500 employees. They are actively expanding into the Florida market and hiring SDRs, suggesting significant growth momentum. A likely sales operations leader visited pricing, product, and case study pages 3 times this week with high engagement (3m42s), indicating active evaluation of AI sales tools. Their current stack includes Salesforce CRM and HubSpot, suggesting technical sophistication. Recommend high-priority outreach to VP Sales Jane Smith with mortgage-specific positioning.",
  "analyzed_at": "2026-03-18T10:05:28Z",
  "confidence_score": 0.82,
  "reasoning_trace": [
    "IP 34.201.114.42 resolved to Acme Mortgage via ipapi.co (confidence: 0.8)",
    "Company enriched via Clearbit + web search (3 sources)",
    "Intent scored at 8.4/10 based on pricing+case study+repeat visit signals",
    "Persona inferred as Sales Operations Director from page pattern",
    "Tech stack detected: 4 technologies via script tag analysis",
    "2 business signals found via Tavily search",
    "2 leadership contacts discovered via web search",
    "Playbook generated with HIGH priority based on intent 8.4 + hiring signals"
  ]
}
```

**Full Response Schema:**

| Field | Type | Nullable | Description |
|-------|------|----------|-------------|
| `account_id` | `string` | no | Unique account identifier |
| `company` | `CompanyProfile` | no | Always present — enriched company data |
| `persona` | `PersonaInference` | yes | Null if no visitor signal provided |
| `intent` | `IntentScore` | yes | Null if no visitor signal provided |
| `tech_stack` | `TechStack` | yes | Null if detection failed |
| `business_signals` | `BusinessSignals` | yes | Null if search found nothing |
| `leadership` | `LeadershipProfile` | yes | Null if discovery failed |
| `playbook` | `SalesPlaybook` | yes | Null if insufficient data |
| `ai_summary` | `string` | no | Always present — may be minimal |
| `analyzed_at` | `string` | no | ISO 8601 |
| `confidence_score` | `number` | no | 0.0–1.0 overall confidence |
| `reasoning_trace` | `string[]` | no | Step-by-step reasoning log |

**Sub-schemas referenced above:**

**CompanyProfile:**

| Field | Type | Nullable |
|-------|------|----------|
| `company_name` | `string` | no |
| `domain` | `string` | yes |
| `industry` | `string` | yes |
| `company_size_estimate` | `string` | yes |
| `headquarters` | `string` | yes |
| `founding_year` | `integer` | yes |
| `description` | `string` | yes |
| `annual_revenue_range` | `string` | yes |
| `confidence_score` | `number` | no |
| `data_sources` | `string[]` | no |

**PersonaInference:**

| Field | Type | Nullable |
|-------|------|----------|
| `likely_role` | `string` | no |
| `department` | `string` | yes |
| `seniority_level` | `SeniorityLevel` | no |
| `behavioral_signals` | `string[]` | no |
| `confidence_score` | `number` | no |
| `reasoning` | `string` | no |

**IntentScore:**

| Field | Type | Nullable |
|-------|------|----------|
| `intent_score` | `number` | no (0.0–10.0) |
| `intent_stage` | `IntentStage` | no |
| `signals_detected` | `string[]` | no |
| `page_score_breakdown` | `Record<string, number>` | no |
| `confidence_score` | `number` | no |

**TechStack:**

| Field | Type | Nullable |
|-------|------|----------|
| `technologies` | `Technology[]` | no |
| `detection_method` | `string` | no |
| `confidence_score` | `number` | no |

**Technology:**

| Field | Type | Nullable |
|-------|------|----------|
| `name` | `string` | no |
| `category` | `TechCategory` | no |
| `confidence_score` | `number` | no |

**BusinessSignals:**

| Field | Type | Nullable |
|-------|------|----------|
| `signals` | `Signal[]` | no |
| `confidence_score` | `number` | no |

**Signal:**

| Field | Type | Nullable |
|-------|------|----------|
| `signal_type` | `SignalType` | no |
| `title` | `string` | no |
| `description` | `string` | no |
| `source_url` | `string` | yes |

**LeadershipProfile:**

| Field | Type | Nullable |
|-------|------|----------|
| `leaders` | `Leader[]` | no |
| `confidence_score` | `number` | no |

**Leader:**

| Field | Type | Nullable |
|-------|------|----------|
| `name` | `string` | no |
| `title` | `string` | no |
| `department` | `string` | yes |
| `linkedin_url` | `string` | yes |
| `source_url` | `string` | yes |

**SalesPlaybook:**

| Field | Type | Nullable |
|-------|------|----------|
| `priority` | `Priority` | no |
| `recommended_actions` | `RecommendedAction[]` | no |
| `talking_points` | `string[]` | no |
| `outreach_template` | `string` | yes |

**RecommendedAction:**

| Field | Type | Nullable |
|-------|------|----------|
| `action` | `string` | no |
| `rationale` | `string` | no |
| `priority` | `Priority` | no |

**Errors:** `404 Not Found`

---

### 2.6 GET `/api/v1/accounts`

List all analyzed accounts with pagination.

**Query Parameters:**

| Parameter | Type | Default | Constraints |
|-----------|------|---------|-------------|
| `page` | `integer` | 1 | >= 1 |
| `page_size` | `integer` | 20 | 1–100 |

**Response: `200 OK`**

```json
{
  "accounts": [
    {
      "account_id": "880e8400-e29b-41d4-a716-446655440010",
      "company_name": "Acme Mortgage",
      "domain": "acmemortgage.com",
      "industry": "Mortgage Lending",
      "intent_score": 8.4,
      "intent_stage": "EVALUATION",
      "priority": "HIGH",
      "confidence_score": 0.82,
      "analyzed_at": "2026-03-18T10:05:28Z"
    }
  ],
  "total": 1,
  "page": 1,
  "page_size": 20
}
```

| Field | Type | Description |
|-------|------|-------------|
| `accounts` | `AccountSummary[]` | Paginated list of account summaries |
| `total` | `integer` | Total number of accounts |
| `page` | `integer` | Current page number |
| `page_size` | `integer` | Items per page |

**AccountSummary:**

| Field | Type | Nullable |
|-------|------|----------|
| `account_id` | `string` | no |
| `company_name` | `string` | no |
| `domain` | `string` | yes |
| `industry` | `string` | yes |
| `intent_score` | `number` | yes (null if no visitor signal) |
| `intent_stage` | `IntentStage` | yes |
| `priority` | `Priority` | yes |
| `confidence_score` | `number` | no |
| `analyzed_at` | `string` | no |

---

### 2.7 GET `/api/v1/health`

Health check endpoint.

**Response: `200 OK`**

```json
{
  "status": "healthy",
  "version": "1.0.0",
  "timestamp": "2026-03-18T10:00:00Z"
}
```

---

## 3. Frontend Polling Contract

The frontend MUST follow this polling protocol:

1. Submit analysis via POST `/analyze/*` → receive `job_id`
2. Poll GET `/jobs/{job_id}` every **2 seconds**
3. While `status` is `PENDING` or `PROCESSING`:
   - Show progress bar using `progress` field (0.0–1.0)
   - Show `current_step` text below progress bar
4. When `status` is `COMPLETED`:
   - Stop polling
   - Fetch full data via GET `/accounts/{result_id}`
5. When `status` is `FAILED`:
   - Stop polling
   - Display `error` message with retry button
6. If polling exceeds **60 seconds** with no completion:
   - Show "Analysis is taking longer than expected" message
   - Continue polling (do not stop)

---

## 4. TypeScript Interface (frontend/types/intelligence.ts)

This MUST be kept in sync with the API response shapes above:

```typescript
// Enums
export type JobStatus = "PENDING" | "PROCESSING" | "COMPLETED" | "FAILED";
export type IntentStage = "AWARENESS" | "CONSIDERATION" | "EVALUATION" | "PURCHASE";
export type Priority = "HIGH" | "MEDIUM" | "LOW";
export type SeniorityLevel = "C_LEVEL" | "VP" | "DIRECTOR" | "MANAGER" | "INDIVIDUAL_CONTRIBUTOR" | "UNKNOWN";
export type SignalType = "HIRING" | "FUNDING" | "EXPANSION" | "PRODUCT_LAUNCH" | "PARTNERSHIP" | "LEADERSHIP_CHANGE" | "OTHER";
export type TechCategory = "CRM" | "MARKETING_AUTOMATION" | "ANALYTICS" | "WEBSITE_PLATFORM" | "CLOUD_INFRASTRUCTURE" | "COMMUNICATION" | "OTHER";
export type AnalysisType = "visitor" | "company" | "batch";

// Request types
export interface VisitorAnalysisRequest {
  visitor_id: string;
  ip_address: string;
  pages_visited: string[];
  time_on_site_seconds?: number;
  visit_count?: number;
  referral_source?: string | null;
  device_type?: string | null;
  location?: string | null;
  timestamps?: string[];
}

export interface CompanyAnalysisRequest {
  company_name: string;
  domain?: string | null;
}

export interface BatchAnalysisRequest {
  companies: CompanyAnalysisRequest[];
}

// Response types
export interface AnalysisResponse {
  job_id: string;
  status: JobStatus;
  analysis_type: AnalysisType;
  message: string;
  poll_url: string;
  created_at: string;
}

export interface BatchAnalysisResponse {
  batch_id: string;
  job_ids: string[];
  status: JobStatus;
  analysis_type: "batch";
  message: string;
  poll_url: string;
  created_at: string;
}

export interface JobStatusResponse {
  job_id: string;
  status: JobStatus;
  progress: number;
  current_step: string | null;
  result_id: string | null;
  error: string | null;
  created_at: string;
  updated_at: string;
}

// Domain types
export interface CompanyProfile {
  company_name: string;
  domain: string | null;
  industry: string | null;
  company_size_estimate: string | null;
  headquarters: string | null;
  founding_year: number | null;
  description: string | null;
  annual_revenue_range: string | null;
  confidence_score: number;
  data_sources: string[];
}

export interface PersonaInference {
  likely_role: string;
  department: string | null;
  seniority_level: SeniorityLevel;
  behavioral_signals: string[];
  confidence_score: number;
  reasoning: string;
}

export interface IntentScore {
  intent_score: number;
  intent_stage: IntentStage;
  signals_detected: string[];
  page_score_breakdown: Record<string, number>;
  confidence_score: number;
}

export interface Technology {
  name: string;
  category: TechCategory;
  confidence_score: number;
}

export interface TechStack {
  technologies: Technology[];
  detection_method: string;
  confidence_score: number;
}

export interface Signal {
  signal_type: SignalType;
  title: string;
  description: string;
  source_url: string | null;
}

export interface BusinessSignals {
  signals: Signal[];
  confidence_score: number;
}

export interface Leader {
  name: string;
  title: string;
  department: string | null;
  linkedin_url: string | null;
  source_url: string | null;
}

export interface LeadershipProfile {
  leaders: Leader[];
  confidence_score: number;
}

export interface RecommendedAction {
  action: string;
  rationale: string;
  priority: Priority;
}

export interface SalesPlaybook {
  priority: Priority;
  recommended_actions: RecommendedAction[];
  talking_points: string[];
  outreach_template: string | null;
  confidence_score: number;
}

export interface AccountIntelligence {
  account_id: string;
  company: CompanyProfile;
  persona: PersonaInference | null;
  intent: IntentScore | null;
  tech_stack: TechStack | null;
  business_signals: BusinessSignals | null;
  leadership: LeadershipProfile | null;
  playbook: SalesPlaybook | null;
  ai_summary: string;
  analyzed_at: string;
  confidence_score: number;
  reasoning_trace: string[];
}

export interface AccountSummary {
  account_id: string;
  company_name: string;
  domain: string | null;
  industry: string | null;
  intent_score: number | null;
  intent_stage: IntentStage | null;
  priority: Priority | null;
  confidence_score: number;
  analyzed_at: string;
}

export interface AccountListResponse {
  accounts: AccountSummary[];
  total: number;
  page: number;
  page_size: number;
}

export interface HealthResponse {
  status: string;
  version: string;
  timestamp: string;
}

export interface ApiError {
  error: {
    code: string;
    message: string;
    details: Record<string, unknown> | null;
  };
}
```

---

## 5. HTTP Status Code Reference

| Status | When |
|--------|------|
| `200 OK` | Successful GET requests |
| `202 Accepted` | Analysis job submitted successfully |
| `404 Not Found` | Job or account ID doesn't exist |
| `422 Unprocessable Entity` | Request body validation failed |
| `500 Internal Server Error` | Unexpected server error (generic message) |

---

## 6. CORS Configuration

```
Allowed Origins: ["http://localhost:3000", $FRONTEND_URL]
Allowed Methods: ["GET", "POST", "OPTIONS"]
Allowed Headers: ["Content-Type"]
```
