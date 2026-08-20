const { defineConfig, devices } = require("@playwright/test");

const externalBaseURL = (process.env.PLAYWRIGHT_BASE_URL || "").trim();
const baseURL = externalBaseURL || "http://127.0.0.1:3000";

module.exports = defineConfig({
  testDir: "./e2e",
  timeout: 30000,
  expect: { timeout: 10000 },
  fullyParallel: false,
  retries: process.env.CI ? 1 : 0,
  reporter: process.env.CI ? "line" : "list",
  use: {
    baseURL,
    trace: "on-first-retry",
    screenshot: "only-on-failure",
  },
  projects: [
    { name: "desktop-chromium", use: { ...devices["Desktop Chrome"] } },
    { name: "mobile-chromium", use: { ...devices["Pixel 7"] } },
  ],
  webServer: externalBaseURL
    ? undefined
    : {
        command: "yarn start",
        url: "http://127.0.0.1:3000",
        reuseExistingServer: !process.env.CI,
        timeout: 120000,
        env: {
          HOST: "127.0.0.1",
          PORT: "3000",
          BROWSER: "none",
          REACT_APP_BACKEND_URL: "http://127.0.0.1:8001",
        },
      },
});
