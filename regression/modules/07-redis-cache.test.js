const { apiGet } = require("../utils/http");
const { getRedisClient, getRedisUrl } = require("../utils/redis");

describe("Redis Cache Performance", () => {
  test("Redis is reachable when configured, otherwise public cache headers are present", async () => {
    if (!getRedisUrl()) {
      const response = await apiGet("/home/books?limit=6&offset=0");
      expect(response.ok).toBe(true);
      expect(response.headers.get("cache-control") || "").toMatch(/public|max-age|stale-while-revalidate/i);
      return;
    }
    const state = await getRedisClient();
    if (state.skipped) throw new Error(state.reason);
    try {
      await state.client.ping();
      const info = await state.client.info();
      expect(info).toMatch(/used_memory/i);
    } finally {
      await state.client.quit();
    }
  });

  test("public cache warm request is not slower than cold request by a large margin", async () => {
    const cold = await apiGet("/home/books?limit=6&offset=0");
    const warm = await apiGet("/home/books?limit=6&offset=0");
    expect(cold.ok).toBe(true);
    expect(warm.ok).toBe(true);
    expect(warm.ms).toBeLessThanOrEqual(Math.max(cold.ms * 2.5, cold.ms + 500));
  });
});
