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

const pick = (value, keys) => value == null ? null : Object.fromEntries(keys.filter(key => key in value).map(key => [key, value[key]]));
const sanitizeReaderDetails = (details) => details == null ? null : {
  sampledAt: details.sampledAt,
  regions: Object.fromEntries(Object.entries(details.regions || {}).map(([key, value]) => [key, pick(value, ["hash", "length", "count"])])),
  state: pick(details.state, ["data-pagination-ready", "data-visual-page-index", "data-page-count", "data-book-page-count", "data-book-map-complete", "data-chapter-id", "data-source-page", "data-source-offset", "data-page-start", "data-page-end", "data-transport-chunks", "loading", "protectedVisible"]),
  fontState: details.fontState ? { status: details.fontState.status, check: details.fontState.check, active: pick(details.fontState.active, ["family", "size", "lineHeight", "style", "weight", "origin"]), relevantFaces: (details.fontState.relevantFaces || []).map(face => pick(face, ["family", "style", "weight", "status"])) } : null,
  fontResources: (details.fontResources || []).map(resource => pick(resource, ["path", "status", "start", "completed", "duration", "transferSize", "encodedBodySize"])),
};

// Runs only after the existing pre/screenshot/post interval. Never queries the
// browser, logs source text, or changes the strict fingerprint comparison.
export function assertCaptureFingerprintUnchanged({ before, after, beforeDetails, afterDetails, metadata, screenshot, attempt, artifactPath }) {
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
    readerBefore: sanitizeReaderDetails(beforeDetails), readerAfter: sanitizeReaderDetails(afterDetails),
    changedRegions: Object.keys(beforeDetails?.regions || afterDetails?.regions || {}).filter(key => hash(beforeDetails?.regions?.[key]) !== hash(afterDetails?.regions?.[key])),
    fontResourceCompletedDuringCapture: beforeDetails && afterDetails ? (afterDetails.fontResources || []).some(resource => resource.completed > beforeDetails.sampledAt && resource.completed <= afterDetails.sampledAt) : null,
  };
  fs.mkdirSync(path.dirname(artifactPath), { recursive: true });
  fs.writeFileSync(artifactPath, JSON.stringify(record, null, 2) + "\n");
  throw new Error(`Screenshot capture changed visual state for ${screenshot}; state=${record.stateId}; viewport=${record.viewport?.width}x${record.viewport?.height}; changed=${changedFields.join(",")}.`);
}
