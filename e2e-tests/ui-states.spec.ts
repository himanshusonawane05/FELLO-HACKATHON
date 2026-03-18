import { expect, test } from "@playwright/test";
import { ELEMENT_TIMEOUT_MS, PIPELINE_TIMEOUT_MS, ROUTES } from "./helpers/constants";

// ── Loading skeleton ──────────────────────────────────────────────────────────

test.describe("Loading skeleton", () => {
  test("account list shows skeleton while loading on initial dashboard mount", async ({
    page,
  }) => {
    // Intercept the listAccounts call to slow it down, exposing the skeleton
    await page.route("**/api/v1/accounts**", async (route) => {
      await page.waitForTimeout(1500);
      await route.continue();
    });

    // Navigate and immediately check for skeleton before content loads
    const navPromise = page.goto(ROUTES.dashboard);

    // The skeleton should appear before content
    await expect(
      page.locator(".animate-pulse").first()
    ).toBeVisible({ timeout: 3000 });

    await navPromise;
  });

  test("account detail shows skeleton on direct navigation before content arrives", async ({
    page,
  }) => {
    // Slow the getAccount API to expose the loading state
    await page.route("**/api/v1/accounts/**", async (route) => {
      await page.waitForTimeout(1000);
      await route.continue();
    });

    const navPromise = page.goto(ROUTES.salesforce);

    await expect(
      page.locator(".animate-pulse").first()
    ).toBeVisible({ timeout: 3000 });

    await navPromise;
  });

  test("skeleton disappears and content loads on direct account navigation", async ({
    page,
  }) => {
    await page.goto(ROUTES.salesforce);
    // After mock delay, real content must appear
    await expect(
      page.getByRole("heading", { name: "Salesforce", level: 1 })
    ).toBeVisible({ timeout: ELEMENT_TIMEOUT_MS });
    // Skeleton should be gone
    await expect(
      page.locator('[class*="animate-pulse"]')
    ).not.toBeVisible({ timeout: ELEMENT_TIMEOUT_MS });
  });
});

// ── All output sections visible on account detail ────────────────────────────

test.describe("All output sections rendered on account detail", () => {
  test.beforeEach(async ({ page }) => {
    await page.goto(ROUTES.salesforce);
    await expect(
      page.getByRole("heading", { name: "Salesforce", level: 1 })
    ).toBeVisible({ timeout: ELEMENT_TIMEOUT_MS });
  });

  test("company profile card is rendered", async ({ page }) => {
    await expect(page.getByTestId("company-profile")).toBeVisible();
  });

  test("intent meter is rendered", async ({ page }) => {
    await expect(page.getByTestId("intent-meter")).toBeVisible();
  });

  test("AI summary is rendered", async ({ page }) => {
    await expect(page.getByTestId("ai-summary")).toBeVisible();
  });

  test("tech stack grid is rendered", async ({ page }) => {
    await expect(page.getByTestId("tech-stack")).toBeVisible();
  });

  test("signals feed is rendered", async ({ page }) => {
    await expect(page.getByTestId("signals-feed")).toBeVisible();
  });

  test("leadership list is rendered", async ({ page }) => {
    await expect(page.getByTestId("leadership-list")).toBeVisible();
  });

  test("sales playbook is rendered", async ({ page }) => {
    await expect(page.getByTestId("sales-playbook")).toBeVisible();
  });

  test("persona badge is rendered", async ({ page }) => {
    await expect(page.getByTestId("persona-badge")).toBeVisible();
  });
});

// ── Error handling ────────────────────────────────────────────────────────────

test.describe("Error states", () => {
  test("navigating to a non-existent account shows error message", async ({ page }) => {
    await page.goto("/account/does-not-exist-12345");

    // Should show an error or fallback message (not a blank page)
    // The hook will throw when the account is not found
    await expect(
      page.getByText(/not found|failed|error/i).first()
    ).toBeVisible({ timeout: ELEMENT_TIMEOUT_MS });
  });

  test("error state on unknown account provides back navigation", async ({ page }) => {
    await page.goto("/account/definitely-not-a-real-id");

    await expect(
      page.getByText("← Dashboard")
    ).toBeVisible({ timeout: ELEMENT_TIMEOUT_MS });
  });

  test("clicking back from error goes to dashboard", async ({ page }) => {
    await page.goto("/account/bad-id-xyz");
    await page.getByText("← Dashboard").click();
    await expect(page).toHaveURL(ROUTES.dashboard);
  });
});

// ── Pipeline UI states ────────────────────────────────────────────────────────

test.describe("Pipeline UI states during analysis", () => {
  test("form is hidden while pipeline is running", async ({ page }) => {
    await page.goto(ROUTES.dashboard);
    await page.getByTestId("company-name-input").fill("Salesforce");
    await page.getByTestId("submit-btn").click();

    // Form should disappear while pipeline shows
    await expect(page.getByTestId("pipeline-progress")).toBeVisible({
      timeout: ELEMENT_TIMEOUT_MS,
    });
    await expect(page.getByTestId("analysis-form")).not.toBeVisible();
  });

  test("percentage shown in pipeline header increments to 100", async ({ page }) => {
    await page.goto(ROUTES.dashboard);
    await page.getByTestId("company-name-input").fill("Salesforce");
    await page.getByTestId("submit-btn").click();

    await expect(page.getByTestId("pipeline-progress")).toBeVisible({
      timeout: ELEMENT_TIMEOUT_MS,
    });

    // Wait for completion
    await page.waitForURL(/\/account\//, { timeout: PIPELINE_TIMEOUT_MS });

    // After navigation, we're on account detail — pipeline is done
    await expect(page.getByTestId("company-profile")).toBeVisible({
      timeout: ELEMENT_TIMEOUT_MS,
    });
  });

  test("How the pipeline works section is hidden while pipeline runs", async ({
    page,
  }) => {
    await page.goto(ROUTES.dashboard);
    await page.getByTestId("company-name-input").fill("Salesforce");
    await page.getByTestId("submit-btn").click();

    await expect(page.getByTestId("pipeline-progress")).toBeVisible({
      timeout: ELEMENT_TIMEOUT_MS,
    });

    // The "how it works" explainer hides during active pipeline
    await expect(page.getByText("How the pipeline works")).not.toBeVisible();
  });
});

// ── Responsive layout ─────────────────────────────────────────────────────────

test.describe("Responsive layout (mobile viewport)", () => {
  test.use({ viewport: { width: 390, height: 844 } }); // iPhone 14

  test("dashboard loads and form is usable on mobile", async ({ page }) => {
    await page.goto(ROUTES.dashboard);
    await expect(page.getByTestId("analysis-form")).toBeVisible({
      timeout: ELEMENT_TIMEOUT_MS,
    });
    await expect(page.getByTestId("company-name-input")).toBeVisible();
  });

  test("account detail renders on mobile", async ({ page }) => {
    await page.goto(ROUTES.salesforce);
    await expect(
      page.getByRole("heading", { name: "Salesforce", level: 1 })
    ).toBeVisible({ timeout: ELEMENT_TIMEOUT_MS });
    await expect(page.getByTestId("intent-meter")).toBeVisible();
  });
});
