#!/usr/bin/env node
import assert from "node:assert/strict";
import fs from "node:fs";
import path from "node:path";

const root = process.cwd();
const read = (relative) => fs.readFileSync(path.join(root, relative), "utf8");
const cases = [];
const test = (name, callback) => {
  callback();
  cases.push(name);
  console.log(`PASS ${cases.length}: ${name}`);
};

const account = read("frontend/src/pages/Account.jsx");
const accountStyles = read("frontend/src/styles/auth-account.css");
const book = read("frontend/src/pages/BookDetailReference.css");
const reader = read("frontend/src/experiences-v2/reader/reader-v2.css");
const listener = read("frontend/src/experiences-v2/listener/listener-v2.css");
const shared = read("frontend/src/experiences-v2/shared/experiences-v2.css");
const generator = read("scripts/generate_seamless_brand_final_owner_review.py");

test("Account fixture supplies visible desktop profile structure", () => {
  assert.match(account, /function AccountVisualFixture\(\)/);
  assert.match(account, /account-visual-fixture__desktop/);
  assert.match(account, /account-visual-fixture-title/);
  assert.match(account, /Reading Pass/);
  assert.match(account, /Recent activity/);
  assert.match(accountStyles, /\.account-visual-fixture__desktop/);
});

test("Account fixture stays compile-time gated and sanitized", () => {
  assert.match(account, /REACT_APP_ENABLE_VISUAL_FIXTURES === "1"/);
  assert.match(account, /review@example\.invalid/);
  const fixture = account.slice(account.indexOf("function AccountVisualFixture"), account.indexOf("export default function Account"));
  assert.doesNotMatch(fixture, /userApi|getReadingPass|refreshUser|trackFunnelEvent/);
});

test("Book Detail uses the Gilded Burgundy token family", () => {
  assert.match(book, /--book-reference-ink: var\(--burgundy-950/);
  assert.match(book, /--book-reference-surface: var\(--burgundy-900/);
  assert.match(book, /--book-reference-gold: var\(--gold-400/);
  assert.doesNotMatch(book, /#07110f|#0c1916|#081612|#0d1b17|#10201b|#10231d|#101b17/i);
});

test("Reader and Listener remove legacy green-derived surfaces", () => {
  assert.match(reader, /background: var\(--ev2-surface\)/);
  assert.doesNotMatch(reader, /#0c1714|#20342d/i);
  assert.match(listener, /\.listener-v2__art \{ background: var\(--ev2-surface\); \}/);
  assert.doesNotMatch(shared, /#091310|#fbf7ef|#d5ad56/i);
});

test("Listener mobile content follows the shared masthead without stale spacer", () => {
  assert.match(listener, /\.listener-v2 \.experience-header \{ display: flex !important; \}/);
  assert.match(listener, /\.listener-v2__main \{ padding: 12px 24px 26px; \}/);
});

test("Owner-review PDF reserves a full-scale Devdas page", () => {
  assert.match(generator, /\("Book Detail — Dracula", \["book-detail-desktop"\]\)/);
  assert.match(generator, /\("Book Detail — Devdas \(Bengali\)", \["secondary-book-desktop"\]\)/);
  assert.doesNotMatch(generator, /secondary-book-detail-desktop/);
});

test("Book Detail fixture serves the requested approved route and rejects a missing book page", () => {
  const capture = read("scripts/capture_seamless_brand_owner_review.mjs");
  assert.match(capture, /const requestedBook = requestUrl\.pathname\.match/);
  assert.match(capture, /books\.find\(\(entry\) => entry\.slug === decodeURIComponent\(requestedBook\)\)/);
  assert.match(capture, /book-detail-fixture-contract/);
});

console.log(JSON.stringify({ result: "PASS", test_case_count: cases.length, cases }));
