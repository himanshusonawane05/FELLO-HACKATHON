#!/usr/bin/env python3
"""End-to-end API validation script for Fello AI Account Intelligence.

Validates the full flow against a running backend:
  1. Health check
  2. POST /analyze/visitor  → job created
  3. POST /analyze/company  → job created
  4. GET  /jobs/{id}        → poll until complete
  5. GET  /accounts/{id}    → full intelligence returned
  6. GET  /accounts         → list with pagination
  7. Unknown IP handling    → low confidence, no fabricated data
  8. Private IP handling    → Unknown company returned

Usage:
  python e2e-tests/validate_api.py [--base-url http://localhost:8000/api/v1]

Exit codes:
  0 — all checks passed
  1 — one or more checks failed
"""
from __future__ import annotations

import argparse
import asyncio
import json
import sys
import time
from typing import Any

# Ensure Windows console can display output (avoid UnicodeEncodeError)
if sys.platform == "win32":
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    except AttributeError:
        pass

import httpx

BASE_URL = "http://localhost:8000/api/v1"
TIMEOUT = 120.0  # seconds to wait for pipeline completion
POLL_INTERVAL = 1.0  # seconds between polls

# ── ANSI colours ──────────────────────────────────────────────────────────────

GREEN = "\033[92m"
RED = "\033[91m"
YELLOW = "\033[93m"
CYAN = "\033[96m"
RESET = "\033[0m"
BOLD = "\033[1m"


def ok(msg: str) -> None:
    print(f"  {GREEN}[PASS]{RESET} {msg}")


def fail(msg: str) -> None:
    print(f"  {RED}[FAIL]{RESET} {msg}")


def info(msg: str) -> None:
    print(f"  {CYAN}[...]{RESET} {msg}")


def section(title: str) -> None:
    print(f"\n{BOLD}{title}{RESET}")
    print("-" * 60)


# ── Helpers ───────────────────────────────────────────────────────────────────

failures: list[str] = []


def check(condition: bool, msg: str, detail: str = "") -> bool:
    if condition:
        ok(msg)
    else:
        fail(msg + (f" - {detail}" if detail else ""))
        failures.append(msg)
    return condition


async def poll_job(client: httpx.AsyncClient, job_id: str) -> dict[str, Any]:
    """Poll GET /jobs/{job_id} until COMPLETED or FAILED, or timeout."""
    deadline = time.monotonic() + TIMEOUT
    while time.monotonic() < deadline:
        r = await client.get(f"/jobs/{job_id}")
        data = r.json()
        status = data.get("status", "UNKNOWN")
        progress = data.get("progress", 0)
        step = data.get("current_step", "")
        info(f"  Job {job_id[:8]}... status={status} progress={progress:.0%} step={step!r}")
        if status in ("COMPLETED", "FAILED"):
            return data
        await asyncio.sleep(POLL_INTERVAL)
    return {"status": "TIMEOUT", "job_id": job_id}


# ── Test cases ────────────────────────────────────────────────────────────────

async def test_health(client: httpx.AsyncClient) -> None:
    section("1. Health Check")
    r = await client.get("/health")
    check(r.status_code == 200, "GET /health returns 200")
    data = r.json()
    check(data.get("status") == "ok", "Health status is 'ok'", str(data))
    check("version" in data, "Health response has 'version' field")


async def test_company_flow(client: httpx.AsyncClient) -> str | None:
    """Returns account_id if successful, else None."""
    section("2. Company Analysis Flow  (POST /analyze/company -> poll -> GET /accounts/{id})")

    r = await client.post("/analyze/company", json={
        "company_name": "Stripe",
        "domain": "stripe.com",
    })
    check(r.status_code == 202, "POST /analyze/company returns 202")
    data = r.json()
    check("job_id" in data, "Response has job_id")
    check(data.get("status") == "PENDING", "Initial status is PENDING")
    check(data.get("analysis_type") == "company", "analysis_type is 'company'")
    check(data.get("poll_url", "").startswith("/api/v1/jobs/"), "poll_url is correct")

    job_id = data.get("job_id")
    if not job_id:
        fail("Cannot poll — no job_id returned")
        return None

    info(f"Polling job {job_id[:8]}... (timeout={TIMEOUT}s)")
    job_data = await poll_job(client, job_id)

    status = job_data.get("status")
    check(status == "COMPLETED", f"Job completed (status={status})")

    result_id = job_data.get("result_id")
    if not result_id:
        fail("No result_id in completed job")
        return None

    r2 = await client.get(f"/accounts/{result_id}")
    check(r2.status_code == 200, "GET /accounts/{id} returns 200")
    account = r2.json()

    check("account_id" in account, "Account has account_id")
    check("company" in account, "Account has company sub-object")
    check("ai_summary" in account, "Account has ai_summary")
    check("confidence_score" in account, "Account has confidence_score")
    check("analyzed_at" in account, "Account has analyzed_at")
    check("reasoning_trace" in account, "Account has reasoning_trace")

    company = account.get("company", {})
    check(company.get("company_name") == "Stripe", "company_name is 'Stripe'")
    check(bool(company.get("industry")), "industry is populated")
    check(company.get("confidence_score", 0) > 0, "company confidence_score > 0")

    check(account.get("tech_stack") is not None, "tech_stack is present")
    check(account.get("playbook") is not None, "playbook is present")
    check(
        account.get("playbook", {}).get("priority") in ("HIGH", "MEDIUM", "LOW"),
        "playbook priority is valid"
    )

    ai_summary = account.get("ai_summary", "")
    check(len(ai_summary) > 50, "ai_summary is non-trivial", f"len={len(ai_summary)}")
    check("Stripe" in ai_summary, "ai_summary mentions company name")

    return result_id


async def test_visitor_flow(client: httpx.AsyncClient) -> None:
    section("3. Visitor Signal Flow  (POST /analyze/visitor -> poll -> GET /accounts/{id})")

    r = await client.post("/analyze/visitor", json={
        "visitor_id": "e2e-test-visitor-001",
        "ip_address": "34.201.114.42",
        "pages_visited": ["/pricing", "/ai-sales-agent", "/case-studies"],
        "time_on_site_seconds": 222,
        "visit_count": 3,
        "referral_source": "google",
        "device_type": "desktop",
    })
    check(r.status_code == 202, "POST /analyze/visitor returns 202")
    data = r.json()
    check("job_id" in data, "Response has job_id")
    check(data.get("analysis_type") == "visitor", "analysis_type is 'visitor'")

    job_id = data.get("job_id")
    if not job_id:
        fail("Cannot poll — no job_id returned")
        return

    info(f"Polling job {job_id[:8]}... (timeout={TIMEOUT}s)")
    job_data = await poll_job(client, job_id)

    status = job_data.get("status")
    check(status == "COMPLETED", f"Visitor job completed (status={status})")

    result_id = job_data.get("result_id")
    if not result_id:
        fail("No result_id in completed visitor job")
        return

    r2 = await client.get(f"/accounts/{result_id}")
    check(r2.status_code == 200, "GET /accounts/{id} returns 200 for visitor result")
    account = r2.json()

    check(account.get("persona") is not None, "Visitor result has persona")
    check(account.get("intent") is not None, "Visitor result has intent")
    intent = account.get("intent", {})
    check(intent.get("intent_score", 0) >= 0, "intent_score is non-negative")
    check(
        intent.get("intent_stage") in ("AWARENESS", "CONSIDERATION", "EVALUATION", "PURCHASE"),
        "intent_stage is valid"
    )


async def test_unknown_ip_handling(client: httpx.AsyncClient) -> None:
    section("4. Unknown/Private IP Handling  (must NOT fabricate company data)")

    for ip, label in [("192.168.1.1", "private RFC1918"), ("10.0.0.1", "private RFC1918 10.x")]:
        r = await client.post("/analyze/visitor", json={
            "visitor_id": f"e2e-test-{ip.replace('.', '-')}",
            "ip_address": ip,
            "pages_visited": ["/pricing"],
            "visit_count": 1,
        })
        check(r.status_code == 202, f"POST /analyze/visitor accepts {label} IP ({ip})")
        job_id = r.json().get("job_id")
        if not job_id:
            continue

        job_data = await poll_job(client, job_id)
        status = job_data.get("status")
        check(status == "COMPLETED", f"Job for {label} IP completed (status={status})")

        result_id = job_data.get("result_id")
        if not result_id:
            continue

        account = (await client.get(f"/accounts/{result_id}")).json()
        company = account.get("company", {})
        company_name = company.get("company_name", "")
        confidence = company.get("confidence_score", 1.0)

        check(
            "Unknown" in company_name,
            f"{label} IP returns 'Unknown' company (got {company_name!r})"
        )
        check(
            confidence < 0.3,
            f"{label} IP has low confidence (got {confidence:.2f})",
            "should be < 0.3"
        )


async def test_list_accounts(client: httpx.AsyncClient) -> None:
    section("5. List Accounts  (GET /accounts)")

    r = await client.get("/accounts")
    check(r.status_code == 200, "GET /accounts returns 200")
    data = r.json()
    check("accounts" in data, "Response has 'accounts' list")
    check("total" in data, "Response has 'total' count")
    check("page" in data, "Response has 'page'")
    check("page_size" in data, "Response has 'page_size'")

    r2 = await client.get("/accounts?page=1&page_size=5")
    check(r2.status_code == 200, "GET /accounts with pagination returns 200")
    check(r2.json().get("page_size") == 5, "page_size respected")


async def test_validation_errors(client: httpx.AsyncClient) -> None:
    section("6. Input Validation  (422 errors)")

    r = await client.post("/analyze/visitor", json={
        "ip_address": "1.2.3.4",
        "pages_visited": ["/pricing"],
    })
    check(r.status_code == 422, "Missing visitor_id returns 422")

    r = await client.post("/analyze/visitor", json={
        "visitor_id": "v-1",
        "ip_address": "1.2.3.4",
        "visit_count": 0,
    })
    check(r.status_code == 422, "visit_count=0 returns 422")

    r = await client.post("/analyze/company", json={})
    check(r.status_code == 422, "Missing company_name returns 422")

    r = await client.post("/analyze/company", json={"company_name": "X" * 201})
    check(r.status_code == 422, "company_name too long returns 422")

    r = await client.get("/jobs/nonexistent-job-id")
    check(r.status_code == 404, "Unknown job_id returns 404")

    r = await client.get("/accounts/nonexistent-account-id")
    check(r.status_code == 404, "Unknown account_id returns 404")


# ── Main ──────────────────────────────────────────────────────────────────────

async def main(base_url: str) -> int:
    print(f"\n{BOLD}Fello AI — End-to-End API Validation{RESET}")
    print(f"Target: {CYAN}{base_url}{RESET}")
    print("=" * 60)

    async with httpx.AsyncClient(base_url=base_url, timeout=30.0) as client:
        await test_health(client)
        await test_validation_errors(client)
        await test_list_accounts(client)
        await test_company_flow(client)
        await test_visitor_flow(client)
        await test_unknown_ip_handling(client)

    section("Summary")
    total_checks = len(failures) + sum(1 for _ in range(0))  # approximate
    if failures:
        print(f"\n{RED}{BOLD}FAILED — {len(failures)} check(s) failed:{RESET}")
        for f in failures:
            print(f"  {RED}[X]{RESET} {f}")
        return 1
    else:
        print(f"\n{GREEN}{BOLD}ALL CHECKS PASSED{RESET}")
        return 0


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Fello AI E2E API Validator")
    parser.add_argument(
        "--base-url",
        default=BASE_URL,
        help=f"Backend API base URL (default: {BASE_URL})",
    )
    args = parser.parse_args()
    sys.exit(asyncio.run(main(args.base_url)))
