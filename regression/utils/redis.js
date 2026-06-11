function getRedisUrl() {
  return process.env.REGRESSION_REDIS_URL || process.env.REDIS_URL || "";
}

async function getRedisClient() {
  const url = getRedisUrl();
  if (!url) return { skipped: true, reason: "REDIS_URL is not configured." };
  let redis;
  try {
    redis = require("redis");
  } catch {
    return { skipped: true, reason: "redis package is not installed for regression cache checks." };
  }
  const client = redis.createClient({ url });
  await client.connect();
  return { client, skipped: false };
}

module.exports = { getRedisUrl, getRedisClient };
