import { expect, test } from "@playwright/test";
import {
  ELEMENT_TIMEOUT_MS,
  PIPELINE_TIMEOUT_MS,
  ROUTES,
} from "./helpers/constants";

// ── Helper: submit a company name from the dashboard ─────────────────────────

async function submitCompany(
  page: Parameters<Parameters<typeof test>[1]>[0],
  companyName: string
): Promise<void> {
  await page.goto(ROUTES.dashboard);
  await page.getByTestId("company-name-input").fill(companyName);
  await page.getByTestId("submit-btn").click();
}

// ── Salesforce ────────────────────────────────────────────────────────────────

test.describe("Company flow — Salesforce (high intent)", () => {
  test("pipeline progress appears immediately after submit", async ({ page }) => {
    await submitCompany(page, "Salesforce");
    await expect(page.getByTestId("pipeline-progress")).toBeVisible({
      timeout: ELEMENT_TIMEOUT_MS,
    });
    await expect(page.getByText("Running Analysis Pipeline")).toBeVisible({
      timeout: ELEMENT_TIMEOUT_MS,
    });
  });

  test("pipeline shows target company name", async ({ page }) => {
    await submitCompany(page, "Salesforce");
    await expect(page.getByText("Salesforce").first()).toBeVisible({
      timeout: ELEMENT_TIMEOUT_MS,
    });
  });

  test("pipeline step label updates during analysis", async ({ page }) => {
    await submitCompany(page, "Salesforce");
    const stepLabel = page.getByTestId("pipeline-step");
    await expect(stepLabel).toBeVisible({ timeout: ELEMENT_TIMEOUT_MS });
    const text = await stepLabel.textContent();
    expect(text?.trim().length).toBeGreaterThan(0);
  });

  test("pipeline progress bar advances (not stuck at 0%)", async ({ page }) => {
    await submitCompany(page, "Salesforce");
    await expect(page.getByTestId("pipeline-progress-bar")).toBeVisible({
      timeout: ELEMENT_TIMEOUT_MS,
    });
    await page.waitForTimeout(1500);
    const pctText = await page
      .locator('[data-testid="pipeline-progress"] span')
      .filter({ hasText: /\d+%/ })
      .textContent();
    const pct = parseInt(pctText ?? "0", 10);
    expect(pct).toBeGreaterThan(0);
  });

  test("navigates to Salesforce account detail after pipeline completes", async ({ page }) => {
    await submitCompany(page, "Salesforce");
    await page.waitForURL(/\/account\/mock-acc-salesforce/, {
      timeout: PIPELINE_TIMEOUT_MS,
    });
    await expect(page).toHaveURL(/\/account\/mock-acc-salesforce/);
  });

  // All assertions below run after navigating to the account detail page
  test.describe("Salesforce account detail", () => {
    test.beforeEach(async ({ page }) => {
      await page.goto(ROUTES.salesforce);
      // Wait for the page to finish loading before each test
      await expect(
        page.getByRole("heading", { name: "Salesforce", level: 1 })
      ).toBeVisible({ timeout: ELEMENT_TIMEOUT_MS });
    });

    test("shows Salesforce h1 company heading", async ({ page }) => {
      await expect(
        page.getByRole("heading", { name: "Salesforce", level: 1 })
      ).toBeVisible();
    });

    test("shows salesforce.com domain link in header", async ({ page }) => {
      // The header link has "salesforce.com ↗" — scope to the header
      await expect(
        page.locator("header").getByText("salesforce.com")
      ).toBeVisible();
    });

    test("shows HIGH priority badge", async ({ page }) => {
      await expect(page.getByText("HIGH PRIORITY")).toBeVisible();
    });

    test("renders company profile card with industry", async ({ page }) => {
      const card = page.getByTestId("company-profile");
      await expect(card).toBeVisible();
      // Scope the text check to the card to avoid multi-match
      await expect(card.getByText("Enterprise CRM")).toBeVisible();
    });

    test("renders intent meter with high score 8.7", async ({ page }) => {
      const score = page.getByTestId("intent-score");
      await expect(score).toBeVisible();
      await expect(score).toHaveText("8.7");
    });

    test("intent meter score color is green (high intent)", async ({ page }) => {
      await expect(page.getByTestId("intent-score")).toHaveCSS(
        "color",
        "rgb(0, 255, 136)"
      );
    });

    test("renders EVALUATION stage label in intent meter", async ({ page }) => {
      // Scope EVALUATION to the intent meter to avoid matching AI summary text
      await expect(
        page.getByTestId("intent-meter").getByText("EVALUATION")
      ).toBeVisible();
    });

    test("renders AI summary block", async ({ page }) => {
      await expect(page.getByTestId("ai-summary")).toBeVisible();
      await expect(page.getByText("AI Summary")).toBeVisible();
    });

    test("AI summary contains meaningful content", async ({ page }) => {
      await expect(
        page.getByTestId("ai-summary").getByText(/EVALUATION stage/i)
      ).toBeVisible();
    });

    test("renders persona badge for VP role", async ({ page }) => {
      const badge = page.getByTestId("persona-badge");
      await expect(badge).toBeVisible();
      // Scope VP text to the badge to avoid matching AI summary text
      await expect(badge.getByText(/VP of Sales Operations/i)).toBeVisible();
    });

    test("renders tech stack with Salesforce technologies", async ({ page }) => {
      const techStack = page.getByTestId("tech-stack");
      await expect(techStack).toBeVisible();
      await expect(techStack.getByText("Salesforce CRM")).toBeVisible();
      await expect(techStack.getByText("Slack")).toBeVisible();
    });

    test("renders business signals feed", async ({ page }) => {
      const signals = page.getByTestId("signals-feed");
      await expect(signals).toBeVisible();
      await expect(page.getByText("Aggressive AI talent hiring surge")).toBeVisible();
    });

    test("renders leadership list with Marc Benioff", async ({ page }) => {
      const list = page.getByTestId("leadership-list");
      await expect(list).toBeVisible();
      await expect(list.getByText("Marc Benioff")).toBeVisible();
      await expect(list.getByText("Chair & CEO")).toBeVisible();
    });

    test("renders sales playbook with HIGH priority", async ({ page }) => {
      const playbook = page.getByTestId("sales-playbook");
      await expect(playbook).toBeVisible();
      await expect(page.getByTestId("playbook-priority")).toHaveText("HIGH");
    });

    test("sales playbook contains recommended actions", async ({ page }) => {
      await expect(
        page.getByText("Lead with AI ROI case study")
      ).toBeVisible();
    });

    test("sales playbook contains outreach template", async ({ page }) => {
      await expect(
        page.getByText(/Saw the Agentforce launch/i)
      ).toBeVisible();
    });

    test("back navigation link goes to dashboard", async ({ page }) => {
      await page.getByText("← Dashboard").click();
      await expect(page).toHaveURL(ROUTES.dashboard);
    });
  });
});

// ── HubSpot ───────────────────────────────────────────────────────────────────

test.describe("Company flow — HubSpot (medium intent)", () => {
  test.beforeEach(async ({ page }) => {
    await page.goto(ROUTES.hubspot);
    await expect(
      page.getByRole("heading", { name: "HubSpot", level: 1 })
    ).toBeVisible({ timeout: ELEMENT_TIMEOUT_MS });
  });

  test("shows HubSpot h1 company heading", async ({ page }) => {
    await expect(
      page.getByRole("heading", { name: "HubSpot", level: 1 })
    ).toBeVisible();
  });

  test("renders intent meter with medium score 6.4", async ({ page }) => {
    await expect(page.getByTestId("intent-score")).toHaveText("6.4");
  });

  test("intent meter score color is amber (medium intent)", async ({ page }) => {
    await expect(page.getByTestId("intent-score")).toHaveCSS(
      "color",
      "rgb(245, 158, 11)"
    );
  });

  test("renders CONSIDERATION stage label in intent meter", async ({ page }) => {
    await expect(
      page.getByTestId("intent-meter").getByText("CONSIDERATION")
    ).toBeVisible();
  });

  test("shows MEDIUM priority badge on account header", async ({ page }) => {
    await expect(page.getByText("MEDIUM PRIORITY")).toBeVisible();
  });

  test("sales playbook priority is MEDIUM", async ({ page }) => {
    await expect(page.getByTestId("playbook-priority")).toHaveText("MEDIUM");
  });

  test("shows Director of Revenue Operations persona in badge", async ({ page }) => {
    await expect(
      page.getByTestId("persona-badge").getByText(/Director of Revenue Operations/i)
    ).toBeVisible();
  });

  test("shows APAC expansion signal", async ({ page }) => {
    await expect(page.getByText("APAC market expansion")).toBeVisible();
  });

  test("shows Yamini Rangan in leadership", async ({ page }) => {
    await expect(
      page.getByTestId("leadership-list").getByText("Yamini Rangan")
    ).toBeVisible();
  });
});
