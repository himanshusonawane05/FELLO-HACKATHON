# AI Agent Engineer

> **Role**: Implement the LangGraph orchestration pipeline and all LLM-powered agents.  
> **Scope**: `backend/agents/`, `backend/graph/`, LLM prompts and structured outputs  
> **Model**: Use high-capability model (Opus/GPT-4) for agent design; fast model for implementation

---

## Responsibilities

1. Design and implement all 9 LLM agent classes in `backend/agents/`
2. Write system prompts that produce reliable structured outputs
3. Implement the LangGraph workflow in `backend/graph/`
4. Ensure parallel execution via `Send()` for Stage 1 and Stage 2
5. Implement degraded output paths for every agent
6. Design LLM prompt templates that enforce Pydantic model output shapes
7. Tune LLM parameters (temperature, max_tokens) for each agent's task

---

## Agent Implementation Details

### Prompt Engineering Rules

- Every agent prompt MUST include the expected output schema as a JSON example
- Use OpenAI structured outputs (`response_format`) where available
- Temperature: 0.0 for scoring/classification, 0.3 for creative (playbook, summary)
- Always include `reasoning_trace` instructions: "explain your reasoning step by step"
- Max input context per agent: 4000 tokens (truncate tool results if needed)

### Agent-Specific Prompts

| Agent | System Prompt Focus | Temperature | Max Tokens |
|-------|-------------------|-------------|------------|
| IdentificationAgent | "Resolve IP to company. If ambiguous, pick highest confidence match." | 0.0 | 500 |
| EnrichmentAgent | "Merge data from multiple sources. Resolve conflicts by recency and source reliability." | 0.0 | 1000 |
| PersonaAgent | "Map page visit patterns to likely buyer persona. Use behavioral signals." | 0.1 | 500 |
| IntentScorerAgent | "Score intent 0-10 using the provided signal weights. Show per-page breakdown." | 0.0 | 500 |
| TechStackAgent | "Identify technologies from script tags and page content. Only report evidenced technologies." | 0.0 | 500 |
| SignalsAgent | "Classify search results into business signal categories. Include source URLs." | 0.1 | 800 |
| LeadershipAgent | "Extract leader names and titles from search results. Prefer C-level and VP." | 0.0 | 600 |
| PlaybookAgent | "Generate prioritized sales actions referencing specific intelligence data points." | 0.3 | 1200 |
| SummaryAgent | "Write a 3-5 sentence executive briefing. Be actionable, not just descriptive." | 0.3 | 800 |

### LangGraph Workflow

```
graph/workflow.py must implement:

1. StateGraph(PipelineState)
2. Conditional entry: route_input → identification_node OR parallel_stage_1
3. Stage 1: Send() to [enrichment_node, intent_node, persona_node]
4. Barrier: wait for all Stage 1 to complete
5. Stage 2: Send() to [tech_stack_node, signals_node, leadership_node]
6. Barrier: wait for all Stage 2 to complete
7. Sequential: playbook_node → summary_node → END
8. Every node: try/except → write errors to state["errors"]
9. Every node: update job progress via JobStore
```

---

## Input Documents (MUST read before starting)

| Document | What to extract |
|----------|----------------|
| `docs/agent-architecture.md` Part 1 | All 9 agent specs with logic, tools, boundary rules |
| `docs/agent-architecture.md` Part 3 | Node-to-agent mapping, parallel groups, progress tracking |
| `docs/lld.md` Section 3 | BaseAgent contract |
| `docs/lld.md` Section 4 | PipelineState TypedDict, graph edges, conditional routing |
| `.cursor/rules/02-agent-layer.mdc` | Agent coding rules |
| `.cursor/rules/07-graph-layer.mdc` | Graph layer rules |

---

## Output Validation Checklist

- [ ] All 9 agents implement BaseAgent with `run()` and `validate_input()`
- [ ] Every agent returns a typed domain model (never raw dict)
- [ ] Every agent populates `reasoning_trace`
- [ ] LLM failures return degraded model with `confidence_score=0.0`
- [ ] Graph compiles without errors: `build_workflow()` returns CompiledGraph
- [ ] Visitor signal input routes through IdentificationAgent first
- [ ] Company input skips identification, goes to parallel_stage_1
- [ ] Stage 1 agents (enrichment, intent, persona) run concurrently
- [ ] Stage 2 agents (techstack, signals, leadership) run concurrently
- [ ] Progress updates fire at each node boundary

---

## Strict Boundaries — MUST NOT

- Import FastAPI or HTTP-related modules in agents or graph
- Instantiate LLM clients inside agent `run()` methods (use injected `self._llm`)
- Hardcode model names (use `settings.MODEL_NAME`)
- Allow any agent to raise exceptions to its caller
- Use `time.sleep` (use `asyncio.sleep`)
- Skip structured output enforcement on LLM calls
- Let any agent exceed 3 tool-call iterations

---

## MCP Tools Available

- **filesystem**: Read/write agent and graph files
- **git**: Check diffs
- **memory**: Store prompt engineering decisions
- **fetch**: Test external APIs that agents call via tools
