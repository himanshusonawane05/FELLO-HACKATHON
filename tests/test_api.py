"""API integration tests — all endpoints tested via httpx.AsyncClient.

Uses the `async_client` fixture from conftest.py, which:
  1. Isolates job/account stores per test
  2. Mounts the FastAPI app directly (no network)
  3. Runs in an async event loop so asyncio.create_task() works
"""
import asyncio

import pytest


# ── Health endpoint ────────────────────────────────────────────────────────────

class TestHealth:
    async def test_health_returns_200(self, async_client):
        r = await async_client.get("/api/v1/health")
        assert r.status_code == 200

    async def test_health_body(self, async_client):
        r = await async_client.get("/api/v1/health")
        data = r.json()
        assert data["status"] == "ok"
        assert "version" in data


# ── POST /analyze/visitor ──────────────────────────────────────────────────────

class TestAnalyzeVisitor:
    @pytest.fixture()
    def visitor_payload(self):
        return {
            "visitor_id": "v-001",
            "ip_address": "34.201.114.42",
            "pages_visited": ["/pricing", "/ai-sales-agent", "/case-studies"],
            "time_on_site_seconds": 222,
            "visit_count": 3,
            "referral_source": "google",
            "device_type": "desktop",
            "location": "New York, USA",
        }

    async def test_returns_202(self, async_client, visitor_payload):
        r = await async_client.post("/api/v1/analyze/visitor", json=visitor_payload)
        assert r.status_code == 202

    async def test_response_has_job_id(self, async_client, visitor_payload):
        r = await async_client.post("/api/v1/analyze/visitor", json=visitor_payload)
        data = r.json()
        assert "job_id" in data
        assert len(data["job_id"]) == 36  # UUID

    async def test_response_analysis_type_visitor(self, async_client, visitor_payload):
        r = await async_client.post("/api/v1/analyze/visitor", json=visitor_payload)
        assert r.json()["analysis_type"] == "visitor"

    async def test_response_has_message(self, async_client, visitor_payload):
        r = await async_client.post("/api/v1/analyze/visitor", json=visitor_payload)
        assert r.json()["message"]

    async def test_response_has_poll_url(self, async_client, visitor_payload):
        r = await async_client.post("/api/v1/analyze/visitor", json=visitor_payload)
        data = r.json()
        assert data["poll_url"].startswith("/api/v1/jobs/")

    async def test_response_status_pending(self, async_client, visitor_payload):
        r = await async_client.post("/api/v1/analyze/visitor", json=visitor_payload)
        assert r.json()["status"] == "PENDING"

    async def test_response_has_created_at(self, async_client, visitor_payload):
        r = await async_client.post("/api/v1/analyze/visitor", json=visitor_payload)
        assert "created_at" in r.json()

    async def test_missing_visitor_id_returns_422(self, async_client):
        r = await async_client.post("/api/v1/analyze/visitor", json={
            "ip_address": "34.0.0.1",
            "pages_visited": ["/pricing"],
        })
        assert r.status_code == 422

    async def test_missing_ip_returns_422(self, async_client):
        r = await async_client.post("/api/v1/analyze/visitor", json={
            "visitor_id": "v-1",
            "pages_visited": ["/pricing"],
        })
        assert r.status_code == 422

    async def test_zero_visit_count_returns_422(self, async_client):
        r = await async_client.post("/api/v1/analyze/visitor", json={
            "visitor_id": "v-1",
            "ip_address": "34.0.0.1",
            "pages_visited": ["/pricing"],
            "visit_count": 0,
        })
        assert r.status_code == 422

    async def test_negative_time_on_site_returns_422(self, async_client):
        r = await async_client.post("/api/v1/analyze/visitor", json={
            "visitor_id": "v-1",
            "ip_address": "34.0.0.1",
            "pages_visited": ["/pricing"],
            "time_on_site_seconds": -10,
        })
        assert r.status_code == 422

    async def test_minimal_payload_accepted(self, async_client):
        """Only visitor_id and ip_address are required."""
        r = await async_client.post("/api/v1/analyze/visitor", json={
            "visitor_id": "v-min",
            "ip_address": "34.0.0.1",
        })
        assert r.status_code == 202


# ── POST /analyze/company ──────────────────────────────────────────────────────

class TestAnalyzeCompany:
    async def test_returns_202(self, async_client):
        r = await async_client.post("/api/v1/analyze/company", json={
            "company_name": "BrightPath Lending",
            "domain": "brightpathlending.com",
        })
        assert r.status_code == 202

    async def test_analysis_type_company(self, async_client):
        r = await async_client.post("/api/v1/analyze/company", json={
            "company_name": "BrightPath Lending",
        })
        assert r.json()["analysis_type"] == "company"

    async def test_response_fields_present(self, async_client):
        r = await async_client.post("/api/v1/analyze/company", json={
            "company_name": "BrightPath Lending",
        })
        data = r.json()
        for field in ("job_id", "status", "analysis_type", "message", "poll_url", "created_at"):
            assert field in data, f"Missing field: {field}"

    async def test_missing_company_name_returns_422(self, async_client):
        r = await async_client.post("/api/v1/analyze/company", json={})
        assert r.status_code == 422

    async def test_company_name_too_long_returns_422(self, async_client):
        r = await async_client.post("/api/v1/analyze/company", json={
            "company_name": "X" * 201
        })
        assert r.status_code == 422

    async def test_domain_optional(self, async_client):
        r = await async_client.post("/api/v1/analyze/company", json={
            "company_name": "Test Corp",
        })
        assert r.status_code == 202


# ── POST /analyze/batch ────────────────────────────────────────────────────────

class TestAnalyzeBatch:
    async def test_returns_202(self, async_client):
        r = await async_client.post("/api/v1/analyze/batch", json={
            "companies": [
                {"company_name": "BrightPath Lending"},
                {"company_name": "Summit Realty Group"},
            ]
        })
        assert r.status_code == 202

    async def test_job_ids_count_matches_input(self, async_client):
        r = await async_client.post("/api/v1/analyze/batch", json={
            "companies": [
                {"company_name": "Co A"},
                {"company_name": "Co B"},
                {"company_name": "Co C"},
            ]
        })
        data = r.json()
        assert len(data["job_ids"]) == 3
        assert data["total"] == 3

    async def test_batch_id_present(self, async_client):
        r = await async_client.post("/api/v1/analyze/batch", json={
            "companies": [{"company_name": "Test Co"}]
        })
        assert "batch_id" in r.json()

    async def test_analysis_type_batch(self, async_client):
        r = await async_client.post("/api/v1/analyze/batch", json={
            "companies": [{"company_name": "Test Co"}]
        })
        assert r.json()["analysis_type"] == "batch"

    async def test_empty_companies_returns_422(self, async_client):
        r = await async_client.post("/api/v1/analyze/batch", json={"companies": []})
        assert r.status_code == 422

    async def test_too_many_companies_returns_422(self, async_client):
        companies = [{"company_name": f"Co {i}"} for i in range(21)]
        r = await async_client.post("/api/v1/analyze/batch", json={"companies": companies})
        assert r.status_code == 422

    async def test_all_job_ids_are_unique(self, async_client):
        r = await async_client.post("/api/v1/analyze/batch", json={
            "companies": [{"company_name": f"Co {i}"} for i in range(5)]
        })
        job_ids = r.json()["job_ids"]
        assert len(set(job_ids)) == 5


# ── GET /jobs/{job_id} ─────────────────────────────────────────────────────────

class TestGetJob:
    async def test_unknown_job_returns_404(self, async_client):
        r = await async_client.get("/api/v1/jobs/00000000-0000-0000-0000-000000000000")
        assert r.status_code == 404

    async def test_job_exists_after_analyze(self, async_client):
        post = await async_client.post("/api/v1/analyze/company", json={
            "company_name": "Test Corp"
        })
        job_id = post.json()["job_id"]
        r = await async_client.get(f"/api/v1/jobs/{job_id}")
        assert r.status_code == 200

    async def test_job_has_required_fields(self, async_client):
        post = await async_client.post("/api/v1/analyze/company", json={
            "company_name": "Test Corp"
        })
        job_id = post.json()["job_id"]
        r = await async_client.get(f"/api/v1/jobs/{job_id}")
        data = r.json()
        for field in ("job_id", "status", "progress", "created_at", "updated_at"):
            assert field in data, f"Missing field: {field}"

    async def test_job_progress_between_0_and_1(self, async_client):
        post = await async_client.post("/api/v1/analyze/company", json={
            "company_name": "Test Corp"
        })
        job_id = post.json()["job_id"]
        r = await async_client.get(f"/api/v1/jobs/{job_id}")
        assert 0.0 <= r.json()["progress"] <= 1.0

    async def test_404_error_structure(self, async_client):
        r = await async_client.get("/api/v1/jobs/nonexistent-id")
        assert r.status_code == 404


# ── GET /accounts ──────────────────────────────────────────────────────────────

class TestListAccounts:
    async def test_empty_returns_200(self, async_client):
        r = await async_client.get("/api/v1/accounts")
        assert r.status_code == 200

    async def test_empty_store_returns_zero_total(self, async_client):
        r = await async_client.get("/api/v1/accounts")
        data = r.json()
        assert data["total"] == 0
        assert data["accounts"] == []

    async def test_response_has_pagination_fields(self, async_client):
        r = await async_client.get("/api/v1/accounts")
        data = r.json()
        for field in ("accounts", "total", "page", "page_size"):
            assert field in data

    async def test_accounts_appear_after_pipeline_completes(self, async_client):
        await async_client.post("/api/v1/analyze/company", json={"company_name": "Test Corp"})
        # Let background pipeline finish
        await asyncio.sleep(0.3)
        r = await async_client.get("/api/v1/accounts")
        assert r.json()["total"] >= 1

    async def test_account_summary_fields(self, async_client):
        await async_client.post("/api/v1/analyze/company", json={"company_name": "Test Corp"})
        await asyncio.sleep(0.3)
        r = await async_client.get("/api/v1/accounts")
        account = r.json()["accounts"][0]
        for field in ("account_id", "company_name", "confidence_score", "analyzed_at"):
            assert field in account

    async def test_pagination_page_size(self, async_client):
        r = await async_client.get("/api/v1/accounts?page=1&page_size=5")
        assert r.json()["page_size"] == 5


# ── GET /accounts/{account_id} ─────────────────────────────────────────────────

class TestGetAccount:
    async def test_unknown_account_returns_404(self, async_client):
        r = await async_client.get("/api/v1/accounts/nonexistent-id")
        assert r.status_code == 404

    async def test_full_flow_company(self, async_client):
        """POST company → poll until complete → GET account."""
        post = await async_client.post("/api/v1/analyze/company", json={
            "company_name": "BrightPath Lending",
            "domain": "brightpathlending.com",
        })
        job_id = post.json()["job_id"]

        # Wait for pipeline to complete
        result_id = None
        for _ in range(10):
            await asyncio.sleep(0.1)
            job_r = await async_client.get(f"/api/v1/jobs/{job_id}")
            job_data = job_r.json()
            if job_data["status"] == "COMPLETED":
                result_id = job_data["result_id"]
                break

        assert result_id, "Job did not complete in time"
        account_r = await async_client.get(f"/api/v1/accounts/{result_id}")
        assert account_r.status_code == 200

    async def test_account_has_required_top_level_fields(self, async_client):
        post = await async_client.post("/api/v1/analyze/company", json={"company_name": "Acme Mortgage"})
        job_id = post.json()["job_id"]
        result_id = None
        for _ in range(10):
            await asyncio.sleep(0.1)
            job_data = (await async_client.get(f"/api/v1/jobs/{job_id}")).json()
            if job_data["status"] == "COMPLETED":
                result_id = job_data["result_id"]
                break

        assert result_id
        data = (await async_client.get(f"/api/v1/accounts/{result_id}")).json()
        for field in ("account_id", "company", "ai_summary", "analyzed_at", "confidence_score"):
            assert field in data, f"Missing field: {field}"

    async def test_company_sub_object_populated(self, async_client):
        post = await async_client.post("/api/v1/analyze/company", json={"company_name": "BrightPath Lending"})
        job_id = post.json()["job_id"]
        result_id = None
        for _ in range(10):
            await asyncio.sleep(0.1)
            job_data = (await async_client.get(f"/api/v1/jobs/{job_id}")).json()
            if job_data["status"] == "COMPLETED":
                result_id = job_data["result_id"]
                break

        data = (await async_client.get(f"/api/v1/accounts/{result_id}")).json()
        company = data["company"]
        assert company["company_name"] == "BrightPath Lending"
        assert company["industry"]
        assert company["confidence_score"] > 0

    async def test_visitor_flow_has_persona_and_intent(self, async_client):
        post = await async_client.post("/api/v1/analyze/visitor", json={
            "visitor_id": "v-001",
            "ip_address": "34.201.114.42",
            "pages_visited": ["/pricing", "/demo"],
            "time_on_site_seconds": 180,
            "visit_count": 2,
        })
        job_id = post.json()["job_id"]
        result_id = None
        for _ in range(15):
            await asyncio.sleep(0.1)
            job_data = (await async_client.get(f"/api/v1/jobs/{job_id}")).json()
            if job_data["status"] == "COMPLETED":
                result_id = job_data["result_id"]
                break

        assert result_id, "Visitor job did not complete"
        data = (await async_client.get(f"/api/v1/accounts/{result_id}")).json()
        assert data["persona"] is not None
        assert data["intent"] is not None
        assert data["intent"]["intent_score"] > 0

    async def test_tech_stack_in_response(self, async_client):
        post = await async_client.post("/api/v1/analyze/company", json={"company_name": "BrightPath Lending"})
        job_id = post.json()["job_id"]
        result_id = None
        for _ in range(10):
            await asyncio.sleep(0.1)
            job_data = (await async_client.get(f"/api/v1/jobs/{job_id}")).json()
            if job_data["status"] == "COMPLETED":
                result_id = job_data["result_id"]
                break

        data = (await async_client.get(f"/api/v1/accounts/{result_id}")).json()
        assert data["tech_stack"] is not None
        assert len(data["tech_stack"]["technologies"]) > 0

    async def test_leadership_in_response(self, async_client):
        post = await async_client.post("/api/v1/analyze/company", json={"company_name": "BrightPath Lending"})
        job_id = post.json()["job_id"]
        result_id = None
        for _ in range(10):
            await asyncio.sleep(0.1)
            job_data = (await async_client.get(f"/api/v1/jobs/{job_id}")).json()
            if job_data["status"] == "COMPLETED":
                result_id = job_data["result_id"]
                break

        data = (await async_client.get(f"/api/v1/accounts/{result_id}")).json()
        assert data["leadership"] is not None
        assert len(data["leadership"]["leaders"]) > 0

    async def test_playbook_priority_valid_value(self, async_client):
        post = await async_client.post("/api/v1/analyze/company", json={"company_name": "BrightPath Lending"})
        job_id = post.json()["job_id"]
        result_id = None
        for _ in range(10):
            await asyncio.sleep(0.1)
            job_data = (await async_client.get(f"/api/v1/jobs/{job_id}")).json()
            if job_data["status"] == "COMPLETED":
                result_id = job_data["result_id"]
                break

        data = (await async_client.get(f"/api/v1/accounts/{result_id}")).json()
        assert data["playbook"]["priority"] in ("HIGH", "MEDIUM", "LOW")
