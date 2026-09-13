import assert from "node:assert/strict";

export const HISTORICAL_BOOK_COMMERCE_SOURCE = "706dfe228cdd554c8aa358b2b112912f457823be";
export const HISTORICAL_BOOK_COMMERCE_TREE = "7cf15b048f42ff6845da8856c7778aab420a96e5";
export const HISTORICAL_CAPTURE_MODE = "historical-v1";
export const CURRENT_CAPTURE_MODE = "current-candidate";
export const EXPECTED_OFFER_IDS = ["30m", "1h", "3h", "10h"];
export const EXPECTED_OFFER_BUTTONS = ["Choose The Opening Hour", "Choose The Quiet Hour", "Choose The Deep Reading Pass", "Choose The Reader’s Reserve"];

export function resolveCaptureIdentity({ mode, baseline, prHead, checkout, tree }) {
  if (mode === HISTORICAL_CAPTURE_MODE) {
    assert.equal(baseline, "1", "historical mode requires BOOK_COMMERCE_BASELINE=1");
    assert.equal(prHead, HISTORICAL_BOOK_COMMERCE_SOURCE, "historical mode requires the pinned historical PR head");
    assert.equal(checkout, HISTORICAL_BOOK_COMMERCE_SOURCE, "historical mode requires the pinned historical checkout identity");
    assert.equal(tree, HISTORICAL_BOOK_COMMERCE_TREE, "historical mode requires the pinned historical tree identity");
    return {
      mode,
      application_source_sha: HISTORICAL_BOOK_COMMERCE_SOURCE,
      application_tree_sha: HISTORICAL_BOOK_COMMERCE_TREE,
      application_provenance: "ARCHIVED_APPLICATION_WITH_CURRENT_CAPTURE_HARNESS_OVERLAY",
    };
  }
  assert.equal(mode, CURRENT_CAPTURE_MODE, `unsupported Book/Commerce capture mode: ${mode}`);
  assert.notEqual(baseline, "1", "current-candidate mode must not enable baseline compatibility");
  assert.notEqual(checkout, HISTORICAL_BOOK_COMMERCE_SOURCE, "historical source cannot use current-candidate acceptance");
  return {
    mode,
    application_source_sha: checkout,
    application_tree_sha: tree,
    application_provenance: "EXACT_CANDIDATE_CHECKOUT",
  };
}

export function evaluateOfferObservation({ mode, cardCount, buttonNames, testIds }) {
  const expectedIds = EXPECTED_OFFER_IDS.map((id) => `pricing-pack-${id}`);
  const namesMatch = JSON.stringify(buttonNames) === JSON.stringify(EXPECTED_OFFER_BUTTONS);
  const countMatch = cardCount === EXPECTED_OFFER_IDS.length && buttonNames.length === EXPECTED_OFFER_IDS.length;
  if (mode === HISTORICAL_CAPTURE_MODE) {
    const noCurrentCandidateIds = testIds.length === 0;
    return {
      mode,
      expected_pack_count: EXPECTED_OFFER_IDS.length,
      rendered_card_count: cardCount,
      rendered_cta_count: buttonNames.length,
      button_accessible_names: buttonNames,
      current_candidate_test_ids: testIds,
      candidate_test_id_requirement: "NOT_APPLICABLE_HISTORICAL_SOURCE",
      result: countMatch && namesMatch && noCurrentCandidateIds ? "HISTORICAL_OBSERVED" : "FAIL",
    };
  }
  const idsMatch = JSON.stringify(testIds) === JSON.stringify(expectedIds);
  return {
    mode,
    expected_pack_count: EXPECTED_OFFER_IDS.length,
    rendered_card_count: cardCount,
    rendered_cta_count: buttonNames.length,
    button_accessible_names: buttonNames,
    current_candidate_test_ids: testIds,
    candidate_test_id_requirement: "REQUIRED",
    result: countMatch && namesMatch && idsMatch ? "PASS" : "FAIL",
  };
}

export function writeCaptureFailure(fs, output, details) {
  fs.mkdirSync(output, { recursive: true });
  fs.writeFileSync(`${output}/capture-stage-error.json`, `${JSON.stringify({ schema_version: "pr341-book-commerce-capture-failure-v1", ...details }, null, 2)}\n`);
}
