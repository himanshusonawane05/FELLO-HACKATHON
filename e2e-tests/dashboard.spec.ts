import { expect, test } from "@playwright/test";
import { ELEMENT_TIMEOUT_MS, ROUTES, SEEDED_ACCOUNTS } from "./helpers/constants";

test.describe("Dashboard", () => {
  test.beforeEach(async ({ page }) => {
    await page.goto(ROUTES.dashboard);
  });

  test("renders page title and tagline", async ({ page }) => {
    await expect(page.getByRole("heading", { name: "Account Intelligence" })).toBeVisible();
    await expect(
      page.getByText("Convert visitor signals and company names")
    ).toBeVisible();
  });

  test("shows brand header with Fello AI logo", async ({ page }) => {
    await expect(page.getByText("Fello")).toBeVisible();
    await expect(page.getByText("Account Intelligence").first()).toBeVisible();
  });

  test("shows AI Pipeline Active indicator", async ({ page }) => {
    await expect(page.getByText("AI Pipeline Active")).toBeVisible();
  });

  test("renders analysis form with Company Lookup tab active by default", async ({ page }) => {
    const form = page.getByTestId("analysis-form");
    await expect(form).toBeVisible();

    // Company Lookup is the default tab
    const companyTab = page.getByTestId("mode-company");
    await expect(companyTab).toBeVisible();
    await expect(companyTab).toHaveText("Company Lookup");

    // Visitor Signal tab is also present
    const visitorTab = page.getByTestId("mode-visitor");
    await expect(visitorTab).toBeVisible();
    await expect(visitorTab).toHaveText("Visitor Signal");
  });

  test("company name input is present in company mode", async ({ page }) => {
    const input = page.getByTestId("company-name-input");
    await expect(input).toBeVisible();
    await expect(input).toHaveAttribute("placeholder", "e.g. Salesforce");
  });

  test("switching to visitor mode shows visitor form fields", async ({ page }) => {
    await page.getByTestId("mode-visitor").click();

    const visitorIdInput = page.getByTestId("visitor-id-input");
    await expect(visitorIdInput).toBeVisible({
      timeout: ELEMENT_TIMEOUT_MS,
    });

    // Scenario builder controls
    await expect(page.getByTestId("time-on-site-slider")).toBeVisible();
    await expect(page.getByTestId("visit-count-slider")).toBeVisible();
  });

  test("visitor mode shows device type toggles", async ({ page }) => {
    await page.getByTestId("mode-visitor").click();
    await expect(page.getByRole("button", { name: "desktop" })).toBeVisible();
    await expect(page.getByRole("button", { name: "mobile" })).toBeVisible();
    await expect(page.getByRole("button", { name: "tablet" })).toBeVisible();
  });

  test("visitor mode shows referral source pills", async ({ page }) => {
    await page.getByTestId("mode-visitor").click();
    await expect(page.getByRole("button", { name: "direct" })).toBeVisible();
    await expect(page.getByRole("button", { name: "organic search" })).toBeVisible();
    await expect(page.getByRole("button", { name: "email" })).toBeVisible();
  });

  test("loads three pre-seeded recent accounts", async ({ page }) => {
    const cards = page.getByTestId("account-card");
    await expect(cards).toHaveCount(3, { timeout: ELEMENT_TIMEOUT_MS });
  });

  test("recent accounts include Salesforce, Stripe and HubSpot", async ({ page }) => {
    for (const account of SEEDED_ACCOUNTS) {
      await expect(
        page.getByTestId("account-card").filter({ hasText: account.name })
      ).toBeVisible({ timeout: ELEMENT_TIMEOUT_MS });
    }
  });

  test("account cards display company domain", async ({ page }) => {
    await expect(page.getByText("salesforce.com").first()).toBeVisible({
      timeout: ELEMENT_TIMEOUT_MS,
    });
    await expect(page.getByText("hubspot.com").first()).toBeVisible({
      timeout: ELEMENT_TIMEOUT_MS,
    });
  });

  test("account cards contain intent meter progress bars", async ({ page }) => {
    const intentMeters = page.getByTestId("intent-meter");
    await expect(intentMeters.first()).toBeVisible({ timeout: ELEMENT_TIMEOUT_MS });
  });

  test("account cards link to the account detail page", async ({ page }) => {
    const salesforceCard = page
      .getByTestId("account-card")
      .filter({ hasText: "Salesforce" });
    await expect(salesforceCard).toBeVisible({ timeout: ELEMENT_TIMEOUT_MS });

    await salesforceCard.click();
    await expect(page).toHaveURL(/\/account\/mock-acc-salesforce/);
  });

  test("shows How the pipeline works section", async ({ page }) => {
    await expect(page.getByText("How the pipeline works")).toBeVisible();
    await expect(page.getByText("Company Enrichment")).toBeVisible();
    await expect(page.getByText("Intent Scoring")).toBeVisible();
  });

  test("submit button is present and labelled Analyze", async ({ page }) => {
    await expect(page.getByTestId("submit-btn")).toBeVisible();
    await expect(page.getByTestId("submit-btn")).toHaveText("Analyze →");
  });

  test("submit button is disabled when company name is empty", async ({ page }) => {
    // Type then clear to trigger any validation
    const input = page.getByTestId("company-name-input");
    await input.fill("");
    await page.getByTestId("submit-btn").click();
    // Browser native required validation should prevent submission
    await expect(page).toHaveURL(ROUTES.dashboard);
    await expect(page.getByTestId("analysis-form")).toBeVisible();
  });
});
