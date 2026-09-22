const crypto = require("node:crypto");

const SCOPE_HEADER = "x-earnalism-release-scope";
const TIMESTAMP_HEADER = "x-earnalism-release-timestamp";
const SIGNATURE_HEADER = "x-earnalism-release-signature";
const DEFAULT_UPSTREAM = "https://api.theearnalism.com";
const PUBLIC_RELEASE_SCOPE = "PUBLIC";

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

function releaseSignature(secret, method, pathname, scope, timestamp) {
  return crypto.createHmac("sha256", secret)
    .update(`${method.toUpperCase()}\\n${pathname}\\n${scope}\\n${timestamp}`)
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

  if (protectedReaderPath(incoming.pathname)) {
    const secret = process.env.EARNALISM_RELEASE_PROXY_SECRET || "";
    if (secret.length < 32) {
      res.statusCode = 503;
      res.setHeader("Cache-Control", "no-store");
      res.end();
      return;
    }
    const timestamp = Math.floor(Date.now() / 1000);
    headers.set(SCOPE_HEADER, PUBLIC_RELEASE_SCOPE);
    headers.set(TIMESTAMP_HEADER, String(timestamp));
    headers.set(SIGNATURE_HEADER, releaseSignature(secret, req.method || "GET", incoming.pathname, PUBLIC_RELEASE_SCOPE, timestamp));
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
