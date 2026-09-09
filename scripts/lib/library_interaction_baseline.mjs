import crypto from "node:crypto";
import fs from "node:fs";
import path from "node:path";

export const LIBRARY_INTERACTION_SURFACE = "library_interaction_surface";
export const LIBRARY_INTERACTION_INPUT_PATHS = [
  "frontend/src/components/ReferencePublicPages.jsx",
  "frontend/src/components/ReferencePublicPages.css",
  "frontend/src/pages/Library.jsx",
];
export const PR360_LIBRARY_INTERACTION_BASELINE = "docs/design-system/pr360-library-interaction-baseline.json";
export const PR362_LIBRARY_INTERACTION_BASELINE = "docs/design-system/pr362-library-interaction-baseline.json";
export const PR364_LIBRARY_INTERACTION_BASELINE = "docs/design-system/pr364-library-interaction-baseline.json";
export const PR371_LIBRARY_INTERACTION_BASELINE = "docs/design-system/pr371-library-interaction-baseline.json";
export const DEFAULT_LIBRARY_INTERACTION_BASELINE = PR371_LIBRARY_INTERACTION_BASELINE;

const SHA256 = /^[0-9a-f]{64}$/;
const GIT_OBJECT_ID = /^[0-9a-f]{40}$/;
const digest = (value) => crypto.createHash("sha256").update(value).digest("hex");
const fileDigest = (file) => digest(fs.readFileSync(file));
const hashAlgorithm = "sha256(file-sha256 plus two spaces plus relative path plus newline, sorted by relative path)";
const baselineContracts = {
  [PR360_LIBRARY_INTERACTION_BASELINE]: {
    reviewedSource: { commit: "14b50734e2f752102d9b9646effaba709b71d1a2", tree: "bf1255698c3c702a2488615ed83ab94b831827ae" },
    previous: { recordPath: "docs/design-system/library-filter-focus-hash-change.json", commit: "3a07c5dbe698046605269a035de1ef139ef36adc", hash: "696a0c8d760d349439280e63e19b8656d6fd1beff19696d6f1a369dc15cb144a" },
    authorizedHash: "a2925700553b5eef5adcc1f9cc52dbc1590d92fe70a022199864c3c3726c8003",
    changedPaths: ["frontend/src/components/ReferencePublicPages.jsx"],
    unchangedPaths: ["frontend/src/components/ReferencePublicPages.css", "frontend/src/pages/Library.jsx"],
    authorization: "OWNER_AUTHORIZATION_PR360_VERSIONED_LIBRARY_INTERACTION_BASELINE",
  },
  [PR362_LIBRARY_INTERACTION_BASELINE]: {
    reviewedSource: { commit: "96257f2c010512477e97dfc7a66771b7443c8a44", tree: "739062485bb53d07747ac84a48fb9826c4f4e862" },
    previous: { recordPath: PR360_LIBRARY_INTERACTION_BASELINE, commit: "14b50734e2f752102d9b9646effaba709b71d1a2", hash: "a2925700553b5eef5adcc1f9cc52dbc1590d92fe70a022199864c3c3726c8003" },
    authorizedHash: "a698315a69c6979ca6eedb2d2bab59461b19745ba883827deac02f79c187cd52",
    changedPaths: ["frontend/src/pages/Library.jsx"],
    unchangedPaths: ["frontend/src/components/ReferencePublicPages.jsx", "frontend/src/components/ReferencePublicPages.css"],
    authorization: "OWNER_AUTHORIZATION_PR362_VERSIONED_LIBRARY_INTERACTION_BASELINE",
  },
  [PR364_LIBRARY_INTERACTION_BASELINE]: {
    reviewedSource: { commit: "3b4f7047dcaebf60c3fb1a1490ac989abebc7fe6", tree: "92c5df30e2dad2240cfa2f1dc07f406f9a4a7836" },
    previous: { recordPath: PR362_LIBRARY_INTERACTION_BASELINE, commit: "96257f2c010512477e97dfc7a66771b7443c8a44", hash: "a698315a69c6979ca6eedb2d2bab59461b19745ba883827deac02f79c187cd52" },
    authorizedHash: "d0c094fbf9db03139d68a6706dcc3af5a59aa53cc22b3b1a9ba352101a0e3770",
    changedPaths: ["frontend/src/components/ReferencePublicPages.jsx"],
    unchangedPaths: ["frontend/src/components/ReferencePublicPages.css", "frontend/src/pages/Library.jsx"],
    authorization: "OWNER_AUTHORIZATION_PR364_VERSIONED_LIBRARY_INTERACTION_BASELINE",
  },
  [PR371_LIBRARY_INTERACTION_BASELINE]: {
    reviewedSource: { commit: "3f89874046258bdd9e0cb531af7f15f1039d8ce1", tree: "f230f7f5b97605923df2550e55c36d3b4e84d6c0" },
    previous: { recordPath: PR364_LIBRARY_INTERACTION_BASELINE, commit: "3b4f7047dcaebf60c3fb1a1490ac989abebc7fe6", hash: "d0c094fbf9db03139d68a6706dcc3af5a59aa53cc22b3b1a9ba352101a0e3770" },
    authorizedHash: "0fc10999d742f8c36ee8e0febdfb6715d3526843e90b96c5918fe9408eaf0d07",
    changedPaths: ["frontend/src/components/ReferencePublicPages.jsx", "frontend/src/components/ReferencePublicPages.css", "frontend/src/pages/Library.jsx"],
    unchangedPaths: [],
    authorization: "OWNER_AUTHORIZATION_PR371_VERSIONED_LIBRARY_INTERACTION_BASELINE",
  },
};

function contractForRecordPath(recordPath) {
  const normalized = String(recordPath).split(path.sep).join("/");
  if (baselineContracts[normalized]) return { recordPath: normalized, contract: baselineContracts[normalized] };
  const resolved = path.resolve(recordPath);
  for (const [knownPath, contract] of Object.entries(baselineContracts)) {
    if (resolved === path.resolve(knownPath)) return { recordPath: knownPath, contract };
  }
  return null;
}

export function libraryInteractionSurfaceHash(root = process.cwd()) {
  const listing = [...LIBRARY_INTERACTION_INPUT_PATHS]
    .sort()
    .map((relativePath) => `${fileDigest(path.join(root, relativePath))}  ${relativePath}\n`)
    .join("");
  return digest(listing);
}

export function loadLibraryInteractionBaseline(root = process.cwd(), recordPath = DEFAULT_LIBRARY_INTERACTION_BASELINE) {
  const expected = contractForRecordPath(recordPath);
  if (!expected) throw new Error(`Library interaction baseline is not an explicitly recognized transition: ${recordPath}`);
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
  const unchangedPaths = baseline.reviewed_source_comparison?.unchanged_paths_within_input_set;
  const previous = baseline.previous_baseline;
  const { contract } = expected;
  if (
    baseline.schema_version !== "earnalism.library-interaction-baseline.v1"
    || baseline.surface !== LIBRARY_INTERACTION_SURFACE
    || baseline.hash_algorithm !== hashAlgorithm
    || !inputPathsMatch
    || !SHA256.test(baseline.authorized_surface_sha256 || "") || baseline.authorized_surface_sha256 !== contract.authorizedHash
    || !SHA256.test(previous?.surface_sha256 || "") || previous.surface_sha256 !== contract.previous.hash
    || previous?.record_path !== contract.previous.recordPath || previous?.reviewed_source_commit !== contract.previous.commit
    || !GIT_OBJECT_ID.test(previous?.reviewed_source_commit || "")
    || baseline.reviewed_source?.commit !== contract.reviewedSource.commit || baseline.reviewed_source?.tree !== contract.reviewedSource.tree
    || !GIT_OBJECT_ID.test(baseline.reviewed_source?.commit || "") || !GIT_OBJECT_ID.test(baseline.reviewed_source?.tree || "")
    || !Array.isArray(changedPaths) || changedPaths.length !== contract.changedPaths.length || changedPaths.some((value, index) => value !== contract.changedPaths[index])
    || !Array.isArray(unchangedPaths) || unchangedPaths.length !== contract.unchangedPaths.length || unchangedPaths.some((value, index) => value !== contract.unchangedPaths[index])
    || baseline.owner_authorization?.reference !== contract.authorization
    || baseline.owner_authorization?.capture_is_not_expected_value_authority !== true
  ) {
    throw new Error(`Library interaction baseline is malformed: ${absolutePath}`);
  }
  return { ...baseline, absolute_path: absolutePath, record_path: expected.recordPath, sha256: fileDigest(absolutePath) };
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
    authorization_scope: baseline.owner_authorization.scope,
    result: observed_surface_sha256 === baseline.authorized_surface_sha256 ? "PASS" : "FAIL",
  };
}
