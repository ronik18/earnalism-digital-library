import assert from "node:assert/strict";
import fs from "node:fs";
import os from "node:os";
import path from "node:path";
import { assertCaptureFingerprintUnchanged } from "./lib/brand_capture_mismatch.mjs";

const temp = fs.mkdtempSync(path.join(os.tmpdir(), "brand-capture-mismatch-"));
const artifactPath = path.join(temp, "brand-capture-state-mismatch.json");
const before = { dom: "safe-length:hash", geometry: [[0, 0, 100, 100]], fonts: [{ fontFamily: "Serif", length: 10 }], scroll: [0, 0, 0, 0], style_count: 1 };
const metadata = { stateId: "fixture", route: "/reader/test", viewport: { width: 390, height: 844 }, browser: "chromium", privateNotes: "DO_NOT_LOG_PRIVATE_NOTES", token: "DO_NOT_LOG_TOKEN" };
let tests = 0;
function check(name, run) { run(); console.log(`PASS ${++tests}: ${name}`); }
try {
  check("equal fingerprints pass without creating an artifact", () => {
    assertCaptureFingerprintUnchanged({ before, after: structuredClone(before), metadata, screenshot: "viewport.png", artifactPath });
    assert.equal(fs.existsSync(artifactPath), false);
  });
  for (const [key, label] of Object.entries({ dom: "DOM_TEXT_CHANGED", geometry: "GEOMETRY_CHANGED", fonts: "FONT_STATE_CHANGED", scroll: "SCROLL_POSITION_CHANGED", style_count: "CAPTURE_STYLE_COUNT_CHANGED" })) {
    check(`${label} fails and retains the exact differing field`, () => {
      const after = structuredClone(before); after[key] = key === "style_count" ? 2 : "DO_NOT_LOG_MANUSCRIPT";
      assert.throws(() => assertCaptureFingerprintUnchanged({ before, after, metadata, screenshot: "viewport.png", artifactPath }), /Screenshot capture changed visual state for viewport.png; state=fixture; viewport=390x844/);
      const text = fs.readFileSync(artifactPath, "utf8"); const record = JSON.parse(text);
      assert.deepEqual(record.changedFields, [label]); assert.equal(record.screenshot, "viewport.png");
      assert.equal(/DO_NOT_LOG/.test(text), false); assert.equal(record.before.domTextHash.length, 64);
    });
  }
  check("multiple changed fields are retained without claiming temporal order", () => {
    assert.throws(() => assertCaptureFingerprintUnchanged({ before, after: { ...before, scroll: [0, 1, 0, 0], style_count: 2 }, metadata, screenshot: "viewport.png", artifactPath }));
    assert.deepEqual(JSON.parse(fs.readFileSync(artifactPath)).changedFields, ["SCROLL_POSITION_CHANGED", "CAPTURE_STYLE_COUNT_CHANGED"]);
  });
  check("sensitive interval has no new browser operations", () => {
    const source = fs.readFileSync("scripts/capture_seamless_brand_owner_review.mjs", "utf8");
    const interval = source.slice(source.indexOf("const before = await visualFingerprint(page);", source.indexOf("const write = async")), source.indexOf("const unchanged =", source.indexOf("const write = async")));
    assert.equal(interval.match(/visualFingerprint\(page\)/g).length, 2);
    assert.equal(/page\.evaluate|waitFor|assertCaptureFingerprintUnchanged/.test(interval), false);
    assert.match(source, /trace.push\(\{ label, name, before, after, unchanged \}\);\s*if \(!unchanged\) assertCaptureFingerprintUnchanged/);
  });
} finally { fs.rmSync(temp, { recursive: true, force: true }); }
console.log(`${tests} tests passed`);
