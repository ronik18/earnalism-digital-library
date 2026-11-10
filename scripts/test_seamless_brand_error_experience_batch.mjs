#!/usr/bin/env node
import assert from "node:assert/strict";
import fs from "node:fs";
import crypto from "node:crypto";
import os from "node:os";
import path from "node:path";
import { loadStateManifest, selectStateRecords } from "./lib/seamless_brand_state_manifest.mjs";
import { stateOutputDirectory, validateCaptureSummary } from "./lib/seamless_brand_one_state_capture.mjs";

const root = process.cwd();
const expectedReleasedSlugs = [
  "a-ghost-story",
  "the-tell-tale-heart",
  "radharani",
  "a-white-heron",
  "the-gift-of-the-magi",
  "the-canterville-ghost",
  "the-adventures-of-sherlock-holmes",
  "agentic-ai-with-python",
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
  "dracula",
  "book-edfcf810c5",
  "muchiram-gurer-jibanchorit",
  "bn-059",
  "the-call-of-the-wild",
  "the-student",
  "the-art-of-money-getting",
  "bn-035",
  "alices-adventures-in-wonderland",
  "dsires-baby",
  "sredni-vashtar",
  "the-cop-and-the-anthem",
  "the-open-window",
  "the-selfish-giant",
  "the-science-of-getting-rich",
  "bn-066",
  "lokrahasya",
  "mrinalini",
  "frankenstein",
  "pride-and-prejudice",
  "the-great-gatsby",
  "the-secret-garden",
  "the-time-machine",
  "acres-of-diamonds",
  "my-life-and-work",
  "the-principles-of-scientific-management",
  "the-wonderful-wizard-of-oz",
  "book-5704b31005"
];
// Exact added release scope, independently pinned from the SEO contract.
expectedReleasedSlugs.push(...["a-retrieved-reformation", "a-wagner-matinee", "feathertop", "markheim", "rappaccinis-daughter", "the-adventure-of-the-abbey-grange", "the-adventure-of-the-beryl-coronet", "the-adventure-of-the-blue-carbuncle", "the-adventure-of-the-copper-beeches", "the-adventure-of-the-dancing-men", "the-adventure-of-the-empty-house", "the-adventure-of-the-engineers-thumb", "the-adventure-of-the-final-problem", "the-adventure-of-the-greek-interpreter", "the-adventure-of-the-noble-bachelor", "the-adventure-of-the-priory-school", "the-adventure-of-the-second-stain", "the-adventure-of-the-solitary-cyclist", "the-ambitious-guest", "the-bet", "the-celebrated-jumping-frog-of-calaveras-county", "the-country-of-the-blind", "the-darling", "the-door-in-the-wall", "the-furnished-room", "the-imp-of-the-perverse", "the-last-leaf", "the-legend-of-sleepy-hollow", "the-luck-of-roaring-camp", "the-man-in-a-case", "the-man-with-the-twisted-lip", "the-masque-of-the-red-death", "the-ministers-black-veil", "the-murders-in-the-rue-morgue", "the-outcasts-of-poker-flat", "the-purloined-letter", "the-ransom-of-red-chief", "the-speckled-band", "the-suicide-club", "the-yellow-wallpaper", "to-build-a-fire", "tobermory", "ward-no-6", "white-fang", "young-goodman-brown"]);
const manifest = loadStateManifest(path.join(root, "docs/design-system/seamless-brand-state-manifest.json"));
const ids = ["error-404-desktop", "error-404-mobile", "tombstone-410-desktop", "tombstone-410-mobile", "secondary-book-desktop", "secondary-book-mobile", "reader-desktop", "listener-unavailable-desktop", "disabled-listener-dracula-desktop"];
const selected = selectStateRecords(manifest, ids); let cases = 0;
function test(name, fn) { fn(); cases += 1; console.log(`PASS ${cases}: ${name}`); }
test("exactly nine new state IDs resolve", () => assert.deepEqual(manifest.states.filter((s) => s.introduced_in === "error-experience-2b4").map((s) => s.id), ids));
test("prior manifest IDs remain present", () => assert.ok(manifest.states.length - selected.length >= 28));
test("reverse-order filter executes in manifest order", () => assert.deepEqual(selectStateRecords(manifest, [...ids].reverse()).map((s) => s.id), ids));
test("404 route is not a real route", () => assert.equal(manifest.states.filter((s) => s.route === "/__seamless-brand-review-not-found-344__").length, 2));
test("selected 410 route exists in tombstone authority", () => assert.match(fs.readFileSync(path.join(root, "scripts/serve_frontend_build.js"), "utf8"), /patterned-wrap-dress/));
test("static SEO contract exposes only the ninety-seven accepted India text releases", () => {
  const contract = JSON.parse(fs.readFileSync(path.join(root, "frontend/static-seo/controlled-publication-public.json"), "utf8"));
  assert.equal(contract.public_release_held, false);
  assert.deepEqual(
    contract.publications.map((publication) => publication.slug).sort(),
    [...expectedReleasedSlugs].sort(),
  );
});
// These are static fixture contracts and explicit local fault injections.
// Historical capture reports remain evidence for their original exact heads;
// this test does not claim a fresh browser or production observation.
test("Reader and disabled Listener manifest fixtures retain their exact routes", () => {
  for (const [id, route, fixture] of [
    ["reader-desktop", "/reader/a-ghost-story", "reader-visual-safe"],
    ["listener-unavailable-desktop", "/listener/a-ghost-story", "listener-non-playable"],
    ["disabled-listener-dracula-desktop", "/listener/dracula", "listener-disabled-safe"],
  ]) {
    const state = selected.find((item) => item.id === id);
    assert.equal(state.route, route);
    assert.equal(state.fixture, fixture);
  }
});
test("current release projection limits audio to the exact protected-package titles", () => {
  const launch = JSON.parse(fs.readFileSync(path.join(root, "data/controlled_launch.json"), "utf8"));
  assert.equal(launch.public_audio_exposure_enabled, false);
  assert.deepEqual(launch.audio_enabled_slugs, []);
  assert.deepEqual(launch.protected_package_public_slugs, ["the-open-window", "the-selfish-giant"]);
  assert.deepEqual(launch.live_approved_slugs, expectedReleasedSlugs);
  for (const slug of expectedReleasedSlugs) {
    const publication = JSON.parse(fs.readFileSync(path.join(root, "data/controlled_publications", slug, "publication_manifest.json"), "utf8"));
    assert.equal(publication.reader_release.exposed, true, slug);
    assert.equal(publication.audio_release.exposed, launch.protected_package_public_slugs.includes(slug), slug);
    if (launch.protected_package_public_slugs.includes(slug)) assert.equal(publication.audio_release.delivery_mode, "PROTECTED_PACKAGE_V2");
  }
});
const temporary = fs.mkdtempSync(path.join(os.tmpdir(), "error-experience-summary-unit-"));
function syntheticSummary(name) {
  const output = path.join(temporary, name);
  for (const state of selected) {
    const directory = stateOutputDirectory(output, state.id);
    fs.mkdirSync(directory, { recursive: true });
    // Explicit synthetic nonvisual bytes: only the storage/hash validator is tested.
    const bytes = Buffer.from(`synthetic capture storage ${state.id}`);
    fs.writeFileSync(path.join(directory, "viewport.png"), bytes);
    fs.writeFileSync(path.join(directory, "metadata.json"), JSON.stringify({
      state_id: state.id, stable: true, screenshot_paths: { viewport: "viewport.png" },
      screenshot_sha256: { viewport: crypto.createHash("sha256").update(bytes).digest("hex") },
    }));
  }
  return { output, summary: { requested_state_ids: ids, captured_state_ids: ids,
    missing_state_ids: [], unexpected_state_ids: [], duplicate_state_ids: [],
    stable_state_count: 9, unstable_state_count: 0 } };
}
try {
  test("synthetic nine-state storage passes the shared summary validator", () => {
    const { output, summary } = syntheticSummary("valid");
    assert.equal(validateCaptureSummary(summary, output, 9).length, 9);
  });
  test("missing state metadata fails the shared summary validator", () => {
    const { output, summary } = syntheticSummary("missing");
    fs.rmSync(path.join(stateOutputDirectory(output, ids[8]), "metadata.json"));
    assert.throws(() => validateCaptureSummary(summary, output, 9), /metadata is missing/);
  });
  test("unstable state fails the shared summary validator", () => {
    const { output, summary } = syntheticSummary("unstable");
    summary.stable_state_count = 8; summary.unstable_state_count = 1;
    assert.throws(() => validateCaptureSummary(summary, output, 9), /unstable/);
  });
  test("tampered capture bytes fail the shared summary validator", () => {
    const { output, summary } = syntheticSummary("tampered");
    fs.appendFileSync(path.join(stateOutputDirectory(output, ids[0]), "viewport.png"), "tampered");
    assert.throws(() => validateCaptureSummary(summary, output, 9), /SHA mismatch/);
  });
} finally { fs.rmSync(temporary, { recursive: true, force: true }); }
console.log(JSON.stringify({ result: "PASS", testCaseCount: cases }));
