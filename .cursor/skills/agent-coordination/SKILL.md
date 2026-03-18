# Skill: Agent Coordination

> **Use when**: Orchestrating multiple Cursor agents, resolving conflicts between agents, or planning parallel execution strategies.

---

## When to Invoke

- Planning which agents should run in parallel vs. sequentially
- Resolving a conflict where two agents produced incompatible outputs
- Deciding which Cursor model to use for a specific task
- Coordinating a handoff between backend-engineer and frontend-engineer agents

---

## Input Format

Provide:
1. **Task**: What needs to be accomplished
2. **Agents involved**: Which agents from `.cursor/agents/` are needed
3. **Dependencies**: What must complete before this task can start

---

## Coordination Rules

### Parallel Execution (Safe)
These agent pairs have NO shared files and CAN run simultaneously:

| Agent A | Agent B | Why safe |
|---------|---------|----------|
| backend-engineer | frontend-engineer | Separate directories, contract-driven |
| qa-engineer (writing tests) | backend-engineer (writing code) | Separate directories |
| qa-engineer (writing tests) | frontend-engineer (writing code) | Separate directories |

### Sequential Execution (Required)
These tasks MUST run in order:

```
1. system-design decisions  →  BEFORE  →  any implementation
2. domain models (backend)  →  BEFORE  →  agents, tools, graph
3. API schemas (backend)    →  BEFORE  →  frontend types
4. backend running          →  BEFORE  →  integration testing
5. frontend running         →  BEFORE  →  integration testing
6. all implementation       →  BEFORE  →  QA validation
```

### Conflict Resolution Protocol

When agents produce conflicting outputs:
1. Check `docs/api-contracts.md` — the contract is ALWAYS right
2. Check `.cursor/rules/` for the relevant layer — rules override agent judgment
3. If still ambiguous, escalate to system-architect for a design decision
4. Document the resolution in MCP memory for future reference

---

## Model Assignment Strategy

| Task Type | Recommended Model | Rationale |
|-----------|------------------|-----------|
| Architecture design | High-capability (Opus/GPT-4) | Complex reasoning, trade-off analysis |
| Agent prompt engineering | High-capability (Opus/GPT-4) | Nuanced prompt design |
| Code implementation | Fast (Sonnet/GPT-4o-mini) | Formulaic, rule-following, cost-efficient |
| Test generation | Fast (Sonnet/GPT-4o-mini) | Repetitive, pattern-based |
| UI component building | Fast (Sonnet/GPT-4o-mini) | Component patterns are well-defined |
| Integration/config | Fast (Sonnet/GPT-4o-mini) | Straightforward file operations |
| Bug debugging | High-capability (Opus/GPT-4) | Multi-file reasoning needed |

---

## Output Format

```markdown
## Execution Plan

### Phase [N]: [Name]
- **Agents**: [list]
- **Can parallelize**: yes/no
- **Blocking dependencies**: [list]
- **Expected duration**: [estimate]
- **Model**: [fast/capable]

### Handoff: [From] → [To]
- **Artifact**: [what is passed]
- **Validation**: [how to verify correctness]
```

---

## Constraints

- Never let two agents modify the same file simultaneously
- API contracts doc is the single source of truth for all agent communication
- Every agent output must be directly consumable by downstream agents
- Use MCP memory to persist coordination decisions across sessions
