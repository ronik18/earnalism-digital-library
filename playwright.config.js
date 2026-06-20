const { defineConfig, devices } = require("playwright/test");

const ARTIFACT_DIR = "output/real-user-ux";

module.exports = defineConfig({
  testDir: "./tests/e2e",
  timeout: 90_000,
  expect: {
    timeout: 15_000,
  },
  fullyParallel: false,
  workers: 1,
  outputDir: `${ARTIFACT_DIR}/playwright-artifacts`,
  reporter: [
    ["list"],
    ["json", { outputFile: `${ARTIFACT_DIR}/playwright-results.json` }],
  ],
  use: {
    baseURL: process.env.EARNALISM_FRONTEND_URL || "https://theearnalism.com",
    trace: "on",
    video: "on",
    screenshot: "on",
    actionTimeout: 20_000,
    navigationTimeout: 45_000,
  },
  projects: [
    {
      name: "chromium",
      use: { ...devices["Desktop Chrome"] },
    },
  ],
});
