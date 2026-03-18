# Skill: Documentation Writer

> **Use when**: Creating or updating project documentation, README, architecture docs, or inline documentation.

---

## When to Invoke

- Creating README.md for the project
- Updating architecture docs after implementation changes
- Writing inline docstrings for public APIs
- Creating deployment guides or setup instructions

---

## Input Format

Provide:
1. **Document type**: README / architecture / API / setup guide / docstring
2. **Audience**: Developer (teammate) / Evaluator (hackathon judges) / User (end user)
3. **Context**: What changed or what needs documenting

---

## Process

1. **Read existing docs** in `docs/` to maintain consistency
2. **Read the source code** to ensure accuracy
3. **Write documentation** following the format guidelines below

---

## Document Standards

### README.md Structure
```markdown
# Project Name
[1-2 sentence description]

## Architecture
[Link to HLD diagram or inline ASCII]

## Quick Start
### Prerequisites
### Backend Setup
### Frontend Setup

## Demo
[How to run the demo, sample inputs, expected outputs]

## Tech Stack
[Table of technologies with rationale]

## Project Structure
[Directory tree with descriptions]

## API Reference
[Link to api-contracts.md or inline summary]

## Team
[Credits]
```

### Architecture Doc Updates
- Always update `Version` and `Date` in frontmatter
- Add a changelog entry at the bottom if modifying existing docs
- Cross-reference other docs using relative markdown links

### Docstring Format (Python)
```python
async def analyze_visitor(self, signal: VisitorSignal) -> str:
    """Create an analysis job for a visitor signal.

    Validates the signal, creates a job record, dispatches the
    LangGraph workflow as a background task, and returns immediately.

    Args:
        signal: Validated visitor signal with IP and behavioral data.

    Returns:
        The job_id (UUID string) for polling via GET /jobs/{id}.

    Raises:
        Never raises — marks job as FAILED on internal error.
    """
```

---

## Output Format

- Complete document ready to write to disk
- Markdown formatted with proper headings, tables, code blocks
- All links relative (e.g., `[HLD](./docs/hld.md)`)
- No placeholder text — every section must have real content

---

## Constraints

- Documentation must be accurate to current implementation (read code first)
- README must be understandable by hackathon judges in 2 minutes
- No marketing language — be technical and precise
- All code examples must be copy-pasteable and working
- Include both local dev and deployment instructions in README
- Keep docs/api-contracts.md as the single source of truth for API shapes
