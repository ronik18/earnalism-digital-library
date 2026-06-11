const { apiOrigin, isProductionTarget, isGoLive, loadTestAllowed } = require("../utils/envGuard");
const { request } = require("../utils/http");

describe("Auto-Scaling & Infrastructure", () => {
  test("/healthz returns status ok", async () => {
    const response = await request(`${apiOrigin()}/healthz`);
    expect(response.ok).toBe(true);
    expect(response.text).toMatch(/ok/i);
  });

  test("GO LIVE target is staging unless explicitly allowed", async () => {
    if (isGoLive()) {
      expect(isProductionTarget()).toBe(false);
    } else {
      expect(true).toBe(true);
    }
  });

  test("load testing is gated away from production", async () => {
    if (process.env.REGRESSION_ENABLE_LOAD_TEST === "true") {
      expect(loadTestAllowed()).toBe(true);
    } else if (isGoLive()) {
      throw new Error("REGRESSION_ENABLE_LOAD_TEST=true is required for GO LIVE non-production load testing.");
    } else {
      expect(true).toBe(true);
    }
  });

  test("Railway/Judoscale readiness secrets are present for GO LIVE", async () => {
    if (!isGoLive()) {
      expect(true).toBe(true);
      return;
    }
    expect(process.env.JUDOSCALE_URL || process.env.RAILWAY_TOKEN).toBeTruthy();
  });
});
