const crypto = require("node:crypto");

const SCOPE_HEADER = "x-earnalism-release-scope";
const TIMESTAMP_HEADER = "x-earnalism-release-timestamp";
const SIGNATURE_HEADER = "x-earnalism-release-signature";
const COUNTRY_HEADER = "x-earnalism-release-country";
const DEFAULT_UPSTREAM = "https://api.theearnalism.com";
const PUBLIC_RELEASE_SCOPE = "PUBLIC";
// The current accepted, hash-bound Reader decisions cover India only.
const AUTHORIZED_READER_COUNTRIES = new Set(["IN"]);

function upstreamOrigin() {
  try {
    const parsed = new URL(process.env.EARNALISM_RELEASE_PROXY_UPSTREAM || DEFAULT_UPSTREAM);
    return parsed.protocol === "https:" ? parsed.origin : "";
  } catch {
    return "";
  }
}

function protectedReaderPath(pathname) {
  return pathname === "/api/books"
    || pathname.startsWith("/api/books/")
    || pathname.startsWith("/api/home")
    || pathname.startsWith("/api/reader/")
    || pathname.startsWith("/api/reading-pass/books/");
}

function releaseSignature(secret, method, pathname, scope, timestamp, country) {
  return crypto.createHmac("sha256", secret)
    .update(`${method.toUpperCase()}\\n${pathname}\\n${scope}\\n${timestamp}\\n${country}`)
    .digest("hex");
}

function requestBody(req) {
  return new Promise((resolve, reject) => {
    const chunks = [];
    req.on("data", (chunk) => chunks.push(chunk));
    req.on("end", () => resolve(chunks.length ? Buffer.concat(chunks) : undefined));
    req.on("error", reject);
  });
}

module.exports = async function releaseProxy(req, res) {
  const origin = upstreamOrigin();
  const incoming = new URL(req.url || "/api", "https://theearnalism.com");
  const rewrittenPaths = incoming.searchParams.getAll("proxy_path");
  if (rewrittenPaths.length > 1) {
    res.statusCode = 400;
    res.end();
    return;
  }
  if (rewrittenPaths.length === 1) {
    const routePath = rewrittenPaths[0];
    const segments = routePath.split("/");
    if (!routePath || routePath.startsWith("/") || segments.some((segment) => !segment || segment === "." || segment === "..")
      || /[?#\\\u0000-\u001f]/.test(routePath) || /%(?:2e|2f|5c)/i.test(routePath)) {
      res.statusCode = 400;
      res.end();
      return;
    }
    incoming.pathname = `/api/${routePath}`;
    incoming.searchParams.delete("proxy_path");
  }
  if (incoming.pathname === "/api/not-found") {
    require("./not-found")(req, res);
    return;
  }
  if (incoming.pathname === "/api/removed-content") {
    require("./removed-content")({
      url: req.url,
      headers: req.headers || {},
      query: { path: incoming.searchParams.get("path") || req.query?.path },
    }, res);
    return;
  }
  if (!origin || !incoming.pathname.startsWith("/api/")) {
    res.statusCode = 503;
    res.end();
    return;
  }

  const headers = new Headers();
  for (const [name, value] of Object.entries(req.headers || {})) {
    if (!value || ["host", "connection", "content-length"].includes(name.toLowerCase())) continue;
    headers.set(name, Array.isArray(value) ? value.join(",") : value);
  }

  const protectedPath = protectedReaderPath(incoming.pathname);
  if (protectedPath) {
    const secret = process.env.EARNALISM_RELEASE_PROXY_SECRET || "";
    if (secret.length < 32) {
      res.statusCode = 503;
      res.setHeader("Cache-Control", "no-store");
      res.end();
      return;
    }
    const country = String(req.headers?.["x-vercel-ip-country"] || "").trim().toUpperCase();
    if (!AUTHORIZED_READER_COUNTRIES.has(country)) {
      res.statusCode = 451;
      res.setHeader("Cache-Control", "no-store");
      res.end();
      return;
    }
    const timestamp = Math.floor(Date.now() / 1000);
    headers.set(SCOPE_HEADER, PUBLIC_RELEASE_SCOPE);
    headers.set(COUNTRY_HEADER, country);
    headers.set(TIMESTAMP_HEADER, String(timestamp));
    headers.set(SIGNATURE_HEADER, releaseSignature(secret, req.method || "GET", incoming.pathname, PUBLIC_RELEASE_SCOPE, timestamp, country));
  }

  try {
    const body = ["GET", "HEAD"].includes(req.method || "GET") ? undefined : await requestBody(req);
    const response = await fetch(`${origin}${incoming.pathname}${incoming.search}`, {
      method: req.method || "GET",
      headers,
      body,
    });
    res.statusCode = response.status;
    for (const [name, value] of response.headers.entries()) {
      if (!["connection", "transfer-encoding"].includes(name.toLowerCase())) res.setHeader(name, value);
    }
    if (protectedPath) {
      // Never let a response cached in one country bypass the next request's
      // country and hash-bound rights checks.
      res.setHeader("Cache-Control", "private, no-store");
      res.setHeader("CDN-Cache-Control", "no-store");
      res.setHeader("Vercel-CDN-Cache-Control", "no-store");
    }
    res.end(Buffer.from(await response.arrayBuffer()));
  } catch (error) {
    console.error("release proxy upstream request failed", { path: incoming.pathname, method: req.method, message: error?.message || "request failed" });
    res.statusCode = 502;
    res.setHeader("Cache-Control", "no-store");
    res.end();
  }
};

module.exports.protectedReaderPath = protectedReaderPath;
module.exports.releaseSignature = releaseSignature;
