#!/usr/bin/env node
import assert from "node:assert/strict";
import { spawnSync } from "node:child_process";
import { createRequire } from "node:module";
import fs from "node:fs";
import os from "node:os";
import path from "node:path";

const workflowPath = path.join(process.cwd(), ".github/workflows/seamless-brand-owner-review.yml");
const workflow = fs.readFileSync(workflowPath, "utf8");
const require = createRequire(import.meta.url);
const yaml = require("js-yaml");
const workflowDocument = yaml.load(workflow);
let cases = 0;
const pass = (name, check) => { assert.ok(check, name); cases += 1; console.log(`PASS ${cases}: ${name}`); };
const before = (first, second) => workflow.indexOf(first) >= 0 && workflow.indexOf(second) >= 0 && workflow.indexOf(first) < workflow.indexOf(second);

const runSteps = Object.entries(workflowDocument.jobs || {}).flatMap(([jobId, job]) => (job.steps || []).filter((step) => typeof step.run === "string").map((step) => ({ jobId, name: step.name || "unnamed", shell: step.shell || "bash", run: step.run })));
const bashCompatible = (shell) => !shell || /(?:^|\s)(?:bash|sh)(?:\s|$)/.test(shell);
const shellSource = (run) => run.replace(/\$\{\{[\s\S]*?\}\}/g, "__GITHUB_EXPRESSION__");
const shellAudit = runSteps.filter((step) => bashCompatible(step.shell)).map((step) => {
  const parsed = spawnSync("bash", ["-n"], { input: shellSource(step.run), encoding: "utf8" });
  const heredocs = [...step.run.matchAll(/<<-?\s*['\"]?([A-Za-z_][A-Za-z0-9_]*)['\"]?/g)].map((match) => ({ delimiter: match[1], nested: /(?:for|while|until|if|case)\b[\s\S]*$/.test(step.run.slice(0, match.index)), effective_leading_whitespace: [...step.run.matchAll(new RegExp(`^([ \\t]*)${match[1]}$`, "gm"))].map((item) => item[1].length) }));
  return { job_id: step.jobId, step_name: step.name, shell: step.shell, bash_syntax_result: parsed.status === 0 ? "PASS" : "FAIL", stderr: parsed.stderr.trim(), heredocs };
});
const shellAuditPath = path.join(os.tmpdir(), "pr344-final-publication-heredoc-audit.json");
fs.writeFileSync(shellAuditPath, `${JSON.stringify({ result: shellAudit.every((entry) => entry.bash_syntax_result === "PASS") ? "PASS" : "FAIL", runs: shellAudit }, null, 2)}\n`);

pass("keeps the dedicated workflow identity", /name: Seamless brand owner review/.test(workflow) && /seamless-brand-review:/.test(workflow));
pass("supports pull-request and manual exact-head resolution", /pull_request:/.test(workflow) && /workflow_dispatch:/.test(workflow) && /github\.event\.pull_request\.head\.sha/.test(workflow) && /\/pulls\/\$\{PR_NUMBER\}/.test(workflow));
pass("checks out the resolved PR head", /ref: \$\{\{ needs\.resolve-pr-head\.outputs\.pr_head \}\}/.test(workflow) && /git rev-parse HEAD/.test(workflow));
pass("records event and checkout provenance", /WORKFLOW_EVENT_SHA/.test(workflow) && /CHECKOUT_TREE_SHA/.test(workflow));
pass("uses a head-scoped concurrency group", /concurrency:[\s\S]*pr344-seamless-brand-owner-review/.test(workflow) && /cancel-in-progress: true/.test(workflow));
pass("runs all three pinned Playwright browsers", /playwright install --with-deps chromium firefox webkit/.test(workflow) && /for browser in firefox webkit/.test(workflow));
pass("runs browser tooling gates before capture", before("Run browser tooling gates", "Capture the exact head in all browsers"));
pass("uses explicit isolated production and review fixture builds", /REACT_APP_ENABLE_VISUAL_FIXTURES=0/.test(workflow) && /REACT_APP_ENABLE_VISUAL_FIXTURES=1/.test(workflow) && /pr344-production-contract-build/.test(workflow) && /pr344-owner-review-fixture-build/.test(workflow));
pass("keeps visual fixture mode out of job-global environment", !/\n\s*REACT_APP_ENABLE_VISUAL_FIXTURES:\s*["']?1/.test(workflow));
pass("serves the review fixture build for browser gates and final capture", (workflow.match(/--directory "\$REVIEW_FIXTURE_BUILD_DIR"/g) || []).length >= 2);
pass("probes production absence and review fixture query gating", /verify_seamless_brand_review_fixture_build\.mjs/.test(workflow) && /final-ci-sanitized-fixture-root-cause\.json/.test(workflow));
pass("keeps the auth private fixture assertion mandatory", /assert\.equal\(record\.private_fixture\.fixture_visible, true\)/.test(fs.readFileSync(path.join(process.cwd(), "scripts/test_seamless_brand_auth_private_batch.mjs"), "utf8")));
pass("audits deployment isolation and labels the review build as non-deployed", /visual-fixture-deployment-isolation\.json/.test(workflow) && /DETERMINISTIC_VISUAL_FIXTURE_BUILD_NOT_DEPLOYED/.test(workflow));
pass("makes final publication depend on fixture build probes", before("Verify production and review fixture build modes", "Run browser tooling gates") && before("Verify production and review fixture build modes", "Capture the exact head in all browsers"));
pass("runs the focused WebKit Article stability preflight before browser populations", before("Run focused Article stability gate", "Run browser tooling gates") && before("Run focused Article stability gate", "Capture the exact head in all browsers") && /node scripts\/test_webkit_article_mobile_stability\.mjs/.test(workflow) && /node scripts\/run_seamless_brand_article_stability_gate\.mjs/.test(workflow) && /--webkit-runs 10/.test(workflow) && /--chromium-runs 5/.test(workflow) && /--firefox-runs 5/.test(workflow));
pass("uses the checked-in Article stability runner with explicit Bash", (() => { const step = runSteps.find((item) => item.name === "Run focused Article stability gate"); return step?.shell === "bash" && !/<<'JS'/.test(step.run) && /run_seamless_brand_article_stability_gate\.mjs/.test(step.run); })());
pass("includes the Article stability runner and its test in workflow path filters", /scripts\/run_seamless_brand_article_stability_gate\.mjs/.test(workflow) && /scripts\/test_seamless_brand_article_stability_gate\.mjs/.test(workflow));
pass("shell-parses every Bash-compatible workflow run block", shellAudit.every((entry) => entry.bash_syntax_result === "PASS"));
pass("records a heredoc audit without invalid indented delimiters", shellAudit.every((entry) => entry.heredocs.every((heredoc) => heredoc.effective_leading_whitespace.every((count) => count === 0))));
pass("records the complete Article stability result in exact-head evidence inputs", /ARTICLE_STABILITY_RESULTS/.test(workflow) && /inputs\.article_stability=articleStability/.test(workflow) && /\[10,10,10\]/.test(workflow));
pass("runs final evidence and package validators", /validate_seamless_brand_final_evidence_inputs\.py/.test(workflow) && /validate_seamless_brand_final_owner_review\.py/.test(workflow));
pass("restores the known generated sitemap before the clean-tree assertion", /source-sitemap\.xml/.test(workflow) && before("cp \"$RUNNER_TEMP/source-sitemap.xml\" frontend/public/sitemap.xml", "git diff --exit-code"));
pass("generates the exact-head package", /generate_seamless_brand_final_owner_review\.py/.test(workflow) && /--pr-head \"\$PR_HEAD_SHA\"/.test(workflow));
pass("gates final upload on successful validation", before("Validate final package", "Upload final owner-review envelope") && !/continue-on-error:\s*true/.test(workflow));
pass("uses full-head final artifact naming", /pr344-seamless-brand-final-review-\$\{PR_HEAD_SHA\}/.test(workflow));
pass("uses a fresh verification job and artifact download", /verify-published-owner-review:/.test(workflow) && /needs: seamless-brand-review/.test(workflow) && /actions\/download-artifact@v7/.test(workflow));
pass("records distinct artifact digests", /GITHUB_ARTIFACT_DIGEST/.test(workflow) && /DOWNLOADED_ARTIFACT_ARCHIVE_SHA256/.test(workflow) && /INNER_ARTIFACT_ZIP_SHA256/.test(workflow));
pass("keeps deployment and merge absent", !/git merge|gh pr merge/.test(workflow) && !/\bvercel\s+deploy\b|\brailway\s+deploy\b/i.test(workflow));
pass("keeps diagnostic artifact name distinct", /pr344-seamless-brand-final-diagnostic-\$\{\{ needs\.resolve-pr-head\.outputs\.pr_head \}\}/.test(workflow));
console.log(JSON.stringify({ result: "PASS", testCaseCount: cases, workflowPath, shellAuditPath }));
