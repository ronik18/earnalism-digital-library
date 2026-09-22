const assert = require("node:assert/strict");
const test = require("node:test");
const fs = require("node:fs");
const path = require("node:path");
const releaseProxy = require("./[...proxy]");
const { protectedReaderPath, releaseSignature } = releaseProxy;

test("release proxy signs only the fixed Reader/catalogue surface", () => {
  assert.equal(protectedReaderPath("/api/books"), true);
  assert.equal(protectedReaderPath("/api/reader/book/a-ghost-story/manifest"), true);
  assert.equal(protectedReaderPath("/api/reading-pass/books/a-ghost-story/manifest"), true);
  assert.equal(protectedReaderPath("/api/admin/books"), false);
  assert.equal(protectedReaderPath("/api/payments/topup"), false);
});

test("protected home API paths cannot be CDN-cached across territories", () => {
  const vercel = JSON.parse(fs.readFileSync(path.join(__dirname, "../vercel.json"), "utf8"));
  assert.equal(vercel.rewrites.some((entry) => entry.source === "/api/(.*)" && entry.destination.startsWith("https://")), false, "external API rewrite bypasses the signed proxy");
  assert.ok(vercel.rewrites.some((entry) => entry.source === "/api/(.*)" && entry.destination === "/api/[...proxy]?proxy_path=$1"), "nested API routes must reach the signed function");
  for (const source of ["/api/home/curated", "/api/home/hero", "/api/home/listening"]) {
    const rule = vercel.headers.find((entry) => entry.source === source);
    assert.deepEqual(rule.headers, [{ key: "Cache-Control", value: "private, no-store" }]);
  }
});

test("same-app nested rewrite signs the actual Reader path and preserves its query", async () => {
  const previousSecret = process.env.EARNALISM_RELEASE_PROXY_SECRET;
  const previousFetch = global.fetch;
  process.env.EARNALISM_RELEASE_PROXY_SECRET = "release-proxy-test-secret-that-is-long-enough";
  let forwardedUrl;
  let forwardedHeaders;
  global.fetch = async (url, options) => {
    forwardedUrl = url;
    forwardedHeaders = options.headers;
    return { status: 204, headers: new Headers(), arrayBuffer: async () => new ArrayBuffer(0) };
  };
  try {
    const response = { statusCode: 200, headers: {}, setHeader(key, value) { this.headers[key] = value; }, end() {} };
    await releaseProxy({ url: "/api/[...proxy]?proxy_path=reader/book/a-ghost-story/manifest&chapter=1", method: "GET", headers: { "x-vercel-ip-country": "IN" } }, response);
    assert.equal(response.statusCode, 204);
    assert.equal(forwardedUrl, "https://api.theearnalism.com/api/reader/book/a-ghost-story/manifest?chapter=1");
    assert.equal(forwardedHeaders.get("x-earnalism-release-scope"), "PUBLIC");
    assert.equal(forwardedHeaders.get("x-earnalism-release-country"), "IN");
    assert.match(forwardedHeaders.get("x-earnalism-release-signature"), /^[a-f0-9]{64}$/);
    assert.equal(response.headers["Cache-Control"], "private, no-store");
  } finally {
    global.fetch = previousFetch;
    if (previousSecret === undefined) delete process.env.EARNALISM_RELEASE_PROXY_SECRET;
    else process.env.EARNALISM_RELEASE_PROXY_SECRET = previousSecret;
  }
});

test("retired local routes remain branded tombstones if the API rewrite matches them", async () => {
  const response = { statusCode: 200, headers: {}, setHeader(key, value) { this.headers[key] = value; }, end(body) { this.body = body; } };
  await releaseProxy({ url: "/api/[...proxy]?proxy_path=removed-content&path=/shop", method: "GET", headers: {} }, response);
  assert.equal(response.statusCode, 410);
  assert.match(response.body, /This page is no longer available/);
  assert.equal(response.headers["X-Robots-Tag"], "noindex, nofollow, noarchive");
});

test("release proxy canonical signature binds method, exact path, scope, timestamp and country", () => {
  const secret = "release-proxy-test-secret-that-is-long-enough";
  const signature = releaseSignature(secret, "GET", "/api/books", "PUBLIC", 1_790_092_800, "IN");
  assert.match(signature, /^[a-f0-9]{64}$/);
  assert.notEqual(signature, releaseSignature(secret, "GET", "/api/books", "OTHER", 1_790_092_800, "IN"));
  assert.notEqual(signature, releaseSignature(secret, "HEAD", "/api/books", "PUBLIC", 1_790_092_800, "IN"));
  assert.notEqual(signature, releaseSignature(secret, "GET", "/api/books/other", "PUBLIC", 1_790_092_800, "IN"));
  assert.notEqual(signature, releaseSignature(secret, "GET", "/api/books", "PUBLIC", 1_790_092_800, "US"));
});

test("uncleared or unknown territory cannot reach the upstream Reader API", async () => {
  const previousSecret = process.env.EARNALISM_RELEASE_PROXY_SECRET;
  const previousFetch = global.fetch;
  process.env.EARNALISM_RELEASE_PROXY_SECRET = "release-proxy-test-secret-that-is-long-enough";
  let calls = 0;
  global.fetch = async () => { calls += 1; throw new Error("must not fetch"); };
  try {
    for (const country of ["US", "GB", "", "ZZ"]) {
      const response = { statusCode: 200, headers: {}, setHeader(key, value) { this.headers[key] = value; }, end() {} };
      await releaseProxy({ url: "/api/reader/book/a-ghost-story/manifest", method: "GET", headers: { "x-vercel-ip-country": country } }, response);
      assert.equal(response.statusCode, 451);
      assert.equal(response.headers["Cache-Control"], "no-store");
    }
    assert.equal(calls, 0);
  } finally {
    global.fetch = previousFetch;
    if (previousSecret === undefined) delete process.env.EARNALISM_RELEASE_PROXY_SECRET;
    else process.env.EARNALISM_RELEASE_PROXY_SECRET = previousSecret;
  }
});

test("India request forwards the proxy-observed country in the signed assertion", async () => {
  const previousSecret = process.env.EARNALISM_RELEASE_PROXY_SECRET;
  const previousFetch = global.fetch;
  process.env.EARNALISM_RELEASE_PROXY_SECRET = "release-proxy-test-secret-that-is-long-enough";
  let forwarded;
  global.fetch = async (_url, options) => {
    forwarded = options.headers;
    return { status: 204, headers: new Headers(), arrayBuffer: async () => new ArrayBuffer(0) };
  };
  try {
    const response = { statusCode: 200, headers: {}, setHeader(key, value) { this.headers[key] = value; }, end() {} };
    await releaseProxy({ url: "/api/books", method: "GET", headers: { "x-vercel-ip-country": "IN", "x-earnalism-release-country": "US" } }, response);
    assert.equal(response.statusCode, 204);
    assert.equal(forwarded.get("x-earnalism-release-country"), "IN");
    assert.equal(forwarded.get("x-earnalism-release-scope"), "PUBLIC");
    assert.match(forwarded.get("x-earnalism-release-signature"), /^[a-f0-9]{64}$/);
    assert.equal(response.headers["Cache-Control"], "private, no-store");
    assert.equal(response.headers["Vercel-CDN-Cache-Control"], "no-store");
  } finally {
    global.fetch = previousFetch;
    if (previousSecret === undefined) delete process.env.EARNALISM_RELEASE_PROXY_SECRET;
    else process.env.EARNALISM_RELEASE_PROXY_SECRET = previousSecret;
  }
});
