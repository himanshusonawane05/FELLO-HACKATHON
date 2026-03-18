// ── URLs ─────────────────────────────────────────────────────────────────────

export const ROUTES = {
  dashboard: "/",
  account: (id: string) => `/account/${id}`,
  salesforce: "/account/mock-acc-salesforce",
  hubspot: "/account/mock-acc-hubspot",
  stripe: "/account/mock-acc-stripe",
} as const;

// ── Pre-seeded mock accounts ──────────────────────────────────────────────────

export const SEEDED_ACCOUNTS = [
  {
    name: "Salesforce",
    id: "mock-acc-salesforce",
    domain: "salesforce.com",
    intentScore: "8.7",
    priority: "HIGH",
    stage: "EVALUATION",
  },
  {
    name: "Stripe",
    id: "mock-acc-stripe",
    domain: "stripe.com",
    intentScore: "9.1",
    priority: "HIGH",
    stage: "PURCHASE",
  },
  {
    name: "HubSpot",
    id: "mock-acc-hubspot",
    domain: "hubspot.com",
    intentScore: "6.4",
    priority: "MEDIUM",
    stage: "CONSIDERATION",
  },
] as const;

// ── Timing ────────────────────────────────────────────────────────────────────

/** Total pipeline duration in mock mode (ms) */
export const PIPELINE_DURATION_MS = 7500;

/** Max wait for the pipeline to complete + navigation (ms) */
export const PIPELINE_TIMEOUT_MS = 15_000;

/** Max wait for general element visibility (ms) */
export const ELEMENT_TIMEOUT_MS = 8_000;

// ── Pipeline step labels ──────────────────────────────────────────────────────

export const PIPELINE_STEPS = [
  "Identifying company...",
  "Enriching company data...",
  "Inferring visitor persona...",
  "Scoring purchase intent...",
  "Generating sales playbook...",
  "Finalizing intelligence report...",
] as const;

// ── Visitor scenarios ─────────────────────────────────────────────────────────

/**
 * visitor_id prefix "salesforce" routes to the Salesforce mock (8.7 intent),
 * producing a HIGH-priority result. Use for high-intent visitor tests.
 */
export const HIGH_INTENT_VISITOR = {
  visitorId: "salesforce_visitor_enterprise",
  pages: "/pricing, /enterprise, /demo, /case-studies",
  timeOnSiteSeconds: 480, // 8 minutes
  visitCount: 7,
  referralSource: "paid_search",
  device: "desktop",
  expectedScore: "8.7",
  expectedPriority: "HIGH",
} as const;

/**
 * visitor_id prefix "hubspot" routes to the HubSpot mock (6.4 intent),
 * producing a MEDIUM-priority result. Use for low-intent visitor tests.
 */
export const LOW_INTENT_VISITOR = {
  visitorId: "hubspot_visitor_casual",
  pages: "/blog, /about",
  timeOnSiteSeconds: 50, // must be a multiple of 10 (slider step=10)
  visitCount: 1,
  referralSource: "organic_search",
  device: "desktop",
  expectedScore: "6.4",
  expectedPriority: "MEDIUM",
} as const;
