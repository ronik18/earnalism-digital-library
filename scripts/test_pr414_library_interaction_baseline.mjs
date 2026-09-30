#!/usr/bin/env node
import assert from "node:assert/strict";
import { execFileSync } from "node:child_process";
import fs from "node:fs";
import os from "node:os";
import path from "node:path";
import {
  PR399_LIBRARY_INTERACTION_BASELINE,
  PR414_LIBRARY_INTERACTION_BASELINE,
  PR416_LIBRARY_INTERACTION_BASELINE,
  HOME_SECTIONS_LIBRARY_INTERACTION_BASELINE,
  INDIA_COMMERCIAL_CUTOVER_HOME_LIBRARY_INTERACTION_BASELINE,
  PR438_READING_ROOM_HOME_LIBRARY_INTERACTION_BASELINE,
  PR457_READING_PASS_HOME_LIBRARY_INTERACTION_BASELINE,
  PR462_APPROVED_HOMEPAGE_LIBRARY_INTERACTION_BASELINE,
  PR466_APPROVED_OPTION_B_HOMEPAGE_LIBRARY_INTERACTION_BASELINE,
  PR467_APPROVED_OPTION_B_HOMEPAGE_LIBRARY_INTERACTION_BASELINE,
  PR468_LISTENING_ROOM_HOMEPAGE_LIBRARY_INTERACTION_BASELINE,
  PR469_POSTMERGE_LIBRARY_RECOVERY_BASELINE,
  compareLibraryInteractionBaseline,
  loadLibraryInteractionBaseline,
} from "./lib/library_interaction_baseline.mjs";

const root = process.cwd();
const baselinePath = path.join(root, PR414_LIBRARY_INTERACTION_BASELINE);
const read = (file) => fs.readFileSync(file, "utf8");
const write = (file, value) => fs.writeFileSync(file, `${JSON.stringify(value, null, 2)}\n`);
const sourceAt = (revision, relativePath) => execFileSync("git", ["show", `${revision}:${relativePath}`], { cwd: root, encoding: "utf8" });
const materializeReviewedSurface = (recordPath = PR414_LIBRARY_INTERACTION_BASELINE) => {
  const temporary = fs.mkdtempSync(path.join(os.tmpdir(), "pr414-library-surface-"));
  const sourceRecord = path.join(root, recordPath);
  const baseline = JSON.parse(read(sourceRecord));
  for (const relativePath of baseline.input_paths) {
    const destination = path.join(temporary, relativePath);
    fs.mkdirSync(path.dirname(destination), { recursive: true });
    fs.writeFileSync(destination, sourceAt(baseline.reviewed_source.commit, relativePath));
  }
  const record = path.join(temporary, recordPath);
  fs.mkdirSync(path.dirname(record), { recursive: true });
  fs.copyFileSync(sourceRecord, record);
  return temporary;
};
let cases = 0;
const test = (name, fn) => { fn(); cases += 1; console.log(`PASS ${cases}: ${name}`); };

test("the explicit PR414 baseline matches the reviewed fail-closed Library source", () => {
  const baseline = loadLibraryInteractionBaseline(root, PR414_LIBRARY_INTERACTION_BASELINE);
  const comparison = compareLibraryInteractionBaseline(materializeReviewedSurface(), PR414_LIBRARY_INTERACTION_BASELINE);
  assert.equal(comparison.expected_surface_sha256, "7bd2fc4b5dc9dcac43a1a9a4086c92075d9ea5443262e77b99385841f66853f4");
  assert.equal(comparison.observed_surface_sha256, comparison.expected_surface_sha256);
  assert.equal(comparison.previous_surface_sha256, "eb5b100dd080afb4213e86f9b91b711bbe442b8a82071161dc9f44cd89ea9738");
  assert.equal(comparison.result, "PASS");
  assert.equal(baseline.owner_authorization.capture_is_not_expected_value_authority, true);
});

test("a changed held-release Library input is rejected", () => {
  const temporary = materializeReviewedSurface();
  fs.appendFileSync(path.join(temporary, "frontend/src/pages/Library.jsx"), "\n// fixture-only source change\n");
  assert.equal(compareLibraryInteractionBaseline(temporary, PR414_LIBRARY_INTERACTION_BASELINE).result, "FAIL");
});

test("wrong predecessor, source provenance, and authorization are rejected", () => {
  const temporary = materializeReviewedSurface();
  const record = path.join(temporary, PR414_LIBRARY_INTERACTION_BASELINE);
  for (const mutate of [
    (value) => { value.previous_baseline.record_path = PR399_LIBRARY_INTERACTION_BASELINE.replace("pr399", "pr397"); },
    (value) => { value.reviewed_source.tree = "0".repeat(40); },
    (value) => { value.owner_authorization.reference = "UNAUTHORIZED"; },
  ]) {
    const value = JSON.parse(read(record));
    mutate(value); write(record, value);
    assert.throws(() => loadLibraryInteractionBaseline(temporary, PR414_LIBRARY_INTERACTION_BASELINE));
    fs.copyFileSync(baselinePath, record);
  }
});

test("the historical PR399 baseline remains byte-for-byte unchanged", () => {
  assert.equal(read(path.join(root, PR399_LIBRARY_INTERACTION_BASELINE)), sourceAt("b6bb598457c3a425c1b8dc77c78db431a95b36e0", PR399_LIBRARY_INTERACTION_BASELINE));
});

test("the owner-authorized PR416 Home shelf transition remains valid at its reviewed source", () => {
  const comparison = compareLibraryInteractionBaseline(materializeReviewedSurface(PR416_LIBRARY_INTERACTION_BASELINE), PR416_LIBRARY_INTERACTION_BASELINE);
  assert.equal(comparison.previous_surface_sha256, "7bd2fc4b5dc9dcac43a1a9a4086c92075d9ea5443262e77b99385841f66853f4");
  assert.equal(comparison.expected_surface_sha256, "29dc1e90c0fbf4bffcd9edbdd1878c94c2647d039528878c70bb15669f90366f");
  assert.equal(comparison.result, "PASS");
});

test("the original approved Home sections baseline remains intact at its reviewed source", () => {
  const comparison = compareLibraryInteractionBaseline(materializeReviewedSurface(HOME_SECTIONS_LIBRARY_INTERACTION_BASELINE), HOME_SECTIONS_LIBRARY_INTERACTION_BASELINE);
  assert.equal(comparison.previous_surface_sha256, "29dc1e90c0fbf4bffcd9edbdd1878c94c2647d039528878c70bb15669f90366f");
  assert.equal(comparison.expected_surface_sha256, "3cbf2dda50902d4745849eb8157af447cf26af0ceb17e93ba9aaf604e621ffc7");
  assert.equal(comparison.result, "PASS");
});

test("the directly authorized India commercial copy transition matches the current Home and Library source", () => {
  const comparison = compareLibraryInteractionBaseline(materializeReviewedSurface(INDIA_COMMERCIAL_CUTOVER_HOME_LIBRARY_INTERACTION_BASELINE), INDIA_COMMERCIAL_CUTOVER_HOME_LIBRARY_INTERACTION_BASELINE);
  assert.equal(comparison.previous_surface_sha256, "3cbf2dda50902d4745849eb8157af447cf26af0ceb17e93ba9aaf604e621ffc7");
  assert.equal(comparison.expected_surface_sha256, "c2f93da984c39f54915df94541f98ce1931e128781b9a9c69621d66b57ac1846");
  assert.equal(comparison.result, "PASS");
});

test("the approved PR438 Reading Room transition matches the current Home source", () => {
  const baseline = loadLibraryInteractionBaseline(root, PR438_READING_ROOM_HOME_LIBRARY_INTERACTION_BASELINE);
  const comparison = compareLibraryInteractionBaseline(materializeReviewedSurface(PR438_READING_ROOM_HOME_LIBRARY_INTERACTION_BASELINE), PR438_READING_ROOM_HOME_LIBRARY_INTERACTION_BASELINE);
  assert.equal(comparison.previous_surface_sha256, "c2f93da984c39f54915df94541f98ce1931e128781b9a9c69621d66b57ac1846");
  assert.equal(comparison.expected_surface_sha256, "70b37008d929f09caa09041e42a7619081932bf66bca698fd2f907deb18f6fb0");
  assert.equal(comparison.result, "PASS");
  assert.equal(baseline.owner_authorization.capture_is_not_expected_value_authority, true);
});

test("the historical PR467 Option B baseline remains valid at its reviewed source", () => {
  const baseline = loadLibraryInteractionBaseline(root, PR467_APPROVED_OPTION_B_HOMEPAGE_LIBRARY_INTERACTION_BASELINE);
  const comparison = compareLibraryInteractionBaseline(materializeReviewedSurface(PR467_APPROVED_OPTION_B_HOMEPAGE_LIBRARY_INTERACTION_BASELINE), PR467_APPROVED_OPTION_B_HOMEPAGE_LIBRARY_INTERACTION_BASELINE);
  assert.equal(comparison.expected_surface_sha256, "b043c3ca7f6031c035a472cfd534bab49a0d31647c1434e280df87bfd658350b");
  assert.equal(comparison.result, "PASS");
  assert.equal(baseline.owner_authorization.capture_is_not_expected_value_authority, true);
});

test("the approved Track B1 Reading Pass transition matches the current Home source", () => {
  const baseline = loadLibraryInteractionBaseline(root, PR457_READING_PASS_HOME_LIBRARY_INTERACTION_BASELINE);
  const comparison = compareLibraryInteractionBaseline(materializeReviewedSurface(PR457_READING_PASS_HOME_LIBRARY_INTERACTION_BASELINE), PR457_READING_PASS_HOME_LIBRARY_INTERACTION_BASELINE);
  assert.equal(comparison.previous_surface_sha256, "70b37008d929f09caa09041e42a7619081932bf66bca698fd2f907deb18f6fb0");
  assert.equal(comparison.expected_surface_sha256, "632659caafce47f36e3f4b19f2dfd966cef72b899cfd728e2ef8bc5c5c1c403f");
  assert.equal(comparison.result, "PASS");
  assert.equal(baseline.owner_authorization.capture_is_not_expected_value_authority, true);
});

test("an unauthorized Track B1 baseline mutation fails closed", () => {
  const temporary = materializeReviewedSurface(PR457_READING_PASS_HOME_LIBRARY_INTERACTION_BASELINE);
  const record = path.join(temporary, PR457_READING_PASS_HOME_LIBRARY_INTERACTION_BASELINE);
  const value = JSON.parse(read(record));
  value.owner_authorization.reference = "UNAUTHORIZED";
  write(record, value);
  assert.throws(() => loadLibraryInteractionBaseline(temporary, PR457_READING_PASS_HOME_LIBRARY_INTERACTION_BASELINE));
});

test("the historical approved PR462 homepage transition preserves its exact Library interaction baseline", () => {
  const baseline = loadLibraryInteractionBaseline(root, PR462_APPROVED_HOMEPAGE_LIBRARY_INTERACTION_BASELINE);
  const comparison = compareLibraryInteractionBaseline(materializeReviewedSurface(PR462_APPROVED_HOMEPAGE_LIBRARY_INTERACTION_BASELINE), PR462_APPROVED_HOMEPAGE_LIBRARY_INTERACTION_BASELINE);
  assert.equal(comparison.previous_surface_sha256, "632659caafce47f36e3f4b19f2dfd966cef72b899cfd728e2ef8bc5c5c1c403f");
  assert.equal(comparison.expected_surface_sha256, "38f492eb2f1798ffe476470ff78a0be3b580c7fb41f488db73e9ee92a14d6f76");
  assert.equal(comparison.result, "PASS");
  assert.equal(baseline.owner_authorization.capture_is_not_expected_value_authority, true);
});

test("an unauthorized PR462 homepage baseline mutation fails closed", () => {
  const temporary = materializeReviewedSurface(PR462_APPROVED_HOMEPAGE_LIBRARY_INTERACTION_BASELINE);
  const record = path.join(temporary, PR462_APPROVED_HOMEPAGE_LIBRARY_INTERACTION_BASELINE);
  const value = JSON.parse(read(record));
  value.owner_authorization.reference = "UNAUTHORIZED";
  write(record, value);
  assert.throws(() => loadLibraryInteractionBaseline(temporary, PR462_APPROVED_HOMEPAGE_LIBRARY_INTERACTION_BASELINE));
});

test("the approved PR466 Option B homepage transition preserves the exact Library interaction baseline", () => {
  const baseline = loadLibraryInteractionBaseline(root, PR466_APPROVED_OPTION_B_HOMEPAGE_LIBRARY_INTERACTION_BASELINE);
  const comparison = compareLibraryInteractionBaseline(materializeReviewedSurface(PR466_APPROVED_OPTION_B_HOMEPAGE_LIBRARY_INTERACTION_BASELINE), PR466_APPROVED_OPTION_B_HOMEPAGE_LIBRARY_INTERACTION_BASELINE);
  assert.equal(comparison.previous_surface_sha256, "38f492eb2f1798ffe476470ff78a0be3b580c7fb41f488db73e9ee92a14d6f76");
  assert.equal(comparison.expected_surface_sha256, "0de6d2fe1388062cbfbf3c4e6569d0bc6bec13c8ffc31ee73c996d4791ba21e4");
  assert.equal(comparison.result, "PASS");
  assert.equal(baseline.owner_authorization.capture_is_not_expected_value_authority, true);
});

test("the historical PR467 Option B refinement preserves its reviewed Library interaction baseline", () => {
  const baseline = loadLibraryInteractionBaseline(root, PR467_APPROVED_OPTION_B_HOMEPAGE_LIBRARY_INTERACTION_BASELINE);
  const comparison = compareLibraryInteractionBaseline(materializeReviewedSurface(PR467_APPROVED_OPTION_B_HOMEPAGE_LIBRARY_INTERACTION_BASELINE), PR467_APPROVED_OPTION_B_HOMEPAGE_LIBRARY_INTERACTION_BASELINE);
  assert.equal(comparison.previous_surface_sha256, "0de6d2fe1388062cbfbf3c4e6569d0bc6bec13c8ffc31ee73c996d4791ba21e4");
  assert.equal(comparison.expected_surface_sha256, "b043c3ca7f6031c035a472cfd534bab49a0d31647c1434e280df87bfd658350b");
  assert.equal(comparison.result, "PASS");
  assert.equal(baseline.owner_authorization.capture_is_not_expected_value_authority, true);
});

test("the owner-approved PR468 Listening Room homepage transition preserves Library interactions", () => {
  const baseline = loadLibraryInteractionBaseline(root, PR468_LISTENING_ROOM_HOMEPAGE_LIBRARY_INTERACTION_BASELINE);
  const comparison = compareLibraryInteractionBaseline(materializeReviewedSurface(PR468_LISTENING_ROOM_HOMEPAGE_LIBRARY_INTERACTION_BASELINE), PR468_LISTENING_ROOM_HOMEPAGE_LIBRARY_INTERACTION_BASELINE);
  assert.equal(comparison.previous_surface_sha256, "b043c3ca7f6031c035a472cfd534bab49a0d31647c1434e280df87bfd658350b");
  assert.equal(comparison.expected_surface_sha256, "9383db9e233be96bff8426e39a55f51a3b0aa441b3b26176f14df5af66e52f93");
  assert.equal(comparison.result, "PASS");
  assert.equal(baseline.owner_authorization.capture_is_not_expected_value_authority, true);
});

test("the directly requested post-merge Library recovery preserves the approved surface and adds only error/retry behavior", () => {
  const baseline = loadLibraryInteractionBaseline(root, PR469_POSTMERGE_LIBRARY_RECOVERY_BASELINE);
  const comparison = compareLibraryInteractionBaseline(root, PR469_POSTMERGE_LIBRARY_RECOVERY_BASELINE);
  assert.equal(compareLibraryInteractionBaseline(root).approval_source, PR469_POSTMERGE_LIBRARY_RECOVERY_BASELINE);
  assert.equal(comparison.previous_surface_sha256, "9383db9e233be96bff8426e39a55f51a3b0aa441b3b26176f14df5af66e52f93");
  assert.equal(comparison.expected_surface_sha256, "b67f6a9d6011dcf6edd20da407216074b14c65b4990c0aecc147d878642a3adf");
  assert.equal(comparison.result, "PASS");
  assert.equal(baseline.owner_authorization.reference, "OWNER_DIRECTIVE_POST_MERGE_LIBRARY_API_RECOVERY");
  assert.match(baseline.limitations, /Owner visual review of the exact repair head remains required/);
});

test("an unauthorized PR468 Listening Room baseline mutation fails closed", () => {
  const temporary = materializeReviewedSurface(PR468_LISTENING_ROOM_HOMEPAGE_LIBRARY_INTERACTION_BASELINE);
  const record = path.join(temporary, PR468_LISTENING_ROOM_HOMEPAGE_LIBRARY_INTERACTION_BASELINE);
  const value = JSON.parse(read(record));
  value.owner_authorization.reference = "UNAUTHORIZED";
  write(record, value);
  assert.throws(() => loadLibraryInteractionBaseline(temporary, PR468_LISTENING_ROOM_HOMEPAGE_LIBRARY_INTERACTION_BASELINE));
});

test("an unauthorized PR469 post-merge Library baseline mutation fails closed", () => {
  const temporary = materializeReviewedSurface(PR469_POSTMERGE_LIBRARY_RECOVERY_BASELINE);
  const record = path.join(temporary, PR469_POSTMERGE_LIBRARY_RECOVERY_BASELINE);
  const value = JSON.parse(read(record));
  value.owner_authorization.reference = "UNAUTHORIZED";
  write(record, value);
  assert.throws(() => loadLibraryInteractionBaseline(temporary, PR469_POSTMERGE_LIBRARY_RECOVERY_BASELINE));
});

test("an unauthorized PR467 homepage baseline mutation fails closed", () => {
  const temporary = materializeReviewedSurface(PR467_APPROVED_OPTION_B_HOMEPAGE_LIBRARY_INTERACTION_BASELINE);
  const record = path.join(temporary, PR467_APPROVED_OPTION_B_HOMEPAGE_LIBRARY_INTERACTION_BASELINE);
  const value = JSON.parse(read(record));
  value.owner_authorization.reference = "UNAUTHORIZED";
  write(record, value);
  assert.throws(() => loadLibraryInteractionBaseline(temporary, PR467_APPROVED_OPTION_B_HOMEPAGE_LIBRARY_INTERACTION_BASELINE));
});

test("an unauthorized PR466 homepage baseline mutation fails closed", () => {
  const temporary = materializeReviewedSurface(PR466_APPROVED_OPTION_B_HOMEPAGE_LIBRARY_INTERACTION_BASELINE);
  const record = path.join(temporary, PR466_APPROVED_OPTION_B_HOMEPAGE_LIBRARY_INTERACTION_BASELINE);
  const value = JSON.parse(read(record));
  value.owner_authorization.reference = "UNAUTHORIZED";
  write(record, value);
  assert.throws(() => loadLibraryInteractionBaseline(temporary, PR466_APPROVED_OPTION_B_HOMEPAGE_LIBRARY_INTERACTION_BASELINE));
});

console.log(JSON.stringify({ result: "PASS", testCaseCount: cases }));
