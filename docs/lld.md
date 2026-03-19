# Low-Level Design — Fello AI Account Intelligence System

> **Version**: 1.0  
> **Date**: 2026-03-18  
> **Depends on**: [HLD](./hld.md)

---

## 1. Directory Structure

```
backend/
├── __init__.py
├── main.py                          # FastAPI app factory + lifespan
├── config.py                        # pydantic-settings: Settings class
├── domain/
│   ├── __init__.py                  # Re-exports all models
│   ├── base.py                      # BaseEntity
│   ├── visitor.py                   # VisitorSignal
│   ├── company.py                   # CompanyInput, CompanyProfile
│   ├── persona.py                   # PersonaInference
│   ├── intent.py                    # IntentScore
│   ├── tech_stack.py                # TechStack, Technology
│   ├── signals.py                   # BusinessSignals, Signal
│   ├── leadership.py                # LeadershipProfile, Leader
│   ├── playbook.py                  # SalesPlaybook, RecommendedAction
│   └── intelligence.py              # AccountIntelligence (aggregate root)
├── agents/
│   ├── __init__.py
│   ├── base_agent.py                # BaseAgent ABC
│   ├── identification.py            # IdentificationAgent
│   ├── enrichment.py                # EnrichmentAgent
│   ├── persona.py                   # PersonaAgent
│   ├── intent_scorer.py             # IntentScorerAgent
│   ├── tech_stack.py                # TechStackAgent
│   ├── signals.py                   # SignalsAgent
│   ├── leadership.py                # LeadershipAgent
│   ├── playbook.py                  # PlaybookAgent
│   └── summary.py                   # SummaryAgent
├── graph/
│   ├── __init__.py
│   ├── state.py                     # PipelineState TypedDict
│   ├── nodes.py                     # Node wrapper functions
│   └── workflow.py                  # build_workflow() → CompiledGraph
├── tools/
│   ├── __init__.py
│   ├── base_tool.py                 # BaseTool ABC + @cached_call
│   ├── ip_lookup.py                 # IPLookupTool
│   ├── web_search.py                # WebSearchTool
│   ├── scraper.py                   # ScraperTool
│   └── enrichment_apis.py           # EnrichmentAPITool
├── controllers/
│   ├── __init__.py
│   └── analysis.py                  # AnalysisController
├── api/
│   ├── __init__.py
│   ├── router.py                    # APIRouter aggregation
│   ├── routes/
│   │   ├── __init__.py
│   │   ├── analyze.py               # POST /analyze/*
│   │   ├── jobs.py                  # GET /jobs/{id}
│   │   └── accounts.py              # GET /accounts, /accounts/{id}
│   └── schemas/
│       ├── __init__.py
│       ├── base.py                  # BaseResponseSchema
│       ├── requests.py              # VisitorAnalysisRequest, etc.
│       └── responses.py             # AccountIntelligenceResponse, etc.
└── storage/
    ├── __init__.py
    ├── base.py                      # Abstract store interface
    ├── job_store.py                 # InMemoryJobStore
    └── account_store.py             # InMemoryAccountStore

frontend/
├── package.json
├── tsconfig.json
├── next.config.ts
├── tailwind.config.ts
├── app/
│   ├── layout.tsx                   # Root layout: fonts, theme, providers
│   ├── page.tsx                     # Dashboard: account list + analysis form
│   ├── account/
│   │   └── [id]/
│   │       └── page.tsx             # Account detail view
│   └── globals.css                  # Tailwind directives + CSS variables
├── components/
│   ├── AnalysisForm.tsx             # Input form (visitor signal or company)
│   ├── AccountCard.tsx              # Summary card in dashboard list
│   ├── IntentMeter.tsx              # Animated score bar
│   ├── PersonaBadge.tsx             # Role + confidence pill
│   ├── CompanyProfileCard.tsx       # Enriched company details
│   ├── TechStackGrid.tsx            # Technology grid
│   ├── LeadershipList.tsx           # Decision maker list
│   ├── SignalsFeed.tsx              # Business signals timeline
│   ├── SalesPlaybook.tsx            # Recommended actions panel
│   ├── AISummary.tsx                # AI narrative block
│   └── LoadingSkeleton.tsx          # Reusable skeleton states
├── hooks/
│   ├── useAccountAnalysis.ts        # Submit analysis + poll for result
│   └── useJobPoller.ts              # Generic job polling hook
├── lib/
│   └── api.ts                       # Centralized API client
└── types/
    └── intelligence.ts              # TypeScript interfaces mirroring domain
```

---

## 2. Domain Models (Pydantic v2)

All models extend `BaseEntity` and are frozen (immutable).

### 2.1 BaseEntity

```python
class BaseEntity(BaseModel):
    model_config = ConfigDict(frozen=True)
    id: str = Field(default_factory=lambda: str(uuid4()))
    created_at: str = Field(default_factory=lambda: datetime.utcnow().isoformat())
```

### 2.2 VisitorSignal (Input)

```python
class VisitorSignal(BaseEntity):
    """Raw visitor activity data from website tracking."""
    visitor_id: str
    ip_address: str
    pages_visited: list[str] = Field(default_factory=list)
    time_on_site_seconds: int = Field(ge=0, default=0)
    visit_count: int = Field(ge=1, default=1)
    referral_source: Optional[str] = None
    device_type: Optional[str] = None
    location: Optional[str] = None
    timestamps: list[str] = Field(default_factory=list)
```

### 2.3 CompanyInput (Input)

```python
class CompanyInput(BaseEntity):
    """Minimal company input for direct enrichment."""
    company_name: str
    domain: Optional[str] = None
```

### 2.4 CompanyProfile (Enrichment Output)

```python
class CompanyProfile(BaseEntity):
    """Enriched company information from multiple data sources."""
    company_name: str
    domain: Optional[str] = None
    industry: Optional[str] = None
    company_size_estimate: Optional[str] = None
    headquarters: Optional[str] = None
    founding_year: Optional[int] = None
    description: Optional[str] = None
    annual_revenue_range: Optional[str] = None
    confidence_score: float = Field(ge=0.0, le=1.0, default=0.0)
    reasoning_trace: list[str] = Field(default_factory=list)
    data_sources: list[str] = Field(default_factory=list)
```

### 2.5 PersonaInference (Agent Output)

```python
class SeniorityLevel(str, Enum):
    C_LEVEL = "C_LEVEL"
    VP = "VP"
    DIRECTOR = "DIRECTOR"
    MANAGER = "MANAGER"
    INDIVIDUAL_CONTRIBUTOR = "INDIVIDUAL_CONTRIBUTOR"
    UNKNOWN = "UNKNOWN"

class PersonaInference(BaseEntity):
    """Inferred visitor persona from behavioral signals."""
    likely_role: str
    department: Optional[str] = None
    seniority_level: SeniorityLevel = SeniorityLevel.UNKNOWN
    behavioral_signals: list[str] = Field(default_factory=list)
    confidence_score: float = Field(ge=0.0, le=1.0, default=0.0)
    reasoning_trace: list[str] = Field(default_factory=list)
```

### 2.6 IntentScore (Agent Output)

```python
class IntentStage(str, Enum):
    AWARENESS = "AWARENESS"
    CONSIDERATION = "CONSIDERATION"
    EVALUATION = "EVALUATION"
    PURCHASE = "PURCHASE"

class IntentScore(BaseEntity):
    """Buying intent assessment from visitor behavior signals."""
    intent_score: float = Field(ge=0.0, le=10.0, default=0.0)
    intent_stage: IntentStage = IntentStage.AWARENESS
    signals_detected: list[str] = Field(default_factory=list)
    page_score_breakdown: dict[str, float] = Field(default_factory=dict)
    confidence_score: float = Field(ge=0.0, le=1.0, default=0.0)
    reasoning_trace: list[str] = Field(default_factory=list)
```

### 2.7 TechStack (Agent Output)

```python
class TechCategory(str, Enum):
    CRM = "CRM"
    MARKETING_AUTOMATION = "MARKETING_AUTOMATION"
    ANALYTICS = "ANALYTICS"
    WEBSITE_PLATFORM = "WEBSITE_PLATFORM"
    CLOUD_INFRASTRUCTURE = "CLOUD_INFRASTRUCTURE"
    COMMUNICATION = "COMMUNICATION"
    OTHER = "OTHER"

class Technology(BaseEntity):
    """A single detected technology."""
    name: str
    category: TechCategory = TechCategory.OTHER
    confidence_score: float = Field(ge=0.0, le=1.0, default=0.0)

class TechStack(BaseEntity):
    """Detected technology stack from website analysis."""
    technologies: list[Technology] = Field(default_factory=list)
    detection_method: str = "script_analysis"
    confidence_score: float = Field(ge=0.0, le=1.0, default=0.0)
    reasoning_trace: list[str] = Field(default_factory=list)
```

### 2.8 BusinessSignals (Agent Output)

```python
class SignalType(str, Enum):
    HIRING = "HIRING"
    FUNDING = "FUNDING"
    EXPANSION = "EXPANSION"
    PRODUCT_LAUNCH = "PRODUCT_LAUNCH"
    PARTNERSHIP = "PARTNERSHIP"
    LEADERSHIP_CHANGE = "LEADERSHIP_CHANGE"
    OTHER = "OTHER"

class Signal(BaseEntity):
    """A single business signal indicating opportunity."""
    signal_type: SignalType = SignalType.OTHER
    title: str
    description: str
    source_url: Optional[str] = None
    detected_at: Optional[str] = None

class BusinessSignals(BaseEntity):
    """Collection of business signals for opportunity detection."""
    signals: list[Signal] = Field(default_factory=list)
    confidence_score: float = Field(ge=0.0, le=1.0, default=0.0)
    reasoning_trace: list[str] = Field(default_factory=list)
```

### 2.9 LeadershipProfile (Agent Output)

```python
class Leader(BaseEntity):
    """A discovered company leader / decision maker."""
    name: str
    title: str
    department: Optional[str] = None
    linkedin_url: Optional[str] = None
    source_url: Optional[str] = None

class LeadershipProfile(BaseEntity):
    """Key decision makers at the target company."""
    leaders: list[Leader] = Field(default_factory=list)
    confidence_score: float = Field(ge=0.0, le=1.0, default=0.0)
    reasoning_trace: list[str] = Field(default_factory=list)
```

### 2.10 SalesPlaybook (Agent Output)

```python
class Priority(str, Enum):
    HIGH = "HIGH"
    MEDIUM = "MEDIUM"
    LOW = "LOW"

class RecommendedAction(BaseEntity):
    """A single recommended sales action."""
    action: str
    rationale: str
    priority: Priority = Priority.MEDIUM

class SalesPlaybook(BaseEntity):
    """AI-generated sales strategy for the account."""
    priority: Priority = Priority.MEDIUM
    recommended_actions: list[RecommendedAction] = Field(default_factory=list)
    talking_points: list[str] = Field(default_factory=list)
    outreach_template: Optional[str] = None
    confidence_score: float = Field(ge=0.0, le=1.0, default=0.0)
    reasoning_trace: list[str] = Field(default_factory=list)
```

### 2.11 AccountIntelligence (Aggregate Root)

```python
class AccountIntelligence(BaseEntity):
    """Complete AI-generated account intelligence — the final output."""
    company: CompanyProfile
    persona: Optional[PersonaInference] = None
    intent: Optional[IntentScore] = None
    tech_stack: Optional[TechStack] = None
    business_signals: Optional[BusinessSignals] = None
    leadership: Optional[LeadershipProfile] = None
    playbook: Optional[SalesPlaybook] = None
    ai_summary: str = ""
    analyzed_at: str = Field(default_factory=lambda: datetime.utcnow().isoformat())
    confidence_score: float = Field(ge=0.0, le=1.0, default=0.0)
    reasoning_trace: list[str] = Field(default_factory=list)
```

---

## 3. Agent Specifications

### 3.1 BaseAgent Contract

```python
class BaseAgent(ABC):
    agent_name: ClassVar[str]
    
    def __init__(self, llm: BaseChatModel, tools: dict[str, BaseTool]):
        self._llm = llm
        self._tools = tools
    
    @abstractmethod
    async def run(self, input: BaseEntity) -> BaseEntity: ...
    
    @abstractmethod
    def validate_input(self, input: BaseEntity) -> bool: ...
    
    @asynccontextmanager
    async def _timed_call(self, task_name: str): ...
```

### 3.2 Agent Details

| Agent | Input | Output | Tools Used | LLM Task |
|-------|-------|--------|-----------|----------|
| **IdentificationAgent** | VisitorSignal | CompanyInput | ip_lookup, web_search | Resolve ambiguous IP → company |
| **EnrichmentAgent** | CompanyInput | CompanyProfile | web_search, scraper (optional) | Uses Tavily search + optional web scraping (if domain available) + LLM synthesis. Does not rely on external enrichment APIs. |
| **PersonaAgent** | VisitorSignal + CompanyProfile | PersonaInference | — | Infer role from page behavior patterns |
| **IntentScorerAgent** | VisitorSignal | IntentScore | — | Score intent from behavioral signals |
| **TechStackAgent** | CompanyProfile | TechStack | scraper (optional) | Uses optional web scraping (if domain available) to detect technologies from HTML, combined with LLM inference fallback. |
| **SignalsAgent** | CompanyProfile | BusinessSignals | web_search | Find hiring/funding/expansion signals |
| **LeadershipAgent** | CompanyProfile | LeadershipProfile | web_search | Discover C-suite and VP-level leaders |
| **PlaybookAgent** | All prior outputs | SalesPlaybook | — | Synthesize strategy from all intelligence |
| **SummaryAgent** | All prior outputs | AccountIntelligence | — | Generate narrative summary, final assembly |

---

## 4. Graph State (LangGraph)

```python
class PipelineState(TypedDict):
    # Input (one of these will be set)
    visitor_signal: Optional[VisitorSignal]
    company_input: Optional[CompanyInput]
    
    # Stage 1 outputs
    identified_company: Optional[CompanyInput]
    company_profile: Optional[CompanyProfile]
    persona: Optional[PersonaInference]
    intent: Optional[IntentScore]
    
    # Stage 2 outputs
    tech_stack: Optional[TechStack]
    business_signals: Optional[BusinessSignals]
    leadership: Optional[LeadershipProfile]
    
    # Final outputs
    playbook: Optional[SalesPlaybook]
    intelligence: Optional[AccountIntelligence]
    
    # Metadata
    job_id: str
    errors: Annotated[list[str], operator.add]
    reasoning_trace: Annotated[list[str], operator.add]
```

### 4.1 Graph Edges

```
START → route_input
    │
    ├─ (has visitor_signal) → identification_node → parallel_stage_1
    ├─ (has company_input)  → parallel_stage_1
    │
parallel_stage_1 = [enrichment_node, intent_node, persona_node]
    │
    ▼
parallel_stage_2 = [tech_stack_node, signals_node, leadership_node]
    │
    ▼
playbook_node → summary_node → END
```

### 4.2 Conditional Routing

```python
def route_input(state: PipelineState) -> str:
    if state.get("visitor_signal"):
        return "identification_node"
    return "parallel_stage_1"
```

---

## 5. Tool Specifications

### 5.1 BaseTool Contract

```python
class BaseTool(ABC):
    tool_name: ClassVar[str]
    
    @abstractmethod
    async def call(self, **kwargs) -> Optional[dict]: ...
    
    # Built-in: retry with exponential backoff, timeout, caching
```

### 5.2 Tool Return Shapes

**IPLookupTool** returns:
```python
{
    "company_name": str | None,
    "country": str | None,
    "city": str | None,
    "isp": str,
    "org": str,
    "is_cloud_provider": bool,
    "confidence": float,
    "source_url": str,
    "fetched_at": str,
    "tool_name": "ip_lookup"
}
```

**WebSearchTool** returns:
```python
{
    "results": [
        {"title": str, "url": str, "snippet": str, "rank": int, "domain": str}
    ],
    "query": str,
    "source_url": str,
    "fetched_at": str,
    "tool_name": "web_search"
}
```

**ScraperTool** returns:
```python
{
    "url": str,
    "title": str | None,
    "meta_description": str | None,
    "visible_text": str,        # first 2000 chars
    "script_sources": list[str],
    "source_url": str,
    "fetched_at": str,
    "tool_name": "scraper"
}
```

> Used opportunistically by EnrichmentAgent and TechStackAgent when a domain is available.
> Scraping is best-effort and non-blocking; system gracefully falls back to LLM-based inference.

**EnrichmentAPITool** returns:
```python
{
    "company_name": str,
    "domain": str | None,
    "industry": str | None,
    "company_size": str | None,
    "headquarters": str | None,
    "description": str | None,
    "founded_year": int | None,
    "enrichment_source": str,    # "clearbit" | "apollo" | "llm_fallback"
    "source_url": str,
    "fetched_at": str,
    "tool_name": "enrichment_apis"
}
```

---

## 6. Controller Layer

### 6.1 AnalysisController

```python
class AnalysisController:
    """Bridges API routes and LangGraph workflow execution."""
    
    async def analyze_visitor(self, signal: VisitorSignal) -> str:
        """Creates job, dispatches graph, returns job_id."""
    
    async def analyze_company(self, input: CompanyInput) -> str:
        """Creates job, dispatches graph, returns job_id."""
    
    async def analyze_batch(self, inputs: list[CompanyInput]) -> tuple[str, list[str]]:
        """Creates batch + individual jobs, returns (batch_id, job_ids)."""
    
    async def get_job_status(self, job_id: str) -> JobStatus:
        """Returns current job state from JobStore."""
    
    async def get_account(self, account_id: str) -> Optional[AccountIntelligence]:
        """Returns completed account intelligence from AccountStore."""
    
    async def list_accounts(self, page: int, page_size: int) -> tuple[list, int]:
        """Returns paginated account list."""
```

---

## 7. Storage Layer

### 7.1 JobStore

```python
class JobStatus(str, Enum):
    PENDING = "PENDING"
    PROCESSING = "PROCESSING"
    COMPLETED = "COMPLETED"
    FAILED = "FAILED"

class JobRecord(BaseModel):
    job_id: str
    status: JobStatus
    progress: float = 0.0             # 0.0 to 1.0
    current_step: Optional[str] = None
    result_id: Optional[str] = None   # AccountIntelligence.id
    error: Optional[str] = None
    created_at: str
    updated_at: str

class InMemoryJobStore:
    async def create(self, job_id: str) -> JobRecord: ...
    async def update(self, job_id: str, **fields) -> JobRecord: ...
    async def get(self, job_id: str) -> Optional[JobRecord]: ...
```

### 7.2 AccountStore

```python
class InMemoryAccountStore:
    async def save(self, intelligence: AccountIntelligence) -> str: ...
    async def get(self, account_id: str) -> Optional[AccountIntelligence]: ...
    async def list(self, page: int, size: int) -> tuple[list[AccountIntelligence], int]: ...
```

---

## 8. Configuration (pydantic-settings)

```python
class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env")
    
    # LLM
    OPENAI_API_KEY: str
    MODEL_NAME: str = "gpt-4o-mini"
    
    # Tools
    TAVILY_API_KEY: str
    CLEARBIT_API_KEY: Optional[str] = None
    APOLLO_API_KEY: Optional[str] = None
    
    # Server
    HOST: str = "0.0.0.0"
    PORT: int = 8000
    CORS_ORIGINS: list[str] = ["http://localhost:3000"]
    
    # Tuning
    TOOL_TIMEOUT_SECONDS: int = 8
    TOOL_MAX_RETRIES: int = 3
    CACHE_TTL_SECONDS: int = 300
```

---

## 9. Error Handling Matrix

| Layer | Error Type | Handling Strategy |
|-------|-----------|------------------|
| **Tools** | HTTP timeout | Retry 3x with backoff → return None |
| **Tools** | API rate limit | Retry with backoff → return None |
| **Tools** | Parse error | Log + return None |
| **Agents** | LLM timeout | Catch → return degraded model (confidence=0.0) |
| **Agents** | Invalid LLM output | Retry parse up to 3x → degraded model |
| **Agents** | Tool returned None | Continue with partial data, note in reasoning_trace |
| **Graph** | Agent exception | Catch at node level → write error to state.errors |
| **Controller** | Graph failure | Mark job as FAILED with error message |
| **API** | Validation error | 422 (automatic via FastAPI/Pydantic) |
| **API** | Job not found | 404 with structured error response |
| **API** | Internal error | 500 with generic message (no traceback) |
| **Frontend** | API unreachable | Error state UI with retry button |
| **Frontend** | Job polling timeout | Show "taking longer than expected" + keep polling |

---

## 10. Dependency Graph

```
domain/ ← depends on: nothing
tools/ ← depends on: domain/, config
agents/ ← depends on: domain/, tools/ (injected)
graph/ ← depends on: domain/, agents/
storage/ ← depends on: domain/
controllers/ ← depends on: domain/, graph/, storage/
api/ ← depends on: domain/, controllers/, storage/
frontend/ ← depends on: api/ (via HTTP only)
```

No circular dependencies. Each layer only reaches "down" or "sideways" (never up).
