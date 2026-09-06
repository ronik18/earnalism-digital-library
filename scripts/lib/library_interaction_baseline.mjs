import crypto from "node:crypto";
import fs from "node:fs";
import path from "node:path";

export const LIBRARY_INTERACTION_SURFACE = "library_interaction_surface";
export const LIBRARY_INTERACTION_INPUT_PATHS = [
  "frontend/src/components/ReferencePublicPages.jsx",
  "frontend/src/components/ReferencePublicPages.css",
  "frontend/src/pages/Library.jsx",
];
export const DEFAULT_LIBRARY_INTERACTION_BASELINE = "docs/design-system/pr360-library-interaction-baseline.json";

const SHA256 = /^[0-9a-f]{64}$/;
const GIT_OBJECT_ID = /^[0-9a-f]{40}$/;
const AUTHORIZATION_REFERENCE = "OWNER_AUTHORIZATION_PR360_VERSIONED_LIBRARY_INTERACTION_BASELINE";
const digest = (value) => crypto.createHash("sha256").update(value).digest("hex");
const fileDigest = (file) => digest(fs.readFileSync(file));

export function libraryInteractionSurfaceHash(root = process.cwd()) {
  const listing = [...LIBRARY_INTERACTION_INPUT_PATHS]
    .sort()
    .map((relativePath) => `${fileDigest(path.join(root, relativePath))}  ${relativePath}\n`)
    .join("");
  return digest(listing);
}

export function loadLibraryInteractionBaseline(root = process.cwd(), recordPath = DEFAULT_LIBRARY_INTERACTION_BASELINE) {
  const absolutePath = path.resolve(root, recordPath);
  let baseline;
  try {
    baseline = JSON.parse(fs.readFileSync(absolutePath, "utf8"));
  } catch (error) {
    throw new Error(`Library interaction baseline is unreadable: ${absolutePath}`, { cause: error });
  }
  const inputPathsMatch = Array.isArray(baseline.input_paths)
    && baseline.input_paths.length === LIBRARY_INTERACTION_INPUT_PATHS.length
    && baseline.input_paths.every((value, index) => value === LIBRARY_INTERACTION_INPUT_PATHS[index]);
  const changedPaths = baseline.reviewed_source_comparison?.changed_paths_within_input_set;
  const previous = baseline.previous_baseline;
  if (
    baseline.schema_version !== "earnalism.library-interaction-baseline.v1"
    || baseline.surface !== LIBRARY_INTERACTION_SURFACE
    || baseline.hash_algorithm !== "sha256(file-sha256 plus two spaces plus relative path plus newline, sorted by relative path)"
    || !inputPathsMatch
    || !SHA256.test(baseline.authorized_surface_sha256 || "")
    || !SHA256.test(previous?.surface_sha256 || "")
    || previous?.record_path !== "docs/design-system/library-filter-focus-hash-change.json"
    || !GIT_OBJECT_ID.test(previous?.reviewed_source_commit || "")
    || !GIT_OBJECT_ID.test(baseline.reviewed_source?.commit || "")
    || !GIT_OBJECT_ID.test(baseline.reviewed_source?.tree || "")
    || !Array.isArray(changedPaths)
    || changedPaths.length !== 1
    || changedPaths[0] !== "frontend/src/components/ReferencePublicPages.jsx"
    || baseline.owner_authorization?.reference !== AUTHORIZATION_REFERENCE
    || baseline.owner_authorization?.capture_is_not_expected_value_authority !== true
  ) {
    throw new Error(`Library interaction baseline is malformed: ${absolutePath}`);
  }
  return { ...baseline, absolute_path: absolutePath, record_path: recordPath, sha256: fileDigest(absolutePath) };
}

export function compareLibraryInteractionBaseline(root = process.cwd(), recordPath = DEFAULT_LIBRARY_INTERACTION_BASELINE) {
  const baseline = loadLibraryInteractionBaseline(root, recordPath);
  const observed_surface_sha256 = libraryInteractionSurfaceHash(root);
  return {
    surface: LIBRARY_INTERACTION_SURFACE,
    approval_source: baseline.record_path,
    approval_source_sha256: baseline.sha256,
    previous_surface_sha256: baseline.previous_baseline.surface_sha256,
    expected_surface_sha256: baseline.authorized_surface_sha256,
    observed_surface_sha256,
    changed_from_previous: observed_surface_sha256 !== baseline.previous_baseline.surface_sha256,
    expected_change: true,
    authorization: baseline.owner_authorization.reference,
    result: observed_surface_sha256 === baseline.authorized_surface_sha256 ? "PASS" : "FAIL",
  };
}
