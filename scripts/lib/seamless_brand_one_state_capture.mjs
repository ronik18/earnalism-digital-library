import fs from "node:fs";
import path from "node:path";
import crypto from "node:crypto";

export function stateOutputDirectory(outputDirectory, stateId) {
  return path.join(path.resolve(outputDirectory), "states", stateId);
}

export function requestedScreenshotNames(capture) {
  const names = [];
  if (capture?.viewport) names.push("viewport.png");
  if (capture?.full_page) names.push("full-page.png");
  if (capture?.brand_close_up) names.push("brand-close-up.png");
  if (capture?.parent_surface_close_up) names.push("parent-surface-close-up.png");
  return names;
}

export function validateOneStateCaptureSummary(summary, outputDirectory) {
  const expectedIds = summary?.requested_state_ids;
  const capturedIds = summary?.captured_state_ids;
  if (!Array.isArray(expectedIds) || expectedIds.length !== 1) throw new Error("Capture summary: expected exactly one requested state.");
  if (!Array.isArray(capturedIds) || capturedIds.length !== 1) throw new Error("Capture summary: expected exactly one captured state.");
  if (expectedIds[0] !== capturedIds[0]) throw new Error("Capture summary: captured state does not match requested state.");
  if (summary.missing_state_ids?.length) throw new Error("Capture summary: missing state IDs are not allowed.");
  if (summary.unexpected_state_ids?.length) throw new Error("Capture summary: unexpected state IDs are not allowed.");
  if (summary.duplicate_state_ids?.length) throw new Error("Capture summary: duplicate state IDs are not allowed.");
  if (summary.stable_state_count !== 1 || summary.unstable_state_count !== 0) throw new Error("Capture summary: the one captured state is unstable.");
  const metadataPath = path.join(stateOutputDirectory(outputDirectory, expectedIds[0]), "metadata.json");
  if (!fs.existsSync(metadataPath)) throw new Error("Capture summary: state metadata is missing.");
  const metadata = JSON.parse(fs.readFileSync(metadataPath, "utf8"));
  if (!metadata.stable) throw new Error("Capture summary: state metadata records an unstable capture.");
  const screenshotPaths = Object.values(metadata.screenshot_paths || {});
  if (!screenshotPaths.includes("viewport.png")) throw new Error("Capture summary: viewport screenshot is missing.");
  for (const [captureType, relativePath] of Object.entries(metadata.screenshot_paths || {})) {
    const file = path.join(path.dirname(metadataPath), relativePath);
    if (!fs.existsSync(file) || fs.statSync(file).size === 0) throw new Error(`Capture summary: required screenshot is missing or empty: ${relativePath}.`);
    const actualHash = crypto.createHash("sha256").update(fs.readFileSync(file)).digest("hex");
    if (metadata.screenshot_sha256?.[captureType] !== actualHash) throw new Error(`Capture summary: screenshot SHA mismatch: ${relativePath}.`);
  }
  return metadata;
}
