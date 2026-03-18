import type {
  AccountIntelligenceResponse,
  AccountListResponse,
  AccountSummary,
} from "@/types/intelligence";

// ── Rich mock datasets ────────────────────────────────────────────────────────

const SALESFORCE_MOCK: AccountIntelligenceResponse = {
  success: true,
  account_id: "mock-acc-salesforce",
  company_name: "Salesforce",
  domain: "salesforce.com",
  industry: "Enterprise CRM",
  company_size: "73,000 employees",
  headquarters: "San Francisco, CA, USA",
  description:
    "Salesforce is the world's #1 CRM platform, connecting companies with their customers in a whole new way. Founded in 1999, it has grown to serve over 150,000 businesses worldwide with cloud-based CRM, analytics, and AI solutions.",
  annual_revenue_range: "$30B – $35B",
  intent_score: 8.7,
  intent_stage: "EVALUATION",
  likely_role: "VP of Sales Operations",
  seniority_level: "VP",
  persona_confidence: 0.78,
  technologies: [
    { name: "Salesforce CRM", category: "CRM", confidence_score: 0.99 },
    { name: "Tableau", category: "ANALYTICS", confidence_score: 0.92 },
    { name: "Slack", category: "COMMUNICATION", confidence_score: 0.95 },
    { name: "AWS", category: "CLOUD_INFRASTRUCTURE", confidence_score: 0.9 },
    { name: "Marketo", category: "MARKETING_AUTOMATION", confidence_score: 0.72 },
    { name: "MuleSoft", category: "OTHER", confidence_score: 0.88 },
  ],
  business_signals: [
    {
      signal_type: "HIRING",
      title: "Aggressive AI talent hiring surge",
      description:
        "400+ AI/ML engineering roles posted in Q4 2024, signaling major Agentforce platform investment.",
      source_url: "https://salesforce.com/careers",
    },
    {
      signal_type: "PRODUCT_LAUNCH",
      title: "Agentforce autonomous AI platform",
      description:
        "New autonomous AI agents platform launched at Dreamforce 2024 — strategic shift to AI-first sales automation.",
      source_url: "https://www.salesforce.com/agentforce",
    },
    {
      signal_type: "FUNDING",
      title: "$2.8B AI infrastructure investment",
      description:
        "Committed $2.8B to expand global AI data centers and GPU compute through 2026.",
      source_url: null,
    },
  ],
  leaders: [
    {
      name: "Marc Benioff",
      title: "Chair & CEO",
      department: "Executive",
      linkedin_url: "https://linkedin.com/in/marcbenioff",
    },
    {
      name: "Brian Millham",
      title: "President & COO",
      department: "Operations",
      linkedin_url: "https://linkedin.com/in/brianmillham",
    },
    {
      name: "Amy Weaver",
      title: "President & CFO",
      department: "Finance",
      linkedin_url: null,
    },
    {
      name: "Clara Shih",
      title: "CEO of Salesforce AI",
      department: "Artificial Intelligence",
      linkedin_url: null,
    },
  ],
  recommended_actions: [
    {
      action: "Lead with AI ROI case study",
      rationale:
        "Agentforce launch signals AI-first strategy — position your AI capabilities as complementary, not competitive.",
      priority: "HIGH",
    },
    {
      action: "Schedule technical demo with VP Engineering",
      rationale:
        "Intent score 8.7 in EVALUATION stage means they're actively comparing solutions right now.",
      priority: "HIGH",
    },
    {
      action: "Send competitive displacement guide",
      rationale:
        "Deeply embedded in their own ecosystem — show clear integration path with zero disruption.",
      priority: "MEDIUM",
    },
  ],
  talking_points: [
    "Your Agentforce launch shows you understand AI agents — we integrate natively with Salesforce workflows.",
    "Our customers see 3.2x pipeline growth within 90 days of deployment.",
    "We already serve 12 enterprise CRM vendors at your scale with proven ROI.",
    "Our API-first architecture means zero disruption to your existing data model.",
  ],
  outreach_template: `Hi {{first_name}},

Saw the Agentforce launch — impressive move toward autonomous sales workflows.

We work with CRM platforms like yours to surface buyer intent signals before they hit your pipeline. Most of our customers see reps spend 60% less time on research.

Worth a 20-minute call to see if the timing makes sense?

Best,
{{your_name}}`,
  playbook_priority: "HIGH",
  ai_summary:
    "Salesforce is in active EVALUATION stage with a high intent score of 8.7/10. Their recent Agentforce launch and aggressive AI hiring signal a strategic pivot toward AI-augmented sales automation. The VP of Sales Operations persona (78% confidence) suggests purchasing authority at the platform level. Recommend immediate outreach with AI ROI framing and a technical integration demo. Window is optimal — they are comparing solutions now.",
  analyzed_at: new Date().toISOString(),
  confidence_score: 0.92,
};

const HUBSPOT_MOCK: AccountIntelligenceResponse = {
  success: true,
  account_id: "mock-acc-hubspot",
  company_name: "HubSpot",
  domain: "hubspot.com",
  industry: "Marketing Automation",
  company_size: "7,400 employees",
  headquarters: "Cambridge, MA, USA",
  description:
    "HubSpot is a leading CRM, marketing, sales, and service platform used by 200,000+ businesses in 135 countries. Known for its inbound marketing methodology and SMB-focused toolset.",
  annual_revenue_range: "$2.1B – $2.5B",
  intent_score: 6.4,
  intent_stage: "CONSIDERATION",
  likely_role: "Director of Revenue Operations",
  seniority_level: "DIRECTOR",
  persona_confidence: 0.65,
  technologies: [
    { name: "HubSpot CRM", category: "CRM", confidence_score: 0.99 },
    { name: "Google Analytics", category: "ANALYTICS", confidence_score: 0.88 },
    { name: "WordPress", category: "WEBSITE_PLATFORM", confidence_score: 0.75 },
    { name: "Intercom", category: "COMMUNICATION", confidence_score: 0.82 },
    { name: "GCP", category: "CLOUD_INFRASTRUCTURE", confidence_score: 0.85 },
  ],
  business_signals: [
    {
      signal_type: "EXPANSION",
      title: "APAC market expansion",
      description:
        "HubSpot opened Singapore and Sydney offices targeting 35% APAC revenue growth in FY2025.",
      source_url: null,
    },
    {
      signal_type: "HIRING",
      title: "RevOps team scaling 15+ roles",
      description:
        "15+ Revenue Operations roles open across NA and EMEA, indicating internal tooling investment.",
      source_url: "https://hubspot.com/jobs",
    },
  ],
  leaders: [
    {
      name: "Yamini Rangan",
      title: "CEO",
      department: "Executive",
      linkedin_url: "https://linkedin.com/in/yaminirangan",
    },
    {
      name: "Dharmesh Shah",
      title: "Co-Founder & CTO",
      department: "Engineering",
      linkedin_url: "https://linkedin.com/in/dharmeshshah",
    },
    {
      name: "Kate Doberstein",
      title: "Chief People Officer",
      department: "HR",
      linkedin_url: null,
    },
  ],
  recommended_actions: [
    {
      action: "Send APAC expansion success stories",
      rationale:
        "Their APAC push aligns with your regional coverage — show relevant customer wins from similar expansion plays.",
      priority: "MEDIUM",
    },
    {
      action: "Nurture with RevOps thought leadership",
      rationale:
        "Mid-funnel CONSIDERATION stage — educate before pushing for demo. Director persona responds to peer insights.",
      priority: "MEDIUM",
    },
    {
      action: "Invite to next RevOps roundtable webinar",
      rationale:
        "Community engagement before vendor demos increases conversion rate by 40% for Director-level buyers.",
      priority: "LOW",
    },
  ],
  talking_points: [
    "We've helped 3 other mid-market CRM platforms expand into APAC with localized signal tracking.",
    "Director-level buyers typically see value in 30 days — low implementation overhead.",
    "HubSpot's inbound methodology + our intent data creates a powerful top-of-funnel flywheel.",
  ],
  outreach_template: `Hi {{first_name}},

Noticed HubSpot is scaling your RevOps team and expanding into APAC — exciting times.

We help Revenue Operations teams at your scale cut through noise by surfacing which accounts are actually in-market. Would love to show you how we've helped similar companies.

Open to a quick intro call next week?

Best,
{{your_name}}`,
  playbook_priority: "MEDIUM",
  ai_summary:
    "HubSpot is at CONSIDERATION stage with a 6.4/10 intent score. APAC expansion and RevOps hiring signal investment in operational scale — but not yet in active evaluation mode. The Director of Revenue Operations persona (65% confidence) suggests mid-level budget authority. Recommend a nurture approach with thought leadership content and community engagement before pushing for a demo. Re-evaluate in 30 days.",
  analyzed_at: new Date().toISOString(),
  confidence_score: 0.78,
};

const STRIPE_MOCK: AccountIntelligenceResponse = {
  success: true,
  account_id: "mock-acc-stripe",
  company_name: "Stripe",
  domain: "stripe.com",
  industry: "FinTech / Payments",
  company_size: "8,000 employees",
  headquarters: "San Francisco & Dublin",
  description:
    "Stripe is a global payments infrastructure company processing hundreds of billions of dollars annually for millions of businesses from startups to Fortune 500s.",
  annual_revenue_range: "$14B – $16B",
  intent_score: 9.1,
  intent_stage: "PURCHASE",
  likely_role: "Head of Sales Engineering",
  seniority_level: "DIRECTOR",
  persona_confidence: 0.84,
  technologies: [
    { name: "Stripe Payments", category: "OTHER", confidence_score: 0.99 },
    { name: "AWS", category: "CLOUD_INFRASTRUCTURE", confidence_score: 0.95 },
    { name: "Salesforce", category: "CRM", confidence_score: 0.88 },
    { name: "Amplitude", category: "ANALYTICS", confidence_score: 0.82 },
    { name: "Segment", category: "ANALYTICS", confidence_score: 0.79 },
    { name: "Notion", category: "COMMUNICATION", confidence_score: 0.70 },
  ],
  business_signals: [
    {
      signal_type: "PRODUCT_LAUNCH",
      title: "Stripe Billing v3 GA release",
      description:
        "New subscription management engine launched globally — creates immediate need for billing intelligence tooling.",
      source_url: "https://stripe.com/blog",
    },
    {
      signal_type: "PARTNERSHIP",
      title: "Goldman Sachs banking partnership expansion",
      description:
        "Expanded financial services partnership signals move upmarket toward enterprise banking segment.",
      source_url: null,
    },
    {
      signal_type: "HIRING",
      title: "Sales engineering team doubling",
      description:
        "20+ senior sales engineer roles posted — direct signal of enterprise sales motion acceleration.",
      source_url: "https://stripe.com/jobs",
    },
  ],
  leaders: [
    {
      name: "Patrick Collison",
      title: "CEO & Co-Founder",
      department: "Executive",
      linkedin_url: "https://linkedin.com/in/patrickcollison",
    },
    {
      name: "John Collison",
      title: "President & Co-Founder",
      department: "Executive",
      linkedin_url: null,
    },
    {
      name: "Eileen O'Mara",
      title: "Chief Revenue Officer",
      department: "Sales",
      linkedin_url: null,
    },
  ],
  recommended_actions: [
    {
      action: "Fast-track executive meeting request",
      rationale:
        "9.1 intent score in PURCHASE stage — they are ready to buy. Every day of delay costs conversion probability.",
      priority: "HIGH",
    },
    {
      action: "Prepare custom enterprise proposal with SLA",
      rationale:
        "Head of Sales Engineering buyer values technical depth and contractual reliability.",
      priority: "HIGH",
    },
    {
      action: "Offer pilot program with success metrics",
      rationale:
        "Engineering-led culture means they will want to validate claims before full commitment.",
      priority: "MEDIUM",
    },
  ],
  talking_points: [
    "Your Billing v3 launch creates an immediate use case — we integrate on day one with zero migration.",
    "Sales engineering teams at your scale save 12 hours/week per rep with our automated qualification.",
    "We have an enterprise SLA with 99.9% uptime — meets Stripe's reliability requirements.",
    "3 other payments companies in our portfolio closed within 60 days of their first demo.",
  ],
  outreach_template: `Hi {{first_name}},

Congrats on the Billing v3 launch — the subscription engine looks powerful.

We've seen a pattern: companies that ship major billing infrastructure soon need better intelligence on which enterprise accounts are ready to adopt it. That's exactly what we do.

Can we find 30 minutes this week? I have a specific use case for Stripe that I'd love to show you.

{{your_name}}`,
  playbook_priority: "HIGH",
  ai_summary:
    "Stripe has the highest intent score in your pipeline at 9.1/10 and is in PURCHASE stage — they are ready to buy. The Head of Sales Engineering persona (84% confidence) has direct budget authority for tooling decisions. Billing v3 launch creates an immediate integration use case. Sales engineering hiring surge confirms active scaling of enterprise motion. This is a must-close account — initiate executive outreach immediately with a custom enterprise proposal.",
  analyzed_at: new Date(Date.now() - 24 * 60 * 60 * 1000).toISOString(),
  confidence_score: 0.88,
};

// ── Default mock for unknown company names ────────────────────────────────────

function buildDefaultMock(companyName: string): AccountIntelligenceResponse {
  const slug = companyName.toLowerCase().replace(/\s+/g, "-");
  return {
    success: true,
    account_id: `mock-acc-${slug}`,
    company_name: companyName,
    domain: `${companyName.toLowerCase().replace(/\s+/g, "")}.com`,
    industry: "B2B Software",
    company_size: "200–500 employees",
    headquarters: "San Francisco, CA",
    description: `${companyName} is a growing B2B software company focused on enterprise workflow automation. They serve mid-market and enterprise clients across multiple verticals with a focus on data-driven decision making.`,
    annual_revenue_range: "$10M – $50M",
    intent_score: 7.2,
    intent_stage: "EVALUATION",
    likely_role: "VP of Sales",
    seniority_level: "VP",
    persona_confidence: 0.62,
    technologies: [
      { name: "Salesforce", category: "CRM", confidence_score: 0.85 },
      { name: "Google Analytics", category: "ANALYTICS", confidence_score: 0.78 },
      { name: "AWS", category: "CLOUD_INFRASTRUCTURE", confidence_score: 0.72 },
      { name: "Intercom", category: "COMMUNICATION", confidence_score: 0.65 },
    ],
    business_signals: [
      {
        signal_type: "HIRING",
        title: "Sales team expansion",
        description: `${companyName} posted 10+ sales roles in the past 30 days, indicating revenue growth targets.`,
        source_url: null,
      },
      {
        signal_type: "FUNDING",
        title: "Series B funding round",
        description: `${companyName} raised a $25M Series B to accelerate product development and market expansion.`,
        source_url: null,
      },
    ],
    leaders: [
      { name: "Sarah Chen", title: "CEO & Co-Founder", department: "Executive", linkedin_url: null },
      { name: "James Park", title: "VP of Sales", department: "Sales", linkedin_url: null },
      { name: "Maria Santos", title: "Head of Engineering", department: "Engineering", linkedin_url: null },
    ],
    recommended_actions: [
      {
        action: "Send ROI case study from similar-sized company",
        rationale: "Series B company with growth targets — ROI and time-to-value messaging resonates strongly.",
        priority: "HIGH",
      },
      {
        action: "Request intro through VP of Sales",
        rationale: "Hiring signals indicate active growth investment — budget is likely available now.",
        priority: "HIGH",
      },
      {
        action: "Add to nurture sequence with growth stage content",
        rationale: "Complement direct outreach with educational content tailored to scaling sales orgs.",
        priority: "LOW",
      },
    ],
    talking_points: [
      `Your recent Series B signals you're scaling fast — we help growing sales teams move faster with less overhead.`,
      "Companies at your stage typically see a 4x improvement in outbound conversion rates.",
      "We integrate with Salesforce in under a day — zero disruption to your existing workflow.",
      "Our customers close 2.3x more enterprise deals within the first quarter.",
    ],
    outreach_template: `Hi {{first_name}},

Congrats on the Series B — scaling a sales org at that pace is both exciting and challenging.

We help companies like ${companyName} identify which accounts are actively in-market so your team focuses on the right opportunities at the right time.

Would love to show you a quick demo. 15 minutes this week?

Best,
{{your_name}}`,
    playbook_priority: "HIGH",
    ai_summary: `${companyName} shows strong buying intent at 7.2/10, currently in EVALUATION stage. Recent Series B funding and aggressive hiring indicate growth-phase investment appetite. The VP of Sales persona (62% confidence) suggests direct budget authority for sales tooling. High priority account — recommend immediate personalized outreach with ROI-first messaging. Optimal window: next 2–3 weeks before quarter-end budget freeze.`,
    analyzed_at: new Date().toISOString(),
    confidence_score: 0.74,
  };
}

// ── Lookup by company name ────────────────────────────────────────────────────

export function getMockIntelligence(companyName: string): AccountIntelligenceResponse {
  const key = companyName.toLowerCase().trim();
  if (key.includes("salesforce")) return { ...SALESFORCE_MOCK, analyzed_at: new Date().toISOString() };
  if (key.includes("hubspot")) return { ...HUBSPOT_MOCK, analyzed_at: new Date().toISOString() };
  if (key.includes("stripe")) return { ...STRIPE_MOCK, analyzed_at: new Date().toISOString() };
  return buildDefaultMock(companyName);
}

export function getMockIntelligenceById(accountId: string): AccountIntelligenceResponse | null {
  if (accountId === "mock-acc-salesforce") return SALESFORCE_MOCK;
  if (accountId === "mock-acc-hubspot") return HUBSPOT_MOCK;
  if (accountId === "mock-acc-stripe") return STRIPE_MOCK;
  return null;
}

// ── Static recent accounts for dashboard ─────────────────────────────────────

export const MOCK_RECENT_ACCOUNTS: AccountSummary[] = [
  {
    success: true,
    account_id: "mock-acc-salesforce",
    company_name: "Salesforce",
    domain: "salesforce.com",
    industry: "Enterprise CRM",
    intent_score: 8.7,
    confidence_score: 0.92,
    analyzed_at: new Date(Date.now() - 2 * 60 * 60 * 1000).toISOString(),
  },
  {
    success: true,
    account_id: "mock-acc-stripe",
    company_name: "Stripe",
    domain: "stripe.com",
    industry: "FinTech / Payments",
    intent_score: 9.1,
    confidence_score: 0.88,
    analyzed_at: new Date(Date.now() - 5 * 60 * 60 * 1000).toISOString(),
  },
  {
    success: true,
    account_id: "mock-acc-hubspot",
    company_name: "HubSpot",
    domain: "hubspot.com",
    industry: "Marketing Automation",
    intent_score: 6.4,
    confidence_score: 0.78,
    analyzed_at: new Date(Date.now() - 24 * 60 * 60 * 1000).toISOString(),
  },
];

export const MOCK_ACCOUNT_LIST_RESPONSE: AccountListResponse = {
  success: true,
  accounts: MOCK_RECENT_ACCOUNTS,
  total: 3,
  page: 1,
  page_size: 20,
};
