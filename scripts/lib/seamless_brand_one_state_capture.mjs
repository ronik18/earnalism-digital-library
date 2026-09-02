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

export function validateUniqueOutputDirectories(outputDirectory, states) {
  const directories = states.map((state) => stateOutputDirectory(outputDirectory, state.id));
  if (new Set(directories).size !== directories.length) throw new Error("Capture summary: duplicate output path.");
  return directories;
}

export function validateCaptureSummary(summary, outputDirectory, expectedCount) {
  const expectedIds = summary?.requested_state_ids;
  const capturedIds = summary?.captured_state_ids;
  if (!Array.isArray(expectedIds) || expectedIds.length !== expectedCount) throw new Error(`Capture summary: expected exactly ${expectedCount} requested states.`);
  if (!Array.isArray(capturedIds) || capturedIds.length !== expectedCount) throw new Error(`Capture summary: expected exactly ${expectedCount} captured states.`);
  if (new Set(expectedIds).size !== expectedIds.length) throw new Error("Capture summary: duplicate requested state IDs are not allowed.");
  if (new Set(capturedIds).size !== capturedIds.length) throw new Error("Capture summary: duplicate captured state IDs are not allowed.");
  if (JSON.stringify(expectedIds) !== JSON.stringify(capturedIds)) throw new Error("Capture summary: captured state order does not match requested manifest order.");
  if (summary.missing_state_ids?.length) throw new Error("Capture summary: missing state IDs are not allowed.");
  if (summary.unexpected_state_ids?.length) throw new Error("Capture summary: unexpected state IDs are not allowed.");
  if (summary.duplicate_state_ids?.length) throw new Error("Capture summary: duplicate state IDs are not allowed.");
  if (summary.stable_state_count !== expectedCount || summary.unstable_state_count !== 0) throw new Error("Capture summary: a captured state is unstable.");
  const records = [];
  const outputDirectories = new Set();
  for (const stateId of expectedIds) {
    const stateDirectory = stateOutputDirectory(outputDirectory, stateId);
    if (outputDirectories.has(stateDirectory)) throw new Error(`Capture summary: duplicate output path for ${stateId}.`);
    outputDirectories.add(stateDirectory);
    const metadataPath = path.join(stateDirectory, "metadata.json");
    if (!fs.existsSync(metadataPath)) throw new Error(`Capture summary: state metadata is missing for ${stateId}.`);
    const metadata = JSON.parse(fs.readFileSync(metadataPath, "utf8"));
    if (!metadata.stable) throw new Error(`Capture summary: state metadata records an unstable capture for ${stateId}.`);
    const screenshotPaths = Object.values(metadata.screenshot_paths || {});
    if (!screenshotPaths.includes("viewport.png")) throw new Error(`Capture summary: viewport screenshot is missing for ${stateId}.`);
    for (const [captureType, relativePath] of Object.entries(metadata.screenshot_paths || {})) {
      const file = path.join(stateDirectory, relativePath);
      if (!fs.existsSync(file) || fs.statSync(file).size === 0) throw new Error(`Capture summary: required screenshot is missing or empty: ${relativePath}.`);
      const actualHash = crypto.createHash("sha256").update(fs.readFileSync(file)).digest("hex");
      if (metadata.screenshot_sha256?.[captureType] !== actualHash) throw new Error(`Capture summary: screenshot SHA mismatch: ${relativePath}.`);
    }
    records.push(metadata);
  }
  return records;
}

export function validateOneStateCaptureSummary(summary, outputDirectory) {
  return validateCaptureSummary(summary, outputDirectory, 1)[0];
}
