# Skill: Test Generation

> **Use when**: Writing tests for any system component. Generates pytest tests for backend and Jest/Vitest tests for frontend.

---

## When to Invoke

- After implementing a new module (write tests immediately)
- When a bug is found (write regression test first)
- When validating API contract conformance
- When testing error handling paths

---

## Input Format

Provide:
1. **Target**: File or module to test (e.g., `backend/domain/company.py`)
2. **Test type**: unit / integration / contract / error-path
3. **Reference**: Relevant docs (LLD for models, api-contracts for endpoints)

---

## Process

1. **Read the source file** to understand the API surface
2. **Read the relevant doc** for expected behavior
3. **Generate tests** following the patterns below

---

## Backend Test Patterns (pytest)

### Domain Model Test
```python
def test_company_profile_valid():
    profile = CompanyProfile(company_name="Acme", confidence_score=0.85)
    assert profile.company_name == "Acme"
    assert profile.confidence_score == 0.85

def test_company_profile_frozen():
    profile = CompanyProfile(company_name="Acme")
    with pytest.raises(ValidationError):
        profile.company_name = "Other"

def test_company_profile_score_bounds():
    with pytest.raises(ValidationError):
        CompanyProfile(company_name="Acme", confidence_score=1.5)
```

### Tool Test (mock external API)
```python
@pytest.mark.asyncio
async def test_ip_lookup_returns_none_on_timeout(mock_httpx):
    mock_httpx.side_effect = httpx.TimeoutException("timeout")
    tool = IPLookupTool()
    result = await tool.call(ip_address="1.2.3.4")
    assert result is None

@pytest.mark.asyncio
async def test_ip_lookup_cloud_provider(mock_httpx):
    mock_httpx.return_value = {"org": "Amazon AWS"}
    tool = IPLookupTool()
    result = await tool.call(ip_address="1.2.3.4")
    assert result["company_name"] is None
```

### Agent Test (mock LLM)
```python
@pytest.mark.asyncio
async def test_enrichment_degraded_on_llm_failure(mock_llm):
    mock_llm.side_effect = Exception("LLM timeout")
    agent = EnrichmentAgent(llm=mock_llm, tools={})
    result = await agent.run(CompanyInput(company_name="Test"))
    assert isinstance(result, CompanyProfile)
    assert result.confidence_score == 0.0
```

### API Contract Test
```python
@pytest.mark.asyncio
async def test_analyze_company_returns_202(client):
    response = await client.post("/api/v1/analyze/company", json={"company_name": "Test"})
    assert response.status_code == 202
    data = response.json()
    assert "job_id" in data
    assert data["status"] == "PENDING"
    assert data["analysis_type"] == "company"
    assert "poll_url" in data
```

---

## Frontend Test Patterns (if applicable)

### Component Test
```typescript
test("IntentMeter renders green for score > 7", () => {
  render(<IntentMeter score={8.4} />);
  expect(screen.getByRole("progressbar")).toHaveClass("bg-green");
});

test("PersonaBadge renders muted for confidence < 50%", () => {
  render(<PersonaBadge role="Manager" confidence={0.3} />);
  expect(screen.getByText("Manager")).toHaveClass("text-muted");
});
```

---

## Output Format

For each test file, produce:
- File path (e.g., `tests/test_domain/test_company.py`)
- Complete test code with imports, fixtures, and assertions
- At minimum: 1 happy path + 1 edge case + 1 error case per function

---

## Constraints

- All external calls MUST be mocked (no network in tests)
- All LLM calls MUST be mocked (no API keys in tests)
- Use `pytest.mark.asyncio` for all async tests
- Use `httpx.AsyncClient` with `app` for API tests (no real server needed)
- Test data should come from examples in docs (realistic, not random)
- Every test must be deterministic (no random, no time-dependent)
