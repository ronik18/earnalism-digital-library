const { apiUrl, frontendUrl } = require("./envGuard");

function joinUrl(base, path) {
  const cleaned = String(path || "/");
  return `${String(base).replace(/\/+$/, "")}/${cleaned.replace(/^\/+/, "")}`;
}

async function request(url, options = {}) {
  const timeoutMs = options.timeoutMs || 15000;
  const controller = new AbortController();
  const timeout = setTimeout(() => controller.abort(), timeoutMs);
  const started = Date.now();
  try {
    const response = await fetch(url, {
      method: options.method || "GET",
      redirect: options.redirect || "follow",
      signal: controller.signal,
      headers: {
        Accept: "*/*",
        ...(options.headers || {}),
      },
    });
    const text = options.skipBody ? "" : await response.text();
    return {
      url,
      status: response.status,
      ok: response.ok,
      redirected: response.redirected,
      headers: response.headers,
      text,
      ms: Date.now() - started,
    };
  } finally {
    clearTimeout(timeout);
  }
}

async function getJson(url, options = {}) {
  const response = await request(url, {
    ...options,
    headers: { Accept: "application/json", ...(options.headers || {}) },
  });
  let data = null;
  try {
    data = response.text ? JSON.parse(response.text) : null;
  } catch (error) {
    throw new Error(`Expected JSON from ${url}, got status=${response.status}: ${error.message}`);
  }
  return { ...response, data };
}

async function apiGet(path, options = {}) {
  return getJson(joinUrl(apiUrl(), path), options);
}

async function apiRequest(path, options = {}) {
  return request(joinUrl(apiUrl(), path), options);
}

async function pageGet(path, options = {}) {
  return request(joinUrl(frontendUrl(), path), options);
}

async function urlOk(url, options = {}) {
  const response = await request(url, { method: options.method || "GET", skipBody: options.skipBody });
  return response.status >= 200 && response.status < 400;
}

module.exports = {
  joinUrl,
  request,
  getJson,
  apiGet,
  apiRequest,
  pageGet,
  urlOk,
};
