#!/usr/bin/env node
import assert from "node:assert/strict";
import crypto from "node:crypto";
import { spawnSync } from "node:child_process";
import fs from "node:fs";
import os from "node:os";
import path from "node:path";
import {
  loadStateManifest,
  selectStateRecords,
  validateStateManifest,
} from "./lib/seamless_brand_state_manifest.mjs";

const root = process.cwd();
const manifestPath = path.join(root, "docs/design-system/seamless-brand-state-manifest.json");
const inventoryPath = path.join(root, "docs/design-system/seamless-brand-route-inventory.json");
const capturePath = path.join(root, "scripts/capture_seamless_brand_owner_review.mjs");
const manifest = loadStateManifest(manifestPath);
const inventory = JSON.parse(fs.readFileSync(inventoryPath, "utf8"));
const temp = fs.mkdtempSync(path.join(os.tmpdir(), "seamless-brand-manifest-cli-"));
let cases = 0;
let malformedIndex = 0;

function test(name, callback) {
  callback();
  cases += 1;
  process.stdout.write(`PASS ${cases}: ${name}\n`);
}

function invalidManifest(mutate) {
  const copy = structuredClone(manifest);
  mutate(copy);
  const file = path.join(temp, `malformed-${malformedIndex += 1}.json`);
  fs.writeFileSync(file, JSON.stringify(copy));
  return loadStateManifest(file);
}

function expectInvalid(copy, pattern) {
  assert.throws(() => validateStateManifest(copy, inventory), pattern);
}

function runCli(args) {
  const result = spawnSync(process.execPath, [capturePath, ...args], {
    cwd: root,
    encoding: "utf8",
    env: { ...process.env, SEAMLESS_BRAND_BROWSER_IMPORT_SENTINEL: "1" },
  });
  assert.equal(result.status, 0, `${args.join(" ")} failed: ${result.stderr}`);
  return result.stdout.trim();
}

test("checked-in manifest passes", () => assert.equal(validateStateManifest(manifest, inventory), manifest));
test("route count is 19", () => assert.equal(inventory.routes.length, 19));
test("manifest contains the five representative states plus the eight public-shell states", () => assert.equal(manifest.states.length, 13));
test("duplicate state ID fails", () => expectInvalid(invalidManifest((copy) => { copy.states[1].id = copy.states[0].id; }), /State index 1.*id/));
test("unknown route fails", () => expectInvalid(invalidManifest((copy) => { copy.states[0].route = "/unknown-route"; }), /State index 0.*route/));
test("invalid viewport fails", () => expectInvalid(invalidManifest((copy) => { copy.states[0].viewport.width = 0; }), /State index 0.*viewport\.width/));
test("invalid zoom fails", () => expectInvalid(invalidManifest((copy) => { copy.states[0].zoom = 0; }), /State index 0.*zoom/));
test("unsupported interaction fails", () => expectInvalid(invalidManifest((copy) => { copy.states[0].interaction = "unsupported"; }), /State index 0.*interaction/));
test("state filter preserves manifest order", () => {
  const reversed = [...manifest.states].map((state) => state.id).reverse();
  assert.deepEqual(selectStateRecords(manifest, reversed).map((state) => state.id), manifest.states.map((state) => state.id));
});
test("unknown filtered state fails", () => assert.throws(() => selectStateRecords(manifest, ["not-a-state"]), /not-a-state/));
test("duplicate filtered state fails", () => assert.throws(() => selectStateRecords(manifest, [manifest.states[0].id, manifest.states[0].id]), /duplicate/));
test("list-states launches no browser", () => {
  const lines = runCli(["--manifest", manifestPath, "--route-inventory", inventoryPath, "--list-states"]).split("\n");
  assert.equal(lines.length, 13);
  assert.deepEqual(lines.map((line) => JSON.parse(line).id), manifest.states.map((state) => state.id));
});
test("dry-run launches no browser", () => {
  const result = JSON.parse(runCli(["--manifest", manifestPath, "--route-inventory", inventoryPath, "--dry-run"]));
  assert.equal(result.total_states, 13);
  assert.deepEqual(result.selected_states, manifest.states.map((state) => state.id));
});
test("manifest and inventory SHA values are reported", () => {
  const result = JSON.parse(runCli(["--manifest", manifestPath, "--route-inventory", inventoryPath, "--dry-run"]));
  const hash = (file) => crypto.createHash("sha256").update(fs.readFileSync(file)).digest("hex");
  assert.equal(result.manifest_sha256, hash(manifestPath));
  assert.equal(result.route_inventory_sha256, hash(inventoryPath));
});

fs.writeFileSync(path.join(temp, "test-result.json"), JSON.stringify({ result: "PASS", testCaseCount: cases }) + "\n");
console.log(JSON.stringify({ result: "PASS", testCaseCount: cases, temp }));
