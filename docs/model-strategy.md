# Model Strategy — Cost & Performance Optimization

> **Version**: 1.0  
> **Date**: 2026-03-18  
> **Goal**: Minimize token cost while maximizing code quality across all Cursor agent tasks

---

## 1. Model Tiers

### Tier 1: High-Capability (use sparingly)

**Models**: Claude Opus, GPT-4, Claude 3.5 Sonnet (thinking mode)

**Cost profile**: ~$15–75/M tokens — 5–10x more expensive than Tier 2

**Use ONLY for**:
- System architecture design and trade-off analysis
- Complex debugging across multiple files
- LLM prompt engineering (agent system prompts)
- Final summary/review passes requiring deep reasoning
- Resolving ambiguous requirements or conflicts between agents

### Tier 2: Fast/Low-Cost (default for everything else)

**Models**: Claude Sonnet, GPT-4o-mini, Claude Haiku

**Cost profile**: ~$0.25–3/M tokens

**Use for**:
- All code implementation (backend + frontend)
- Test generation
- File creation and editing
- Documentation writing
- Configuration and integration tasks
- Data transformation and repetitive patterns

---

## 2. Agent → Model → Task Mapping

| Cursor Agent | Default Model | Tier 1 Override Conditions |
|-------------|---------------|---------------------------|
| **backend-engineer** | Tier 2 (Fast) | Tier 1 only if debugging a multi-file issue |
| **frontend-engineer** | Tier 2 (Fast) | Tier 1 only if designing complex state management |
| **ai-agent-engineer** | Tier 2 (Fast) for code, **Tier 1 for prompt design** | System prompt writing always uses Tier 1 |
| **qa-engineer** | Tier 2 (Fast) | Never needs Tier 1 |
| **integration-engineer** | Tier 2 (Fast) | Never needs Tier 1 |

---

## 3. Task-Level Model Assignments

### Backend Engineer Tasks

| Task | Model | Rationale |
|------|-------|-----------|
| Domain models (`backend/domain/`) | Tier 2 | Formulaic: copy schemas from LLD |
| Tool wrappers (`backend/tools/`) | Tier 2 | Pattern-based: HTTP call + error handling |
| Storage (`backend/storage/`) | Tier 2 | Simple dict operations |
| API schemas (`backend/api/schemas/`) | Tier 2 | Direct translation from api-contracts.md |
| API routes (`backend/api/routes/`) | Tier 2 | Thin delegation, pattern-based |
| Controllers (`backend/controllers/`) | Tier 2 | Orchestration logic is well-defined in docs |
| Config + main.py | Tier 2 | Boilerplate |

### AI Agent Engineer Tasks

| Task | Model | Rationale |
|------|-------|-----------|
| BaseAgent ABC | Tier 2 | Simple abstract class |
| Agent class structure | Tier 2 | Follows BaseAgent pattern |
| **System prompts for LLM** | **Tier 1** | Requires nuanced reasoning about output quality |
| **LangGraph workflow design** | **Tier 1** | Complex state management + parallel execution |
| Node wrapper functions | Tier 2 | Simple try/except + delegation |
| PipelineState TypedDict | Tier 2 | Copy from LLD |

### Frontend Engineer Tasks

| Task | Model | Rationale |
|------|-------|-----------|
| Project scaffold (Next.js) | Tier 2 | CLI commands + config |
| TypeScript interfaces | Tier 2 | Copy from api-contracts.md |
| API client (`lib/api.ts`) | Tier 2 | Fetch wrapper pattern |
| Mock data | Tier 2 | Copy JSON from api-contracts.md examples |
| Hooks (polling, analysis) | Tier 2 | Well-defined state machine from integration.md |
| UI components | Tier 2 | shadcn/ui + Tailwind patterns |
| Page composition | Tier 2 | Wiring existing components |

### QA Engineer Tasks

| Task | Model | Rationale |
|------|-------|-----------|
| Domain model tests | Tier 2 | Repetitive pattern: valid/invalid/edge |
| Tool tests | Tier 2 | Mock + assert None pattern |
| Agent tests | Tier 2 | Mock LLM + assert degraded output |
| API contract tests | Tier 2 | Assert response shapes |
| Error path tests | Tier 2 | Predefined scenarios from LLD |

### Integration Engineer Tasks

| Task | Model | Rationale |
|------|-------|-----------|
| Environment configuration | Tier 2 | File editing |
| CORS setup | Tier 2 | Single config change |
| Demo scripts | Tier 2 | Curl/Python scripts |
| README writing | Tier 2 | Template-based |
| Deployment configuration | Tier 2 | Standard Railway/Vercel patterns |

---

## 4. Cost Estimation

### Per-Session Token Budget

| Agent | Est. Input Tokens | Est. Output Tokens | Model | Est. Cost |
|-------|------------------|-------------------|-------|-----------|
| backend-engineer (full build) | ~80K | ~40K | Tier 2 | ~$0.30 |
| frontend-engineer (full build) | ~60K | ~35K | Tier 2 | ~$0.25 |
| ai-agent-engineer (prompts) | ~20K | ~10K | Tier 1 | ~$2.00 |
| ai-agent-engineer (code) | ~40K | ~25K | Tier 2 | ~$0.15 |
| qa-engineer (full tests) | ~50K | ~30K | Tier 2 | ~$0.20 |
| integration-engineer | ~30K | ~15K | Tier 2 | ~$0.10 |
| **Total estimated** | | | | **~$3.00** |

### Cost Savings vs. All-Tier-1

| Strategy | Estimated Cost |
|----------|---------------|
| All tasks on Tier 1 | ~$25–40 |
| Optimized (this strategy) | ~$3–5 |
| **Savings** | **~85–90%** |

---

## 5. Quality Safeguards

Using Tier 2 for implementation doesn't sacrifice quality because:

1. **Architecture docs constrain the solution space** — every model/endpoint/agent is fully specified
2. **Cursor rules enforce coding standards** — layer boundaries, type hints, error handling
3. **Agent definitions provide step-by-step instructions** — implementation order is predetermined
4. **Contract tests catch mismatches** — automated validation against api-contracts.md

Tier 1 is reserved for tasks where the solution space is open (prompt design, debugging, architecture decisions).

---

## 6. Model Selection Decision Tree

```
Is this a NEW architectural decision?
  └─ YES → Tier 1
  └─ NO → Is this a complex debugging task spanning 3+ files?
           └─ YES → Tier 1
           └─ NO → Is this writing an LLM system prompt?
                    └─ YES → Tier 1
                    └─ NO → Tier 2 (default)
```
