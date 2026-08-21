const { defineConfig, devices } = require("playwright/test");

const ARTIFACT_DIR = "output/real-user-ux";
const FRONTEND_URL = String(process.env.UAT_BASE_URL || "").replace(/\/$/, "");
const API_URL = String(process.env.UAT_API_BASE_URL || "").replace(/\/$/, "");

function assertLocalUatUrl(name, value, expectedPath = "") {
  if (!value) throw new Error(`${name} is required; production fallback is disabled.`);
  const parsed = new URL(value);
  if (parsed.protocol !== "http:" || parsed.hostname !== "127.0.0.1") {
    throw new Error(`${name} must use http://127.0.0.1 only.`);
  }
  if (expectedPath && parsed.pathname.replace(/\/$/, "") !== expectedPath) {
    throw new Error(`${name} must use the ${expectedPath} API prefix.`);
  }
}

assertLocalUatUrl("UAT_BASE_URL", FRONTEND_URL);
assertLocalUatUrl("UAT_API_BASE_URL", API_URL, "/api");

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
    baseURL: FRONTEND_URL,
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
    {
      name: "firefox",
      use: { ...devices["Desktop Firefox"] },
    },
    {
      name: "webkit",
      use: { ...devices["Desktop Safari"] },
    },
  ],
});
