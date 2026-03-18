# Skill: Database Design

> **Use when**: Designing storage schemas, modifying store interfaces, or planning data migration.

---

## When to Invoke

- Adding a new data entity that needs persistence
- Modifying an existing store's operations
- Planning future migration from in-memory to PostgreSQL
- Debugging data inconsistencies between stores

---

## Input Format

Provide:
1. **Entity**: What data needs to be stored
2. **Access patterns**: How will it be queried (by ID, by field, paginated list)
3. **Relationships**: How it relates to existing stored entities (JobStore, AccountStore)

---

## Process

1. **Read current schema** from `docs/database-schema.md`
2. **Design the storage structure**:
   - Define the dict key (usually a UUID string)
   - Define the value type (must be a Pydantic domain model)
   - Define all CRUD operations as `async def` methods
   - Add `asyncio.Lock` for write operations
3. **Map to API**: Show how stored data maps to API response fields
4. **Update docs**: Modify `docs/database-schema.md` with the new schema
5. **Future-proof**: Show the equivalent SQL schema for post-hackathon migration

---

## Output Format

```markdown
## New Store: [StoreName]

### Schema
| Field | Type | Constraints | Description |
[Field table]

### Operations
| Method | Signature | Complexity |
[Operations table]

### API Mapping
[Store field → API response field mapping]

### Future SQL
[CREATE TABLE statement]
```

---

## Constraints

- All stores use in-memory dicts for hackathon scope
- All methods MUST be `async def` (migration-ready)
- All writes MUST be protected by `asyncio.Lock`
- Stores accept/return domain models, never raw dicts
- Follow the singleton pattern from `.cursor/rules/09-storage-layer.mdc`
- No business logic in stores (pure persistence)
