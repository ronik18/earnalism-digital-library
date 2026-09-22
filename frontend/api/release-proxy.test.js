const assert = require("node:assert/strict");
const test = require("node:test");
const { protectedReaderPath, releaseSignature } = require("./[...proxy]");

test("release proxy signs only the fixed Reader/catalogue surface", () => {
  assert.equal(protectedReaderPath("/api/books"), true);
  assert.equal(protectedReaderPath("/api/reader/book/a-ghost-story/manifest"), true);
  assert.equal(protectedReaderPath("/api/reading-pass/books/a-ghost-story/manifest"), true);
  assert.equal(protectedReaderPath("/api/admin/books"), false);
  assert.equal(protectedReaderPath("/api/payments/topup"), false);
});

test("release proxy canonical signature binds method, exact path, country, and timestamp", () => {
  const secret = "release-proxy-test-secret-that-is-long-enough";
  const signature = releaseSignature(secret, "GET", "/api/books", "IN", 1_790_092_800);
  assert.match(signature, /^[a-f0-9]{64}$/);
  assert.notEqual(signature, releaseSignature(secret, "GET", "/api/books", "US", 1_790_092_800));
  assert.notEqual(signature, releaseSignature(secret, "HEAD", "/api/books", "IN", 1_790_092_800));
  assert.notEqual(signature, releaseSignature(secret, "GET", "/api/books/other", "IN", 1_790_092_800));
});
