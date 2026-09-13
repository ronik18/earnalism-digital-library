#!/usr/bin/env node
import assert from "node:assert/strict";
import fs from "node:fs";
import os from "node:os";
import path from "node:path";
import {
  CURRENT_CAPTURE_MODE,
  HISTORICAL_BOOK_COMMERCE_SOURCE,
  HISTORICAL_BOOK_COMMERCE_TREE,
  HISTORICAL_CAPTURE_MODE,
  evaluateOfferObservation,
  resolveCaptureIdentity,
  writeCaptureFailure,
} from "./lib/book_commerce_capture_contract.mjs";

const names = ["Choose The Opening Hour", "Choose The Quiet Hour", "Choose The Deep Reading Pass", "Choose The Reader’s Reserve"];
const ids = ["pricing-pack-30m", "pricing-pack-1h", "pricing-pack-3h", "pricing-pack-10h"];
let cases = 0;
const pass = (name, fn) => { fn(); cases += 1; console.log(`PASS ${cases}: ${name}`); };

pass("the pinned historical source selects only the explicit compatibility mode", () => {
  const result = resolveCaptureIdentity({ mode: HISTORICAL_CAPTURE_MODE, baseline: "1", prHead: HISTORICAL_BOOK_COMMERCE_SOURCE, checkout: HISTORICAL_BOOK_COMMERCE_SOURCE, tree: HISTORICAL_BOOK_COMMERCE_TREE });
  assert.equal(result.application_provenance, "ARCHIVED_APPLICATION_WITH_CURRENT_CAPTURE_HARNESS_OVERLAY");
});
pass("historical mode records its actual no-test-id DOM instead of a candidate PASS", () => assert.equal(evaluateOfferObservation({ mode: HISTORICAL_CAPTURE_MODE, cardCount: 4, buttonNames: names, testIds: [] }).result, "HISTORICAL_OBSERVED"));
pass("current candidate mode requires every current offer test ID", () => assert.equal(evaluateOfferObservation({ mode: CURRENT_CAPTURE_MODE, cardCount: 4, buttonNames: names, testIds: ids }).result, "PASS"));
pass("missing candidate CTA or wrong card count still fails", () => {
  assert.equal(evaluateOfferObservation({ mode: CURRENT_CAPTURE_MODE, cardCount: 3, buttonNames: names.slice(0, 3), testIds: ids.slice(0, 3) }).result, "FAIL");
});
pass("historical source cannot enter current-candidate acceptance", () => assert.throws(() => resolveCaptureIdentity({ mode: CURRENT_CAPTURE_MODE, baseline: "", prHead: HISTORICAL_BOOK_COMMERCE_SOURCE, checkout: HISTORICAL_BOOK_COMMERCE_SOURCE, tree: HISTORICAL_BOOK_COMMERCE_TREE })));
pass("wrong historical identity is rejected", () => assert.throws(() => resolveCaptureIdentity({ mode: HISTORICAL_CAPTURE_MODE, baseline: "1", prHead: "0".repeat(40), checkout: HISTORICAL_BOOK_COMMERCE_SOURCE, tree: HISTORICAL_BOOK_COMMERCE_TREE })));
pass("forced capture failure diagnostics are retained without converting failure to PASS", () => {
  const output = fs.mkdtempSync(path.join(os.tmpdir(), "pr381-commerce-capture-failure-"));
  writeCaptureFailure(fs, output, { stage: "forced-test", error: { name: "Error", message: "forced capture failure" }, partial_state_ids: [] });
  const record = JSON.parse(fs.readFileSync(path.join(output, "capture-stage-error.json"), "utf8"));
  assert.equal(record.error.message, "forced capture failure");
  assert.notEqual(record.status, "PASS");
});
console.log(JSON.stringify({ result: "PASS", testCaseCount: cases }));
