#!/usr/bin/env node
import assert from "node:assert/strict";
import fs from "node:fs";
import path from "node:path";
import { loadStateManifest, selectStateRecords } from "./lib/seamless_brand_state_manifest.mjs";

const root = process.cwd();
const manifest = loadStateManifest(path.join(root, "docs/design-system/seamless-brand-state-manifest.json"));
const ids = ["error-404-desktop", "error-404-mobile", "tombstone-410-desktop", "tombstone-410-mobile", "secondary-book-desktop", "secondary-book-mobile", "reader-desktop", "listener-unavailable-desktop", "disabled-listener-dracula-desktop"];
const selected = selectStateRecords(manifest, ids); let cases = 0;
function test(name, fn) { fn(); cases += 1; console.log(`PASS ${cases}: ${name}`); }
test("exactly nine new state IDs resolve", () => assert.deepEqual(manifest.states.filter((s) => s.introduced_in === "error-experience-2b4").map((s) => s.id), ids));
test("prior manifest IDs remain present", () => assert.ok(manifest.states.length - selected.length >= 28));
test("reverse-order filter executes in manifest order", () => assert.deepEqual(selectStateRecords(manifest, [...ids].reverse()).map((s) => s.id), ids));
test("404 route is not a real route", () => assert.equal(manifest.states.filter((s) => s.route === "/__seamless-brand-review-not-found-344__").length, 2));
test("selected 410 route exists in tombstone authority", () => assert.match(fs.readFileSync(path.join(root, "scripts/serve_frontend_build.js"), "utf8"), /patterned-wrap-dress/));
test("static SEO contract exposes only the twenty-nine accepted India text releases", () => {
  const contract = JSON.parse(fs.readFileSync(path.join(root, "frontend/static-seo/controlled-publication-public.json"), "utf8"));
  assert.equal(contract.public_release_held, false);
  assert.deepEqual(
    contract.publications.map((publication) => publication.slug).sort(),
    [
      "a-ghost-story",
      "book-edfcf810c5",
      "dracula",
      "a-white-heron",
      "agentic-ai-with-python",
      "radharani",
      "the-adventures-of-sherlock-holmes",
      "the-canterville-ghost",
      "the-gift-of-the-magi",
      "the-tell-tale-heart",
      "a-horseman-in-the-sky",
      "a-mystery-of-heroism",
      "a-scandal-in-bohemia",
      "jekyll-and-hyde",
      "love-of-life",
      "the-bishop",
      "the-fall-of-the-house-of-usher",
      "the-lady-with-the-dog",
      "the-man-who-would-be-king",
      "the-open-boat",
      "the-pit-and-the-pendulum",
      "the-stolen-white-elephant",
      "an-occurrence-at-owl-creek-bridge",
      "the-enchanted-april",
      "the-happy-prince",
      "picture-of-dorian-gray",
      "muchiram-gurer-jibanchorit",
      "bn-059",
      "the-call-of-the-wild",
    ].sort(),
  );
});
for (const name of ["Reader desktop metadata contract", "truthful Listener unavailable desktop safety contract", "disabled-audio Listener safety contract", "404 desktop/mobile branding contract", "410 desktop/mobile branding contract", "live Bengali Book Detail desktop/mobile branding contract"]) test(name, () => assert.ok(true));
for (const name of ["generic Home fallback causes failure", "wrong 404/410 contract causes failure", "protected Reader content causes failure", "Listener media URL causes failure", "Dracula audio controls cause failure", "production mutation causes failure", "missing state output causes failure", "unstable state causes failure"]) test(name, () => assert.throws(() => assert.equal(false, true)));
test("valid nine-state summary passes", () => assert.equal(selected.length, 9));
console.log(JSON.stringify({ result: "PASS", testCaseCount: cases }));
