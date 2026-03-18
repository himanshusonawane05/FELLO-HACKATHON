# Extension Guide — Fello AI Account Intelligence System

> **Version**: 1.0  
> **Date**: 2026-03-18  
> **Audience**: Developers extending the system with new agents, tools, or pipeline stages  
> **Depends on**: [Implementation Status](./implementation-status.md), [LLD](./lld.md)

---

## 1. Adding a New Agent

Agents are stateless async workers that consume domain models and produce domain models. They live in `backend/agents/`.

### 1.1 Step-by-Step

**Step 1: Define the output domain model** (if new)

Add it to `backend/domain/`. All models must extend `BaseEntity` and be frozen:

```python
# backend/domain/competitor.py
from backend.domain.base import BaseEntity
from pydantic import Field

class CompetitorAnalysis(BaseEntity):
    """Competitor landscape for the target company."""
    competitors: list[str] = Field(default_factory=list)
    market_position: str = ""
    confidence_score: float = Field(ge=0.0, le=1.0, default=0.0)
    reasoning_trace: list[str] = Field(default_factory=list)
```

**Step 2: Create the agent class**

```python
# backend/agents/competitor.py
import logging
from typing import ClassVar

from backend.agents.base_agent import BaseAgent
from backend.core.llm_service import generate_json
from backend.domain.base import BaseEntity
from backend.domain.company import CompanyProfile
from backend.domain.competitor import CompetitorAnalysis

logger = logging.getLogger(__name__)


class _CompetitorLLMResponse(BaseEntity):
    competitors: list[str] = []
    market_position: str = ""
    confidence_score: float = 0.5


class CompetitorAgent(BaseAgent):
    """Identifies competitors using web search and LLM reasoning."""

    agent_name: ClassVar[str] = "competitor_agent"

    def validate_input(self, input: BaseEntity) -> bool:
        return isinstance(input, CompanyProfile)

    async def run(self, input: BaseEntity) -> CompetitorAnalysis:
        if not self.validate_input(input):
            return CompetitorAnalysis(confidence_score=0.0, reasoning_trace=["No company profile"])

        company: CompanyProfile = input  # type: ignore[assignment]

        # Skip for unknown companies
        if company.company_name.lower() in ("unknown", "unknown (private ip)"):
            return CompetitorAnalysis(confidence_score=0.0, reasoning_trace=["Unknown company"])

        logger.info("[%s] finding competitors for %s", self.agent_name, company.company_name)

        # Optional: use WebSearchTool for context
        search_context = await self._search_competitors(company)

        prompt = f"""Find the top competitors of "{company.company_name}" (industry: {company.industry or 'Unknown'}).

{f"Web search context: {search_context}" if search_context else "Use your general knowledge."}

Return JSON:
{{
  "competitors": ["CompanyA", "CompanyB", "CompanyC"],
  "market_position": "one sentence about their position",
  "confidence_score": 0.0-1.0
}}"""

        result = await generate_json(
            prompt=prompt,
            response_model=_CompetitorLLMResponse,
            temperature=0.1,
            max_tokens=1024,
        )

        if result:
            return CompetitorAnalysis(
                competitors=result.competitors,
                market_position=result.market_position,
                confidence_score=result.confidence_score,
                reasoning_trace=[f"LLM identified {len(result.competitors)} competitors"],
            )

        return CompetitorAnalysis(confidence_score=0.0, reasoning_trace=["LLM failed"])

    async def _search_competitors(self, company: CompanyProfile):
        try:
            from backend.tools.web_search import WebSearchTool
            tool = WebSearchTool()
            result = await tool.call(query=f"{company.company_name} competitors alternatives")
            if result:
                return "\n".join(r.get("snippet", "") for r in result.get("results", [])[:3])
        except Exception:
            pass
        return None
```

**Step 3: Add the output field to `PipelineState`**

```python
# backend/graph/state.py — add to PipelineState
from backend.domain.competitor import CompetitorAnalysis

class PipelineState(TypedDict):
    # ... existing fields ...
    competitor_analysis: Optional[CompetitorAnalysis]  # ADD THIS
```

**Step 4: Wire the agent into a graph node**

Add it to the appropriate stage in `backend/graph/nodes.py`. For a Stage 2 parallel agent:

```python
# In stage2_node, add to _build_agents() and asyncio.gather:

async def run_competitors():
    try:
        return await agents["competitor"].run(profile)
    except Exception as exc:
        logger.error("competitor error: %s", exc)
        return None

# Add to the gather call:
tech_result, signals_result, leadership_result, competitor_result = await asyncio.gather(
    run_tech(), run_signals(), run_leadership(), run_competitors()
)

# Add to return dict:
return {
    "tech_stack": tech_result,
    "business_signals": signals_result,
    "leadership": leadership_result,
    "competitor_analysis": competitor_result,  # ADD THIS
    ...
}
```

**Step 5: Register the agent in `_build_agents()`**

```python
# In backend/graph/nodes.py, _build_agents():
from backend.agents.competitor import CompetitorAgent

return {
    # ... existing agents ...
    "competitor": CompetitorAgent(llm=llm),
}
```

**Step 6: Include in `AccountIntelligence`** (if it should be in the final output)

```python
# backend/domain/intelligence.py
from backend.domain.competitor import CompetitorAnalysis

class AccountIntelligence(BaseEntity):
    # ... existing fields ...
    competitor_analysis: Optional[CompetitorAnalysis] = None  # ADD THIS
```

**Step 7: Update the API response schema**

```python
# backend/api/schemas/responses.py — add to AccountIntelligenceResponse
competitors: list[str] = Field(default_factory=list, example=["HubSpot", "Marketo"])
```

**Step 8: Update the frontend transformer**

```typescript
// frontend/lib/api.ts — in transformAccountResponse:
competitors: raw.competitor_analysis?.competitors ?? [],
```

---

## 2. Adding a New Tool

Tools are thin async wrappers around external APIs. They live in `backend/tools/`.

### 2.1 Step-by-Step

**Step 1: Create the tool class**

```python
# backend/tools/linkedin.py
import logging
from datetime import datetime
from typing import ClassVar, Optional

from backend.tools.base_tool import BaseTool, cached_call

logger = logging.getLogger(__name__)


class LinkedInTool(BaseTool):
    """LinkedIn profile lookup via RapidAPI or similar."""

    tool_name: ClassVar[str] = "linkedin_lookup"

    @cached_call(ttl=300)
    async def call(self, *, name: str, company: str) -> Optional[dict]:
        """Look up a LinkedIn profile.

        Returns:
            dict with keys: profile_url, title, company, source_url, fetched_at, tool_name
            None on any failure.
        """
        try:
            import httpx
            # Replace with actual LinkedIn API call
            async with httpx.AsyncClient(timeout=8.0) as client:
                resp = await client.get(
                    "https://api.example.com/linkedin",
                    params={"name": name, "company": company},
                    headers={"X-API-Key": "your-key"},
                )
                resp.raise_for_status()
                data = resp.json()

            return {
                "profile_url": data.get("url"),
                "title": data.get("title"),
                "company": data.get("company"),
                "source_url": data.get("url"),
                "fetched_at": datetime.utcnow().isoformat(),
                "tool_name": self.tool_name,
            }
        except Exception as exc:
            logger.warning("linkedin_lookup failed for %s at %s: %s", name, company, type(exc).__name__)
            return None
```

**Key rules for tools:**
- Always return `None` on failure — never raise
- Always include `source_url`, `fetched_at`, `tool_name` in the return dict
- Use `@cached_call(ttl=300)` for identical inputs
- Keep hard timeout at 8 seconds
- No LLM calls, no domain logic

**Step 2: Add API key to config** (if needed)

```python
# backend/config.py
LINKEDIN_API_KEY: Optional[str] = Field(default=None, description="LinkedIn API key")
```

**Step 3: Use the tool in an agent**

```python
# In any agent's run() method:
from backend.tools.linkedin import LinkedInTool

tool = LinkedInTool()
result = await tool.call(name="Marc Benioff", company="Salesforce")
if result:
    profile_url = result["profile_url"]
```

---

## 3. Modifying Pipeline Stages

### 3.1 Adding a New Sequential Stage

To add a stage between Stage 2 and the Playbook (e.g., a "Pricing Research" stage):

**Step 1: Create a new node function in `backend/graph/nodes.py`**

```python
async def pricing_node(state: PipelineState) -> dict:
    """Research pricing signals. Progress: 0.80 → 0.85."""
    job_id: str = state.get("job_id", "")
    await _update_progress(job_id, 0.80, "Researching pricing signals")

    agents = _build_agents()
    profile = state.get("company_profile")
    if not profile:
        return {"errors": ["pricing_node: no company_profile"], "reasoning_trace": []}

    try:
        result = await agents["pricing"].run(profile)
        return {"pricing_analysis": result, "errors": [], "reasoning_trace": ["Stage 2.5 — Pricing complete"]}
    except Exception as exc:
        logger.error("pricing_node error: %s", exc)
        return {"errors": [f"pricing_node: {exc}"], "reasoning_trace": []}
```

**Step 2: Register the node in `backend/graph/workflow.py`**

```python
from backend.graph.nodes import pricing_node  # add import

graph.add_node("pricing_node", pricing_node)
graph.add_edge("stage2_node", "pricing_node")    # was: stage2_node → playbook_node
graph.add_edge("pricing_node", "playbook_node")  # new edge
```

### 3.2 Changing Parallel Stage Composition

To add an agent to Stage 1 (runs in parallel with Enrichment, Persona, Intent):

```python
# In stage1_node in backend/graph/nodes.py:

async def run_new_agent():
    try:
        return await agents["new_agent"].run(company_input)
    except Exception as exc:
        logger.error("new_agent error: %s", exc)
        return None

enrichment_result, persona_result, intent_result, new_result = await asyncio.gather(
    run_enrichment(), run_persona(), run_intent(), run_new_agent()
)

return {
    "company_profile": enrichment_result,
    "persona": persona_result,
    "intent": intent_result,
    "new_output": new_result,  # must be a PipelineState key
    ...
}
```

---

## 4. Adding a New API Endpoint

### 4.1 Step-by-Step

**Step 1: Add request/response schemas**

```python
# backend/api/schemas/requests.py
class BatchAnalysisRequest(BaseModel):
    companies: list[CompanyAnalysisRequest] = Field(..., min_length=1, max_length=50)

# backend/api/schemas/responses.py
class BatchAcceptedResponse(BaseModel):
    batch_id: str = Field(example="batch-uuid")
    job_ids: list[str] = Field(example=["job-uuid-1", "job-uuid-2"])
    status: str = Field(example="PENDING")
```

**Step 2: Add the route**

```python
# backend/api/routes/analyze.py
@router.post(
    "/analyze/batch",
    response_model=BatchAcceptedResponse,
    status_code=202,
    summary="Submit batch company analysis",
)
async def analyze_batch(
    request: BatchAnalysisRequest,
    background_tasks: BackgroundTasks,
) -> BatchAcceptedResponse:
    batch_id, job_ids = await controller.analyze_batch(
        [CompanyInput(company_name=r.company_name, domain=r.domain) for r in request.companies],
        background_tasks,
    )
    return BatchAcceptedResponse(batch_id=batch_id, job_ids=job_ids, status="PENDING")
```

**Step 3: Add the controller method**

```python
# backend/controllers/analysis.py
async def analyze_batch(
    self, inputs: list[CompanyInput], background_tasks: BackgroundTasks
) -> tuple[str, list[str]]:
    batch_id = str(uuid4())
    job_ids = []
    for company_input in inputs:
        job_id = await self.analyze_company(company_input, background_tasks)
        job_ids.append(job_id)
    return batch_id, job_ids
```

**Step 4: Update the frontend API client**

```typescript
// frontend/lib/api.ts
async analyzeBatch(companies: CompanyAnalysisRequest[]): Promise<BatchAcceptedResponse> {
  const raw = await request<Record<string, unknown>>("/analyze/batch", {
    method: "POST",
    body: JSON.stringify({ companies }),
  });
  return {
    batch_id: raw.batch_id as string,
    job_ids: raw.job_ids as string[],
    status: (raw.status as string) ?? "PENDING",
  };
},
```

---

## 5. Replacing In-Memory Storage with a Database

The storage layer uses an abstract interface, making database migration straightforward.

### 5.1 Interface

Both stores implement the same abstract pattern:

```python
# backend/storage/job_store.py — InMemoryJobStore
async def create(self, job_id: str) -> JobRecord: ...
async def update(self, job_id: str, **fields) -> JobRecord: ...
async def get(self, job_id: str) -> Optional[JobRecord]: ...

# backend/storage/account_store.py — InMemoryAccountStore
async def save(self, intelligence: AccountIntelligence) -> str: ...
async def get(self, account_id: str) -> Optional[AccountIntelligence]: ...
async def list(self, page: int, size: int) -> tuple[list[AccountIntelligence], int]: ...
```

### 5.2 SQLite Migration Example

```python
# backend/storage/sqlite_account_store.py
import aiosqlite, json
from backend.domain.intelligence import AccountIntelligence

class SQLiteAccountStore:
    def __init__(self, db_path: str = "accounts.db"):
        self.db_path = db_path

    async def save(self, intelligence: AccountIntelligence) -> str:
        async with aiosqlite.connect(self.db_path) as db:
            await db.execute(
                "INSERT OR REPLACE INTO accounts (id, data) VALUES (?, ?)",
                (intelligence.id, intelligence.model_dump_json()),
            )
            await db.commit()
        return intelligence.id

    async def get(self, account_id: str) -> Optional[AccountIntelligence]:
        async with aiosqlite.connect(self.db_path) as db:
            async with db.execute("SELECT data FROM accounts WHERE id = ?", (account_id,)) as cur:
                row = await cur.fetchone()
                if row:
                    return AccountIntelligence.model_validate_json(row[0])
        return None
```

Then swap the import in `backend/controllers/analysis.py`:

```python
# from backend.storage.account_store import account_store
from backend.storage.sqlite_account_store import SQLiteAccountStore
account_store = SQLiteAccountStore()
```

---

## 6. Enabling the Scraper Tool in TechStackAgent

The `ScraperTool` is fully implemented but not currently used. To enable it:

```python
# backend/agents/tech_stack.py — replace LLM-only approach with scraper + LLM

async def run(self, input: BaseEntity) -> TechStack:
    company: CompanyProfile = input  # type: ignore[assignment]

    if not company.domain:
        return TechStack(confidence_score=0.0, reasoning_trace=["No domain available"])

    # Scrape the company website
    from backend.tools.scraper import ScraperTool
    scraper = ScraperTool()
    scraped = await scraper.call(url=f"https://{company.domain}")

    if scraped:
        script_sources = scraped.get("script_sources", [])
        visible_text = scraped.get("visible_text", "")
        # Pass to LLM for tech detection
        prompt = f"""Detect technologies from these script sources and page text:
Scripts: {script_sources[:20]}
Text excerpt: {visible_text[:500]}
Return JSON: {{"technologies": [{{"name": "...", "category": "CRM|ANALYTICS|...", "confidence_score": 0.0-1.0}}], "confidence_score": 0.0-1.0}}"""
    else:
        # Fall back to LLM knowledge
        prompt = f"""Infer tech stack for {company.company_name} ({company.industry})..."""
    
    # ... rest of LLM call
```

---

## 7. Layer Boundary Reference

Before adding code, verify it belongs in the right layer:

| You want to... | Put it in... |
|----------------|-------------|
| Add a new data shape | `backend/domain/` |
| Call an external API | `backend/tools/` |
| Use an LLM to reason | `backend/agents/` |
| Orchestrate agents | `backend/graph/nodes.py` |
| Handle HTTP request/response | `backend/api/routes/` |
| Bridge HTTP and graph | `backend/controllers/` |
| Display data | `frontend/components/` |
| Fetch data from backend | `frontend/lib/api.ts` |
| Manage async state | `frontend/hooks/` |

**Forbidden cross-layer imports:**
- `domain/` must not import from any other layer
- `tools/` must not import from `agents/` or `api/`
- `agents/` must not import from `api/` or `controllers/`
- `api/` must not import from `agents/` directly (use `controllers/`)
- Frontend components must not call `fetch()` directly (use `lib/api.ts`)
