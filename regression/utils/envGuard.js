const PRODUCTION_HOSTS = new Set([
  "theearnalism.com",
  "www.theearnalism.com",
  "api.theearnalism.com",
]);

function mode() {
  return (process.env.REGRESSION_MODE || "pr").trim().toLowerCase();
}

function normalizeBase(value, fallback) {
  return String(value || fallback || "").replace(/\/+$/, "");
}

function frontendUrl() {
  return normalizeBase(
    process.env.REGRESSION_FRONTEND_URL || process.env.FRONTEND_URL || process.env.E2E_BASE_URL,
    "https://theearnalism.com",
  );
}

function apiUrl() {
  const raw = normalizeBase(
    process.env.REGRESSION_API_URL || process.env.API_URL || process.env.E2E_API_URL,
    "https://api.theearnalism.com",
  );
  return raw.endsWith("/api") ? raw : `${raw}/api`;
}

function apiOrigin() {
  return apiUrl().replace(/\/api$/, "");
}

function hostOf(value) {
  try {
    return new URL(value).hostname.toLowerCase();
  } catch {
    return "";
  }
}

function isProductionUrl(value) {
  return PRODUCTION_HOSTS.has(hostOf(value));
}

function isLocalUrl(value) {
  const host = hostOf(value);
  return ["localhost", "127.0.0.1", "::1"].includes(host);
}

function targetName() {
  return (process.env.REGRESSION_TARGET || process.env.NODE_ENV || "").toLowerCase();
}

function isProductionTarget() {
  const target = targetName();
  return target === "production" || isProductionUrl(frontendUrl()) || isProductionUrl(apiUrl());
}

function mutationAllowed() {
  const env = (process.env.NODE_ENV || "").toLowerCase();
  const target = targetName();
  return (
    ["test", "ci", "staging"].includes(env) &&
    process.env.REGRESSION_ALLOW_MUTATION === "true" &&
    !["production", "prod"].includes(target) &&
    !isProductionTarget()
  );
}

function redisFlushAllowed(redisUrl) {
  return (
    mutationAllowed() &&
    process.env.REDIS_ALLOW_FLUSH_FOR_REGRESSION === "true" &&
    redisUrl &&
    !/prod|production|theearnalism/i.test(redisUrl)
  );
}

function loadTestAllowed() {
  return (
    process.env.REGRESSION_ENABLE_LOAD_TEST === "true" &&
    !isProductionTarget() &&
    !isProductionUrl(frontendUrl()) &&
    !isProductionUrl(apiUrl())
  );
}

function isGoLive() {
  return mode() === "go-live";
}

function isPr() {
  return mode() === "pr";
}

function isCanary() {
  return mode() === "canary";
}

module.exports = {
  mode,
  frontendUrl,
  apiUrl,
  apiOrigin,
  isProductionUrl,
  isProductionTarget,
  isLocalUrl,
  mutationAllowed,
  redisFlushAllowed,
  loadTestAllowed,
  isGoLive,
  isPr,
  isCanary,
};
