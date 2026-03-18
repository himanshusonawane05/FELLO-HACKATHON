import { expect, test } from "@playwright/test";
import {
  ELEMENT_TIMEOUT_MS,
  HIGH_INTENT_VISITOR,
  LOW_INTENT_VISITOR,
  PIPELINE_TIMEOUT_MS,
  ROUTES,
} from "./helpers/constants";

// ── Helpers ───────────────────────────────────────────────────────────────────

async function openVisitorForm(
  page: Parameters<Parameters<typeof test>[1]>[0]
): Promise<void> {
  await page.goto(ROUTES.dashboard);
  await page.getByTestId("mode-visitor").click();
  // Wait for the visitor form to render
  await expect(page.getByTestId("visitor-id-input")).toBeVisible({
    timeout: ELEMENT_TIMEOUT_MS,
  });
}

async function fillVisitorForm(
  page: Parameters<Parameters<typeof test>[1]>[0],
  opts: {
    visitorId: string;
    pages?: string;
    timeSliderValue?: number;
    visitSliderValue?: number;
    referral?: string;
  }
): Promise<void> {
  await page.getByTestId("visitor-id-input").fill(opts.visitorId);

  if (opts.pages) {
    await page.getByPlaceholder("/pricing, /enterprise, /case-studies, /demo").fill(opts.pages);
  }

  if (opts.timeSliderValue !== undefined) {
    await page.getByTestId("time-on-site-slider").fill(String(opts.timeSliderValue));
  }

  if (opts.visitSliderValue !== undefined) {
    await page.getByTestId("visit-count-slider").fill(String(opts.visitSliderValue));
  }

  if (opts.referral) {
    await page.getByRole("button", { name: opts.referral }).click();
  }
}

// ── Form rendering ────────────────────────────────────────────────────────────

test.describe("Visitor form rendering", () => {
  test.beforeEach(async ({ page }) => {
    await openVisitorForm(page);
  });

  test("visitor ID input is visible", async ({ page }) => {
    await expect(page.getByTestId("visitor-id-input")).toBeVisible();
  });

  test("IP address input is visible", async ({ page }) => {
    await expect(
      page.getByPlaceholder("203.0.113.42 (default used)")
    ).toBeVisible();
  });

  test("pages visited input is visible", async ({ page }) => {
    await expect(
      page.getByPlaceholder("/pricing, /enterprise, /case-studies, /demo")
    ).toBeVisible();
  });

  test("time on site slider is visible with range 10–600", async ({ page }) => {
    const slider = page.getByTestId("time-on-site-slider");
    await expect(slider).toBeVisible();
    await expect(slider).toHaveAttribute("min", "10");
    await expect(slider).toHaveAttribute("max", "600");
  });

  test("visit count slider is visible with range 1–20", async ({ page }) => {
    const slider = page.getByTestId("visit-count-slider");
    await expect(slider).toBeVisible();
    await expect(slider).toHaveAttribute("min", "1");
    await expect(slider).toHaveAttribute("max", "20");
  });

  test("device type toggles are all present", async ({ page }) => {
    await expect(page.getByRole("button", { name: "desktop" })).toBeVisible();
    await expect(page.getByRole("button", { name: "mobile" })).toBeVisible();
    await expect(page.getByRole("button", { name: "tablet" })).toBeVisible();
  });

  test("referral source pills are all present", async ({ page }) => {
    const sources = ["direct", "organic search", "paid search", "social", "email", "referral"];
    for (const source of sources) {
      await expect(page.getByRole("button", { name: source })).toBeVisible();
    }
  });

  test("submit button is present in visitor mode", async ({ page }) => {
    await expect(page.getByTestId("submit-btn")).toBeVisible();
  });
});

// ── Scenario builder interactions ─────────────────────────────────────────────

test.describe("Scenario builder interactions", () => {
  test.beforeEach(async ({ page }) => {
    await openVisitorForm(page);
  });

  test("time on site label updates when slider moves", async ({ page }) => {
    await page.getByTestId("time-on-site-slider").fill("300");
    // Label should show 5m 0s
    await expect(page.getByText("5m 0s")).toBeVisible();
  });

  test("visit count label updates when slider moves", async ({ page }) => {
    await page.getByTestId("visit-count-slider").fill("8");
    await expect(page.getByText("8x")).toBeVisible();
  });

  test("clicking mobile device type activates it", async ({ page }) => {
    const mobileBtn = page.getByRole("button", { name: "mobile" });
    await mobileBtn.click();
    // Active state: has accent border class
    await expect(mobileBtn).toHaveClass(/border-accent/);
  });

  test("clicking paid search referral activates it", async ({ page }) => {
    const paidBtn = page.getByRole("button", { name: "paid search" });
    await paidBtn.click();
    await expect(paidBtn).toHaveClass(/border-accent/);
  });
});

// ── High intent visitor flow ──────────────────────────────────────────────────

test.describe("High intent visitor analysis (maps to Salesforce mock)", () => {
  test("pipeline starts after submitting high-intent visitor", async ({ page }) => {
    await openVisitorForm(page);
    await fillVisitorForm(page, {
      visitorId: HIGH_INTENT_VISITOR.visitorId,
      pages: HIGH_INTENT_VISITOR.pages,
      timeSliderValue: HIGH_INTENT_VISITOR.timeOnSiteSeconds,
      visitSliderValue: HIGH_INTENT_VISITOR.visitCount,
    });
    await page.getByTestId("submit-btn").click();

    await expect(page.getByTestId("pipeline-progress")).toBeVisible({
      timeout: ELEMENT_TIMEOUT_MS,
    });
  });

  test("high intent visitor pipeline completes and navigates to account", async ({
    page,
  }) => {
    await openVisitorForm(page);
    await fillVisitorForm(page, {
      visitorId: HIGH_INTENT_VISITOR.visitorId,
      pages: HIGH_INTENT_VISITOR.pages,
      timeSliderValue: HIGH_INTENT_VISITOR.timeOnSiteSeconds,
      visitSliderValue: HIGH_INTENT_VISITOR.visitCount,
      referral: "paid search",
    });
    await page.getByTestId("submit-btn").click();

    await page.waitForURL(/\/account\//, { timeout: PIPELINE_TIMEOUT_MS });
    await expect(page.getByTestId("intent-score")).toBeVisible({
      timeout: ELEMENT_TIMEOUT_MS,
    });
  });

  test("high intent visitor result shows high intent score (8.7)", async ({ page }) => {
    await openVisitorForm(page);
    await fillVisitorForm(page, { visitorId: HIGH_INTENT_VISITOR.visitorId });
    await page.getByTestId("submit-btn").click();
    await page.waitForURL(/\/account\//, { timeout: PIPELINE_TIMEOUT_MS });

    const score = page.getByTestId("intent-score");
    await expect(score).toHaveText(HIGH_INTENT_VISITOR.expectedScore, {
      timeout: ELEMENT_TIMEOUT_MS,
    });
  });

  test("high intent visitor result shows HIGH priority playbook", async ({ page }) => {
    await openVisitorForm(page);
    await fillVisitorForm(page, { visitorId: HIGH_INTENT_VISITOR.visitorId });
    await page.getByTestId("submit-btn").click();
    await page.waitForURL(/\/account\//, { timeout: PIPELINE_TIMEOUT_MS });

    await expect(
      page.getByTestId("playbook-priority")
    ).toHaveText(HIGH_INTENT_VISITOR.expectedPriority, { timeout: ELEMENT_TIMEOUT_MS });
  });
});

// ── Low intent visitor flow ───────────────────────────────────────────────────

test.describe("Low intent visitor analysis (maps to HubSpot mock)", () => {
  test("low intent visitor pipeline completes and navigates to account", async ({
    page,
  }) => {
    await openVisitorForm(page);
    await fillVisitorForm(page, {
      visitorId: LOW_INTENT_VISITOR.visitorId,
      pages: LOW_INTENT_VISITOR.pages,
      timeSliderValue: LOW_INTENT_VISITOR.timeOnSiteSeconds,
      visitSliderValue: LOW_INTENT_VISITOR.visitCount,
    });
    await page.getByTestId("submit-btn").click();
    await page.waitForURL(/\/account\//, { timeout: PIPELINE_TIMEOUT_MS });

    await expect(page.getByTestId("intent-score")).toBeVisible({
      timeout: ELEMENT_TIMEOUT_MS,
    });
  });

  test("low intent visitor result shows medium score 6.4", async ({ page }) => {
    await openVisitorForm(page);
    await fillVisitorForm(page, { visitorId: LOW_INTENT_VISITOR.visitorId });
    await page.getByTestId("submit-btn").click();
    await page.waitForURL(/\/account\//, { timeout: PIPELINE_TIMEOUT_MS });

    const score = page.getByTestId("intent-score");
    await expect(score).toHaveText(LOW_INTENT_VISITOR.expectedScore, {
      timeout: ELEMENT_TIMEOUT_MS,
    });
  });

  test("low intent visitor result shows MEDIUM priority", async ({ page }) => {
    await openVisitorForm(page);
    await fillVisitorForm(page, { visitorId: LOW_INTENT_VISITOR.visitorId });
    await page.getByTestId("submit-btn").click();
    await page.waitForURL(/\/account\//, { timeout: PIPELINE_TIMEOUT_MS });

    await expect(
      page.getByTestId("playbook-priority")
    ).toHaveText(LOW_INTENT_VISITOR.expectedPriority, { timeout: ELEMENT_TIMEOUT_MS });
  });
});

// ── Cancel and reset ──────────────────────────────────────────────────────────

test.describe("Pipeline cancel and reset", () => {
  test("cancel button appears during pipeline run", async ({ page }) => {
    await openVisitorForm(page);
    await fillVisitorForm(page, { visitorId: "salesforce_visitor_abc" });
    await page.getByTestId("submit-btn").click();

    await expect(page.getByTestId("pipeline-progress")).toBeVisible({
      timeout: ELEMENT_TIMEOUT_MS,
    });
    await expect(
      page.getByText("← Cancel and start over")
    ).toBeVisible({ timeout: ELEMENT_TIMEOUT_MS });
  });

  test("clicking cancel hides pipeline and shows form again", async ({ page }) => {
    await openVisitorForm(page);
    await fillVisitorForm(page, { visitorId: "salesforce_visitor_abc" });
    await page.getByTestId("submit-btn").click();

    await expect(page.getByTestId("pipeline-progress")).toBeVisible({
      timeout: ELEMENT_TIMEOUT_MS,
    });
    await page.getByText("← Cancel and start over").click();

    await expect(page.getByTestId("analysis-form")).toBeVisible({
      timeout: ELEMENT_TIMEOUT_MS,
    });
  });
});
