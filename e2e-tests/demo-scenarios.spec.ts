/**
 * Demo scenario tests — validate the four key scenarios for demo stability.
 *
 * These tests verify end-to-end behavior for each intent tier and ensure the
 * full pipeline produces the correct visual output for a live demo.
 */
import { expect, test } from "@playwright/test";
import {
  ELEMENT_TIMEOUT_MS,
  PIPELINE_TIMEOUT_MS,
  ROUTES,
} from "./helpers/constants";

// ── Scenario 1: Maximum intent — Stripe (9.1 / PURCHASE) ─────────────────────

test.describe("Scenario: Maximum intent — Stripe 9.1", () => {
  test.beforeEach(async ({ page }) => {
    await page.goto(ROUTES.stripe);
  });

  test("shows 9.1 intent score", async ({ page }) => {
    const score = page.getByTestId("intent-score");
    await expect(score).toBeVisible({ timeout: ELEMENT_TIMEOUT_MS });
    await expect(score).toHaveText("9.1");
  });

  test("intent score renders in green (score > 7)", async ({ page }) => {
    await expect(page.getByTestId("intent-score")).toHaveCSS(
      "color",
      "rgb(0, 255, 136)",
      { timeout: ELEMENT_TIMEOUT_MS }
    );
  });

  test("intent stage is PURCHASE", async ({ page }) => {
    await expect(
      page.getByTestId("intent-meter").getByText("PURCHASE")
    ).toBeVisible({ timeout: ELEMENT_TIMEOUT_MS });
  });

  test("shows HIGH priority badge", async ({ page }) => {
    await expect(page.getByText("HIGH PRIORITY")).toBeVisible({
      timeout: ELEMENT_TIMEOUT_MS,
    });
  });

  test("playbook priority badge is HIGH", async ({ page }) => {
    await expect(page.getByTestId("playbook-priority")).toHaveText("HIGH", {
      timeout: ELEMENT_TIMEOUT_MS,
    });
  });

  test("ai summary contains PURCHASE stage language", async ({ page }) => {
    await expect(
      page.getByTestId("ai-summary").getByText(/they are ready to buy/i)
    ).toBeVisible({ timeout: ELEMENT_TIMEOUT_MS });
  });

  test("leadership shows Patrick Collison", async ({ page }) => {
    await expect(page.getByText("Patrick Collison")).toBeVisible({
      timeout: ELEMENT_TIMEOUT_MS,
    });
  });

  test("signals feed shows billing product launch", async ({ page }) => {
    await expect(
      page.getByText("Stripe Billing v3 GA release")
    ).toBeVisible({ timeout: ELEMENT_TIMEOUT_MS });
  });

  test("full pipeline run produces Stripe result (via company form)", async ({ page }) => {
    await page.goto(ROUTES.dashboard);
    await page.getByTestId("company-name-input").fill("Stripe");
    await page.getByTestId("submit-btn").click();

    await expect(page.getByTestId("pipeline-progress")).toBeVisible({
      timeout: ELEMENT_TIMEOUT_MS,
    });

    await page.waitForURL(/\/account\/mock-acc-stripe/, {
      timeout: PIPELINE_TIMEOUT_MS,
    });

    await expect(page.getByTestId("intent-score")).toHaveText("9.1", {
      timeout: ELEMENT_TIMEOUT_MS,
    });
  });
});

// ── Scenario 2: High intent — Salesforce (8.7 / EVALUATION) ──────────────────

test.describe("Scenario: High intent — Salesforce 8.7", () => {
  test.beforeEach(async ({ page }) => {
    await page.goto(ROUTES.salesforce);
  });

  test("shows 8.7 intent score", async ({ page }) => {
    await expect(page.getByTestId("intent-score")).toHaveText("8.7", {
      timeout: ELEMENT_TIMEOUT_MS,
    });
  });

  test("intent score is green", async ({ page }) => {
    await expect(page.getByTestId("intent-score")).toHaveCSS(
      "color",
      "rgb(0, 255, 136)",
      { timeout: ELEMENT_TIMEOUT_MS }
    );
  });

  test("intent stage is EVALUATION", async ({ page }) => {
    await expect(
      page.getByTestId("intent-meter").getByText("EVALUATION")
    ).toBeVisible({ timeout: ELEMENT_TIMEOUT_MS });
  });

  test("talking points are present in playbook", async ({ page }) => {
    await expect(
      page.getByText(/natively with Salesforce workflows/i)
    ).toBeVisible({ timeout: ELEMENT_TIMEOUT_MS });
  });

  test("recommended action to Lead with AI ROI is shown", async ({ page }) => {
    await expect(
      page.getByTestId("sales-playbook").getByText("Lead with AI ROI case study")
    ).toBeVisible({ timeout: ELEMENT_TIMEOUT_MS });
  });

  test("persona badge shows VP confidence > 50% (high contrast style)", async ({
    page,
  }) => {
    const badge = page.getByTestId("persona-badge");
    await expect(badge).toBeVisible({ timeout: ELEMENT_TIMEOUT_MS });
    await expect(badge.getByText(/VP of Sales Operations/i)).toBeVisible();
    // High-confidence persona (78%) should render with accent border
    await expect(badge).toHaveClass(/border-accent/);
  });
});

// ── Scenario 3: Medium intent — HubSpot (6.4 / CONSIDERATION) ────────────────

test.describe("Scenario: Medium intent — HubSpot 6.4", () => {
  test.beforeEach(async ({ page }) => {
    await page.goto(ROUTES.hubspot);
  });

  test("shows 6.4 intent score", async ({ page }) => {
    await expect(page.getByTestId("intent-score")).toHaveText("6.4", {
      timeout: ELEMENT_TIMEOUT_MS,
    });
  });

  test("intent score is amber (4 ≤ score ≤ 7)", async ({ page }) => {
    await expect(page.getByTestId("intent-score")).toHaveCSS(
      "color",
      "rgb(245, 158, 11)",
      { timeout: ELEMENT_TIMEOUT_MS }
    );
  });

  test("intent stage is CONSIDERATION", async ({ page }) => {
    await expect(
      page.getByTestId("intent-meter").getByText("CONSIDERATION")
    ).toBeVisible({ timeout: ELEMENT_TIMEOUT_MS });
  });

  test("playbook priority badge is MEDIUM", async ({ page }) => {
    await expect(page.getByTestId("playbook-priority")).toHaveText("MEDIUM", {
      timeout: ELEMENT_TIMEOUT_MS,
    });
  });

  test("recommended action is nurture-focused (not direct push)", async ({ page }) => {
    await expect(
      page.getByTestId("sales-playbook").getByText(/nurture with RevOps thought leadership/i)
    ).toBeVisible({ timeout: ELEMENT_TIMEOUT_MS });
  });

  test("persona confidence < 100% shown correctly in badge", async ({ page }) => {
    // 65% confidence — should show "65%" scoped to the persona badge only
    await expect(
      page.getByTestId("persona-badge").getByText(/65%/)
    ).toBeVisible({ timeout: ELEMENT_TIMEOUT_MS });
  });

  test("company description mentions inbound marketing", async ({ page }) => {
    await expect(
      page.getByText(/inbound marketing methodology/i)
    ).toBeVisible({ timeout: ELEMENT_TIMEOUT_MS });
  });
});

// ── Scenario 4: Unknown company — default mock (7.2 / EVALUATION) ─────────────

test.describe("Scenario: Unknown company — default mock", () => {
  test("submitting an unknown company name returns a result", async ({ page }) => {
    await page.goto(ROUTES.dashboard);
    await page.getByTestId("company-name-input").fill("AcmeTestCorp");
    await page.getByTestId("submit-btn").click();

    await expect(page.getByTestId("pipeline-progress")).toBeVisible({
      timeout: ELEMENT_TIMEOUT_MS,
    });

    await page.waitForURL(/\/account\/mock-acc-acmetestcorp/, {
      timeout: PIPELINE_TIMEOUT_MS,
    });

    await expect(
      page.getByRole("heading", { name: "AcmeTestCorp", level: 1 })
    ).toBeVisible({ timeout: ELEMENT_TIMEOUT_MS });
  });

  test("unknown company result shows 7.2 intent score", async ({ page }) => {
    await page.goto(ROUTES.dashboard);
    await page.getByTestId("company-name-input").fill("AcmeTestCorp");
    await page.getByTestId("submit-btn").click();
    await page.waitForURL(/\/account\/mock-acc-acmetestcorp/, {
      timeout: PIPELINE_TIMEOUT_MS,
    });

    await expect(page.getByTestId("intent-score")).toHaveText("7.2", {
      timeout: ELEMENT_TIMEOUT_MS,
    });
  });

  test("unknown company result has all output sections", async ({ page }) => {
    await page.goto(ROUTES.dashboard);
    await page.getByTestId("company-name-input").fill("AcmeTestCorp");
    await page.getByTestId("submit-btn").click();
    await page.waitForURL(/\/account\/mock-acc-acmetestcorp/, {
      timeout: PIPELINE_TIMEOUT_MS,
    });

    const sections = [
      "company-profile",
      "intent-meter",
      "ai-summary",
      "tech-stack",
      "signals-feed",
      "leadership-list",
      "sales-playbook",
    ];

    for (const testId of sections) {
      await expect(page.getByTestId(testId)).toBeVisible({
        timeout: ELEMENT_TIMEOUT_MS,
      });
    }
  });
});

// ── Pipeline step progression ─────────────────────────────────────────────────

test.describe("Pipeline step progression during demo", () => {
  test("pipeline step messages change over time", async ({ page }) => {
    await page.goto(ROUTES.dashboard);
    await page.getByTestId("company-name-input").fill("Salesforce");
    await page.getByTestId("submit-btn").click();

    const stepLabel = page.getByTestId("pipeline-step");
    await expect(stepLabel).toBeVisible({ timeout: ELEMENT_TIMEOUT_MS });

    // Capture initial step
    const firstStep = await stepLabel.textContent();

    // Wait 3 seconds — step should have advanced
    await page.waitForTimeout(3000);
    const laterStep = await stepLabel.textContent();

    // Steps should differ (pipeline has advanced)
    expect(firstStep).not.toEqual(laterStep);
  });

  test("pipeline completes with 100% after 7.5 seconds", async ({ page }) => {
    await page.goto(ROUTES.dashboard);
    await page.getByTestId("company-name-input").fill("Salesforce");
    await page.getByTestId("submit-btn").click();

    // Once complete, page navigates — that is the implicit assertion
    await page.waitForURL(/\/account\//, { timeout: PIPELINE_TIMEOUT_MS });
    await expect(page.getByTestId("company-profile")).toBeVisible({
      timeout: ELEMENT_TIMEOUT_MS,
    });
  });

  test("after pipeline, dashboard re-adds the account to recent list", async ({
    page,
  }) => {
    await page.goto(ROUTES.dashboard);
    await page.getByTestId("company-name-input").fill("Salesforce");
    await page.getByTestId("submit-btn").click();
    await page.waitForURL(/\/account\/mock-acc-salesforce/, {
      timeout: PIPELINE_TIMEOUT_MS,
    });

    // Go back to dashboard — the analyzed account should appear in the list
    await page.getByText("← Dashboard").click();
    await expect(page).toHaveURL(ROUTES.dashboard);

    await expect(
      page.getByTestId("account-card").filter({ hasText: "Salesforce" }).first()
    ).toBeVisible({ timeout: ELEMENT_TIMEOUT_MS });
  });
});
