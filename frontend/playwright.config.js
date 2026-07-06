import { defineConfig, devices } from "@playwright/test";

export default defineConfig({
  testDir: "./tests/e2e",
  outputDir: "./test-results/e2e",
  fullyParallel: true,
  retries: process.env.CI ? 2 : 0,
  reporter: process.env.CI
    ? [["github"], ["html", { outputFolder: "playwright-report" }]]
    : [["list"], ["html", { outputFolder: "playwright-report" }]],
  use: {
    baseURL: "http://127.0.0.1:4174",
    trace: "on-first-retry",
    serviceWorkers: "block",
    screenshot: "only-on-failure",
    video: "retain-on-failure",
    launchOptions: {
      args: ["--no-sandbox", "--disable-dev-shm-usage", "--disable-gpu"],
    },
  },
  projects: [
    {
      name: "chromium",
      use: { ...devices["Desktop Chrome"] },
    },
    {
      name: "firefox",
      use: { ...devices["Desktop Firefox"] },
    },
    {
      name: "Mobile Chrome",
      use: { ...devices["Pixel 5"] },
    },
  ],
  webServer: {
    command:
      "npm run build && node node_modules/vite/bin/vite.js preview --host 127.0.0.1 --port 4174",
    url: "http://127.0.0.1:4174",
    reuseExistingServer: !process.env.CI,
    timeout: 300000,
  },
  globalSetup: "./tests/e2e/global-setup.js",
  expect: {
    timeout: 10000,
  },
});
