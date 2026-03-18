# Skill: System Design

> **Use when**: Designing new modules, evaluating architecture decisions, creating HLD/LLD, or restructuring existing components.

---

## When to Invoke

- User asks to design a new system component
- User asks to evaluate trade-offs between architectural approaches
- User needs to add a new layer, service, or module to the system
- User asks "how should I structure X?" or "what's the best pattern for Y?"

---

## Input Format

Provide:
1. **Problem statement**: What capability is needed
2. **Constraints**: Performance, cost, time, team size
3. **Existing context**: Reference `docs/hld.md` and `docs/lld.md` for current architecture

---

## Process

1. **Read existing architecture docs** (`docs/hld.md`, `docs/lld.md`) to understand current state
2. **Identify which layers are affected** using the layer boundary map from rule `06-global.mdc`
3. **Design the solution** respecting:
   - Layer boundaries (domain → tools → agents → graph → controllers → api → frontend)
   - No circular dependencies
   - Each module has a single responsibility
   - All communication through typed interfaces (Pydantic models)
4. **Define data flow** with clear input/output at each step
5. **Document decisions** with rationale in `docs/` directory

---

## Output Format

Produce a structured design document containing:

```markdown
## Problem
[1-2 sentences]

## Proposed Solution
[Architecture description with ASCII diagram if applicable]

## Affected Layers
[List of layers that need changes]

## Data Models
[New or modified Pydantic models]

## API Changes
[New or modified endpoints — update api-contracts.md if needed]

## Implementation Order
[Numbered steps respecting dependency order]

## Trade-offs
[What was considered and why this approach was chosen]
```

---

## Constraints

- Every design MUST respect the layer boundaries in `.cursor/rules/06-global.mdc`
- Every new module MUST have a corresponding `.cursor/rules/` file
- Every API change MUST be reflected in `docs/api-contracts.md`
- Prefer simplicity over cleverness — this is a 48-hour hackathon
- In-memory storage only (no new database dependencies)
