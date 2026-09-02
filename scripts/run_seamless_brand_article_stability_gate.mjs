#!/usr/bin/env node
import crypto from "node:crypto";
import { execFileSync, spawnSync } from "node:child_process";
import fs from "node:fs";
import path from "node:path";

const ROOT = process.cwd();
const BROWSER_RUNS = { webkit: 10, chromium: 5, firefox: 5 };

function sha256(file) {
  return crypto.createHash("sha256").update(fs.readFileSync(file)).digest("hex");
}

function gitReference(...args) {
  return execFileSync("git", args, { cwd: ROOT, encoding: "utf8" }).trim();
}

function parseArgs(argv) {
  const options = { webkitRuns: 10, chromiumRuns: 5, firefoxRuns: 5 };
  const names = new Map([
    ["--base-url", "baseUrl"], ["--output", "output"], ["--manifest", "manifest"],
    ["--route-inventory", "routeInventory"], ["--capture-script", "captureScript"], ["--state-id", "stateId"],
    ["--webkit-runs", "webkitRuns"], ["--chromium-runs", "chromiumRuns"], ["--firefox-runs", "firefoxRuns"],
  ]);
  for (let index = 0; index < argv.length; index += 1) {
    const key = argv[index]; const property = names.get(key); const value = argv[index + 1];
    if (!property || !value || value.startsWith("--")) throw new Error(`Invalid Article stability argument: ${key}`);
    options[property] = property.endsWith("Runs") ? Number(value) : value;
    index += 1;
  }
  for (const key of ["baseUrl", "output", "manifest", "routeInventory", "captureScript", "stateId"]) if (!options[key]) throw new Error(`Missing required argument: ${key}`);
  if (options.stateId !== "article-mobile") throw new Error(`Article stability state must be article-mobile; received ${options.stateId}`);
  for (const [browser, property] of [["webkit", "webkitRuns"], ["chromium", "chromiumRuns"], ["firefox", "firefoxRuns"]]) {
    if (!Number.isInteger(options[property]) || options[property] < 1) throw new Error(`${browser} run count must be a positive integer`);
  }
  return options;
}

function resolveSafeOutput(raw) {
  if (raw.split(path.sep).includes("..")) throw new Error("Article stability output path traversal is not permitted");
  return path.resolve(raw);
}

function readJson(file, label) {
  if (!fs.existsSync(file)) throw new Error(`Missing ${label}: ${file}`);
  return JSON.parse(fs.readFileSync(file, "utf8"));
}

function validateRun({ output, browser, index, stateId }) {
  const summary = readJson(path.join(output, "capture-summary.json"), "capture summary");
  const metadata = readJson(path.join(output, "states", stateId, "metadata.json"), "state metadata");
  if (JSON.stringify([summary.expected_state_count, summary.captured_state_count, summary.stable_state_count]) !== JSON.stringify([1, 1, 1])) throw new Error(`${browser} run ${index}: expected/captured/stable count must be 1/1/1`);
  if (metadata.state_id !== stateId) throw new Error(`${browser} run ${index}: wrong state ID ${metadata.state_id}`);
  if (metadata.visual_quiescence?.result !== "PASS") throw new Error(`${browser} run ${index}: visual quiescence did not pass`);
  for (const key of ["console_error_count", "page_error_count", "failed_required_request_count"]) if (metadata[key] !== 0) throw new Error(`${browser} run ${index}: ${key} must be zero`);
  if (!Array.isArray(metadata.stability_attempts) || !metadata.stability_attempts.length || !metadata.stability_attempts.every((attempt) => attempt.stable === true)) throw new Error(`${browser} run ${index}: all paired screenshot attempts must be stable`);
  return { run: index, expected: 1, captured: 1, stable: 1, visual_quiescence: "PASS", paired_screenshot_hashes: true, browser_version: metadata.browser_version || "unknown", output_directory: output };
}

export function runArticleStabilityGate(options) {
  const root = resolveSafeOutput(options.output);
  const captureScript = path.resolve(options.captureScript);
  const manifest = path.resolve(options.manifest);
  const routeInventory = path.resolve(options.routeInventory);
  if (!fs.existsSync(captureScript) || !fs.existsSync(manifest) || !fs.existsSync(routeInventory)) throw new Error("Article stability inputs must exist");
  fs.mkdirSync(root, { recursive: true });
  const counts = { webkit: options.webkitRuns, chromium: options.chromiumRuns, firefox: options.firefoxRuns };
  const articleMobile = {};
  const runDirectories = new Set();
  for (const [browser, count] of Object.entries(counts)) {
    const runs = [];
    for (let index = 1; index <= count; index += 1) {
      const output = path.join(root, browser, `run-${index}`);
      const resolvedOutput = resolveSafeOutput(output);
      if (runDirectories.has(resolvedOutput)) throw new Error(`Duplicate Article stability run directory: ${resolvedOutput}`);
      if (fs.existsSync(resolvedOutput)) throw new Error(`Duplicate Article stability run directory already exists: ${resolvedOutput}`);
      runDirectories.add(resolvedOutput);
      const result = spawnSync(process.execPath, [captureScript, "--manifest", manifest, "--route-inventory", routeInventory, "--state-filter", options.stateId, "--capture", "--browser", browser, "--base-url", options.baseUrl, "--output", resolvedOutput], { cwd: ROOT, encoding: "utf8", maxBuffer: 40 * 1024 * 1024, shell: false });
      if (result.status !== 0) throw new Error(`${browser} run ${index}: capture process failed (${result.status}): ${result.stderr || result.stdout}`);
      runs.push(validateRun({ output: resolvedOutput, browser, index, stateId: options.stateId }));
    }
    if (runs.length !== count) throw new Error(`${browser}: missing Article stability run`);
    articleMobile[browser] = { expected: count, captured: runs.length, stable: runs.filter((run) => run.stable === 1).length, runs };
  }
  const result = {
    result: "PASS", state_id: options.stateId, exact_pr_head: gitReference("rev-parse", "HEAD"),
    state_manifest_sha256: sha256(manifest), route_inventory_sha256: sha256(routeInventory), capture_script_sha256: sha256(captureScript),
    production_surface_sha256: articleMobile.webkit.runs[0] && readJson(path.join(articleMobile.webkit.runs[0].output_directory, "capture-summary.json"), "capture summary").production_surface_sha256,
    article_mobile: articleMobile, generated_timestamp: new Date().toISOString(),
  };
  fs.writeFileSync(path.join(root, "article-stability-results.json"), `${JSON.stringify(result, null, 2)}\n`);
  return result;
}

if (import.meta.url === `file://${process.argv[1]}`) {
  try {
    const result = runArticleStabilityGate(parseArgs(process.argv.slice(2)));
    console.log(JSON.stringify(result));
  } catch (error) {
    console.error(error.stack || error.message);
    process.exitCode = 1;
  }
}
