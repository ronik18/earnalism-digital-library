#!/usr/bin/env node
import assert from "node:assert/strict";
import fs from "node:fs";
import path from "node:path";

const workflowPath = path.join(process.cwd(), ".github/workflows/seamless-brand-owner-review.yml");
const workflow = fs.readFileSync(workflowPath, "utf8");
let cases = 0;
const pass = (name, check) => { assert.ok(check, name); cases += 1; console.log(`PASS ${cases}: ${name}`); };
const before = (first, second) => workflow.indexOf(first) >= 0 && workflow.indexOf(second) >= 0 && workflow.indexOf(first) < workflow.indexOf(second);

pass("keeps the dedicated workflow identity", /name: Seamless brand owner review/.test(workflow) && /seamless-brand-review:/.test(workflow));
pass("supports pull-request and manual exact-head resolution", /pull_request:/.test(workflow) && /workflow_dispatch:/.test(workflow) && /github\.event\.pull_request\.head\.sha/.test(workflow) && /\/pulls\/\$\{PR_NUMBER\}/.test(workflow));
pass("checks out the resolved PR head", /ref: \$\{\{ needs\.resolve-pr-head\.outputs\.pr_head \}\}/.test(workflow) && /git rev-parse HEAD/.test(workflow));
pass("records event and checkout provenance", /WORKFLOW_EVENT_SHA/.test(workflow) && /CHECKOUT_TREE_SHA/.test(workflow));
pass("uses a head-scoped concurrency group", /concurrency:[\s\S]*pr344-seamless-brand-owner-review/.test(workflow) && /cancel-in-progress: true/.test(workflow));
pass("runs all three pinned Playwright browsers", /playwright install --with-deps chromium firefox webkit/.test(workflow) && /for browser in firefox webkit/.test(workflow));
pass("runs tooling gates before capture", before("Run deterministic tooling gates", "Capture the exact head in all browsers"));
pass("runs final evidence and package validators", /validate_seamless_brand_final_evidence_inputs\.py/.test(workflow) && /validate_seamless_brand_final_owner_review\.py/.test(workflow));
pass("generates the exact-head package", /generate_seamless_brand_final_owner_review\.py/.test(workflow) && /--pr-head \"\$PR_HEAD_SHA\"/.test(workflow));
pass("gates final upload on successful validation", before("Validate final package", "Upload final owner-review envelope") && !/continue-on-error:\s*true/.test(workflow));
pass("uses full-head final artifact naming", /pr344-seamless-brand-final-review-\$\{PR_HEAD_SHA\}/.test(workflow));
pass("uses a fresh verification job and artifact download", /verify-published-owner-review:/.test(workflow) && /needs: seamless-brand-review/.test(workflow) && /actions\/download-artifact@v7/.test(workflow));
pass("records distinct artifact digests", /GITHUB_ARTIFACT_DIGEST/.test(workflow) && /DOWNLOADED_ARTIFACT_ARCHIVE_SHA256/.test(workflow) && /INNER_ARTIFACT_ZIP_SHA256/.test(workflow));
pass("keeps deployment and merge absent", !/git merge|gh pr merge/.test(workflow) && !/\bdeploy(?:ment)?\b/i.test(workflow.replace(/deployment jobs intentionally skipped/gi, "")));
pass("keeps diagnostic artifact name distinct", /pr344-seamless-brand-final-diagnostic-\$\{\{ needs\.resolve-pr-head\.outputs\.pr_head \}\}/.test(workflow));
console.log(JSON.stringify({ result: "PASS", testCaseCount: cases, workflowPath }));
