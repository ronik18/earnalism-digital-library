import crypto from "node:crypto";
import fs from "node:fs";
import path from "node:path";

const hash = (value) => crypto.createHash("sha256").update(JSON.stringify(value)).digest("hex");
const fields = {
  dom: "DOM_TEXT_CHANGED",
  geometry: "GEOMETRY_CHANGED",
  fonts: "FONT_STATE_CHANGED",
  scroll: "SCROLL_POSITION_CHANGED",
  style_count: "CAPTURE_STYLE_COUNT_CHANGED",
};
const summarize = (value) => ({
  domTextHash: hash(value.dom),
  geometryHash: hash(value.geometry),
  fontHash: hash(value.fonts),
  scrollHash: hash(value.scroll),
  captureStyleCount: value.style_count,
});

// Runs only after the existing pre/screenshot/post interval. Never queries the
// browser, logs source text, or changes the strict fingerprint comparison.
export function assertCaptureFingerprintUnchanged({ before, after, metadata, screenshot, attempt, artifactPath }) {
  if (hash(before) === hash(after)) return;
  const changedFields = Object.entries(fields).filter(([key]) => hash(before[key]) !== hash(after[key])).map(([, label]) => label);
  const record = {
    stateId: metadata.stateId, route: metadata.route, variant: metadata.variant,
    browser: metadata.browser, browserVersion: metadata.browserVersion,
    viewport: metadata.viewport, requestedViewport: metadata.requestedViewport,
    zoom: metadata.zoom, deviceScaleFactor: metadata.deviceScaleFactor,
    colorScheme: metadata.colorScheme, reducedMotion: metadata.reducedMotion,
    sourceHead: metadata.sourceHead, screenshot, attempt,
    before: summarize(before), after: summarize(after), changedFields,
  };
  fs.mkdirSync(path.dirname(artifactPath), { recursive: true });
  fs.writeFileSync(artifactPath, JSON.stringify(record, null, 2) + "\n");
  throw new Error(`Screenshot capture changed visual state for ${screenshot}; state=${record.stateId}; viewport=${record.viewport?.width}x${record.viewport?.height}; changed=${changedFields.join(",")}.`);
}
