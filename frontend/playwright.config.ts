import { defineConfig, devices } from "@playwright/test";

export default defineConfig({
  testDir: "../e2e-tests",

  // Pipeline takes ~7.5s; give each test 30s total
  timeout: 30_000,

  // Each assertion waits up to 12s (accounts for pipeline + render)
  expect: { timeout: 12_000 },

  // Run tests sequentially — they share a browser and dev server
  fullyParallel: false,
  workers: 1,

  // Retry once on CI; no retries locally for faster feedback
  retries: process.env.CI ? 2 : 0,

  reporter: [
    ["list"],
    ["html", { outputFolder: "../playwright-report", open: "never" }],
  ],

  use: {
    baseURL: "http://localhost:3000",
    trace: "retain-on-failure",
    screenshot: "only-on-failure",
    video: "retain-on-failure",
    // Ensure mock env is set
    extraHTTPHeaders: {},
  },

  // Reuse the running dev server; start one if not already up
  webServer: {
    command: "npm run dev",
    url: "http://localhost:3000",
    reuseExistingServer: true,
    timeout: 30_000,
    env: {
      NEXT_PUBLIC_USE_MOCKS: "true",
      NEXT_PUBLIC_API_URL: "http://localhost:8000/api/v1",
    },
  },

  projects: [
    {
      name: "chromium",
      use: { ...devices["Desktop Chrome"] },
    },
  ],
});
