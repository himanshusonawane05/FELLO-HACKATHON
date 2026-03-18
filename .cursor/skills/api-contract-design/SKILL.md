# Skill: API Contract Design

> **Use when**: Adding, modifying, or validating API endpoints. The contracts doc is the single source of truth.

---

## When to Invoke

- Adding a new API endpoint
- Modifying an existing endpoint's request or response shape
- Frontend reports a schema mismatch
- Validating that backend implementation matches contracts
- Creating TypeScript interfaces from API responses

---

## Input Format

Provide:
1. **Action**: Add / Modify / Validate
2. **Endpoint**: HTTP method + path (e.g., `POST /api/v1/analyze/visitor`)
3. **Context**: Why the change is needed

---

## Process

1. **Read current contracts** from `docs/api-contracts.md`
2. **For additions**: Design request/response schemas following existing patterns:
   - Request: Required fields, optional fields, validation constraints
   - Response: Status code, typed response body with example JSON
   - Error cases: Which HTTP errors can this endpoint return
3. **For modifications**: Update the contract doc, then list all files that need updating:
   - `backend/api/schemas/requests.py` or `responses.py`
   - `frontend/types/intelligence.ts`
   - Any tests that assert response shapes
4. **For validation**: Compare backend response against contract, report mismatches

---

## Output Format

For new/modified endpoints:

```markdown
### [METHOD] `/api/v1/[path]`

**Request Body:**
[JSON example with all fields]

| Field | Type | Required | Constraints |
[Field table]

**Response: `[status code]`**
[JSON example]

| Field | Type | Nullable | Description |
[Field table]

**Errors:** [list of error codes]

**Files to update:**
- [ ] docs/api-contracts.md
- [ ] backend/api/schemas/...
- [ ] frontend/types/intelligence.ts
- [ ] tests/test_api/...
```

---

## Constraints

- `docs/api-contracts.md` is the SINGLE SOURCE OF TRUTH — update it first, always
- Every field MUST have an explicit type and nullability
- Every response MUST include a JSON example
- Request validation errors return 422 (automatic via FastAPI)
- Long-running operations return 202 + job_id (never block)
- All timestamps in ISO 8601 format
- All IDs in UUID format
- TypeScript interfaces in api-contracts.md Section 4 MUST match JSON schemas exactly
