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
export const PR372_LIBRARY_INTERACTION_BASELINE = "docs/design-system/pr372-library-interaction-baseline.json";
export const PR376_LIBRARY_INTERACTION_BASELINE = "docs/design-system/pr376-library-interaction-baseline.json";
export const PR377_LIBRARY_INTERACTION_BASELINE = "docs/design-system/pr377-library-interaction-baseline.json";
export const ISSUE380_LIBRARY_INTERACTION_BASELINE = "docs/design-system/issue380-library-interaction-baseline.json";
export const ISSUE380_UI_COMPLETION_LIBRARY_INTERACTION_BASELINE = "docs/design-system/issue380-ui-completion-library-interaction-baseline.json";
export const PR397_LIBRARY_INTERACTION_BASELINE = "docs/design-system/pr397-library-interaction-baseline.json";
export const PR399_LIBRARY_INTERACTION_BASELINE = "docs/design-system/pr399-library-interaction-baseline.json";
export const PR414_LIBRARY_INTERACTION_BASELINE = "docs/design-system/pr414-held-release-library-interaction-baseline.json";
export const PR416_LIBRARY_INTERACTION_BASELINE = "docs/design-system/pr416-home-shelf-library-interaction-baseline.json";
export const HOME_SECTIONS_LIBRARY_INTERACTION_BASELINE = "docs/design-system/home-sections-library-interaction-baseline.json";
export const INDIA_COMMERCIAL_CUTOVER_HOME_LIBRARY_INTERACTION_BASELINE = "docs/design-system/india-commercial-cutover-home-library-interaction-baseline.json";
export const ISSUE380_UI_COMPLETION_LIBRARY_INTERACTION_INPUT_PATHS = [
  "frontend/src/components/EditorialHomeLibrarySurfaces.jsx",
  "frontend/src/components/ReferencePublicPages.css",
  "frontend/src/styles/library-paper-review.css",
  "frontend/src/pages/Library.jsx",
];
// The prior Home-sections record remains an immutable historical transition.
// Runtime/evidence callers must use the later, explicitly authorized India
// commercial cutover record as the active decision.
export const DEFAULT_LIBRARY_INTERACTION_BASELINE = INDIA_COMMERCIAL_CUTOVER_HOME_LIBRARY_INTERACTION_BASELINE;

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
  [PR372_LIBRARY_INTERACTION_BASELINE]: {
    reviewedSource: { commit: "66ecdf65215521c2148307616c2c36c393008277", tree: "35e7418b288e1bb1199e33626de3eb9c6ee361e5" },
    previous: { recordPath: PR371_LIBRARY_INTERACTION_BASELINE, commit: "3f89874046258bdd9e0cb531af7f15f1039d8ce1", hash: "0fc10999d742f8c36ee8e0febdfb6715d3526843e90b96c5918fe9408eaf0d07" },
    authorizedHash: "750e6eb58ebc1e6c55df6f6ba305dae460a2f39bbb4dda5661c08f59a6fd2a34",
    changedPaths: ["frontend/src/components/ReferencePublicPages.jsx"],
    unchangedPaths: ["frontend/src/components/ReferencePublicPages.css", "frontend/src/pages/Library.jsx"],
    authorization: "OWNER_AUTHORIZATION_PR372_VERSIONED_LIBRARY_INTERACTION_BASELINE",
  },
  [PR376_LIBRARY_INTERACTION_BASELINE]: {
    reviewedSource: { commit: "f286262009a845c8aaf3da8ba8da349c6718b4de", tree: "eb68ff05ae5b89fa660549410eb6993daee82e0d", base: "bd1e37680b833599b36345a21e6842df4144d499" },
    previous: { recordPath: PR372_LIBRARY_INTERACTION_BASELINE, commit: "66ecdf65215521c2148307616c2c36c393008277", hash: "750e6eb58ebc1e6c55df6f6ba305dae460a2f39bbb4dda5661c08f59a6fd2a34" },
    authorizedHash: "4120516e672e41d0a873bcbdc38f08f218c2b1017c8bc5e030b9b0e727b1326f",
    changedPaths: ["frontend/src/pages/Library.jsx"],
    unchangedPaths: ["frontend/src/components/ReferencePublicPages.jsx", "frontend/src/components/ReferencePublicPages.css"],
    authorization: "OWNER_AUTHORIZATION_PR376_VERSIONED_LIBRARY_INTERACTION_BASELINE",
  },
  [PR377_LIBRARY_INTERACTION_BASELINE]: {
    reviewedSource: { commit: "f3e18e0a40bd025ef874220b873168dc793b87ee", tree: "767e5eb9af03238fd494119d370cbfad5c38ff0a", base: "babc3d320f5ed6c00b73c90ade2bc4a98f166f08" },
    previous: { recordPath: PR376_LIBRARY_INTERACTION_BASELINE, commit: "f286262009a845c8aaf3da8ba8da349c6718b4de", hash: "4120516e672e41d0a873bcbdc38f08f218c2b1017c8bc5e030b9b0e727b1326f" },
    authorizedHash: "0499acf4a59729151980cb220e0d7d22292d5add88e53abc6805d3aacb84c95b",
    changedPaths: ["frontend/src/components/ReferencePublicPages.jsx", "frontend/src/pages/Library.jsx"],
    unchangedPaths: ["frontend/src/components/ReferencePublicPages.css"],
    authorization: "OWNER_AUTHORIZATION_PR377_VERSIONED_LIBRARY_INTERACTION_BASELINE",
  },
  [ISSUE380_LIBRARY_INTERACTION_BASELINE]: {
    reviewedSource: { commit: "dfde080137d6f722f09b44c3729e67f169521569", tree: "ef28eb8582cd6e05bf27e8d9dcd27d31e7fd62cd", base: "a220f007f848eb32261cedd929f9a27eedb359c4" },
    previous: { recordPath: PR377_LIBRARY_INTERACTION_BASELINE, commit: "f3e18e0a40bd025ef874220b873168dc793b87ee", hash: "0499acf4a59729151980cb220e0d7d22292d5add88e53abc6805d3aacb84c95b" },
    authorizedHash: "54e3670f223a9f464ace67244802d4bcc3c25d6231c0ae7a4518aea4056dec66",
    changedPaths: ["frontend/src/components/ReferencePublicPages.jsx", "frontend/src/components/ReferencePublicPages.css", "frontend/src/pages/Library.jsx"],
    unchangedPaths: [],
    authorization: "OWNER_AUTHORIZATION_ISSUE380_VERSIONED_LIBRARY_INTERACTION_BASELINE",
  },
  [ISSUE380_UI_COMPLETION_LIBRARY_INTERACTION_BASELINE]: {
    reviewedSource: { commit: "2fc56906697e016b570b3fd13d9673717408a60a", tree: "0d9bdcb4b25f1b9a722e02771e606958516f2084", base: "2abbd3a5674208e40bcd1e636082c6e5f819d8ab" },
    previous: { recordPath: ISSUE380_LIBRARY_INTERACTION_BASELINE, commit: "dfde080137d6f722f09b44c3729e67f169521569", hash: "54e3670f223a9f464ace67244802d4bcc3c25d6231c0ae7a4518aea4056dec66" },
    authorizedHash: "eb5b100dd080afb4213e86f9b91b711bbe442b8a82071161dc9f44cd89ea9738",
    inputPaths: ISSUE380_UI_COMPLETION_LIBRARY_INTERACTION_INPUT_PATHS,
    changedPaths: ["frontend/src/components/EditorialHomeLibrarySurfaces.jsx", "frontend/src/styles/library-paper-review.css", "frontend/src/pages/Library.jsx"],
    unchangedPaths: ["frontend/src/components/ReferencePublicPages.css"],
    authorization: "OWNER_AUTHORIZATION_ISSUE380_UI_COMPLETION_INTEGRITY_MAINTENANCE",
  },
  [PR397_LIBRARY_INTERACTION_BASELINE]: {
    reviewedSource: { commit: "eeea9f38a636ffb9de156b4edafcabd269e417ee", tree: "deb729a72009a41f4cdb0c05769b8d0f0e454f9b", base: "08d95c01574571ee05b6c6513b60de150922bb61" },
    previous: { recordPath: ISSUE380_UI_COMPLETION_LIBRARY_INTERACTION_BASELINE, commit: "2fc56906697e016b570b3fd13d9673717408a60a", hash: "eb5b100dd080afb4213e86f9b91b711bbe442b8a82071161dc9f44cd89ea9738" },
    authorizedHash: "99f0892ea0c1de2de7c11c90d7b0a36f09ed40ecdc0be2af7249d1de089c3f99",
    inputPaths: ISSUE380_UI_COMPLETION_LIBRARY_INTERACTION_INPUT_PATHS,
    changedPaths: ["frontend/src/components/EditorialHomeLibrarySurfaces.jsx"],
    unchangedPaths: ["frontend/src/components/ReferencePublicPages.css", "frontend/src/styles/library-paper-review.css", "frontend/src/pages/Library.jsx"],
    authorization: "OWNER_AUTHORIZATION_PR397_HOME_TESTIMONIALS_INTEGRITY_MAINTENANCE",
  },
  [PR399_LIBRARY_INTERACTION_BASELINE]: {
    reviewedSource: { commit: "db5c8f70a5546766c90b196eb85cdb18be59ceca", tree: "98e6048aec0406db0d3e86494692beee877cd4ef", base: "23591a938735b16c8657f63e31ada70794bc0521" },
    previous: { recordPath: PR397_LIBRARY_INTERACTION_BASELINE, commit: "eeea9f38a636ffb9de156b4edafcabd269e417ee", hash: "99f0892ea0c1de2de7c11c90d7b0a36f09ed40ecdc0be2af7249d1de089c3f99" },
    authorizedHash: "eb5b100dd080afb4213e86f9b91b711bbe442b8a82071161dc9f44cd89ea9738",
    inputPaths: ISSUE380_UI_COMPLETION_LIBRARY_INTERACTION_INPUT_PATHS,
    changedPaths: ["frontend/src/components/EditorialHomeLibrarySurfaces.jsx"],
    unchangedPaths: ["frontend/src/components/ReferencePublicPages.css", "frontend/src/styles/library-paper-review.css", "frontend/src/pages/Library.jsx"],
    authorization: "ISSUE_380_COMMENT_5668321194_CONTENT_GOVERNANCE_REMEDIATION",
  },
  [PR414_LIBRARY_INTERACTION_BASELINE]: {
    reviewedSource: { commit: "b6bb598457c3a425c1b8dc77c78db431a95b36e0", tree: "675f7ba7226db6d5de10bf8f1e82995f7d3ff692", base: "24d11e030cdd8401a200379baf404ffb2db37613" },
    previous: { recordPath: PR399_LIBRARY_INTERACTION_BASELINE, commit: "db5c8f70a5546766c90b196eb85cdb18be59ceca", hash: "eb5b100dd080afb4213e86f9b91b711bbe442b8a82071161dc9f44cd89ea9738" },
    authorizedHash: "7bd2fc4b5dc9dcac43a1a9a4086c92075d9ea5443262e77b99385841f66853f4",
    inputPaths: ISSUE380_UI_COMPLETION_LIBRARY_INTERACTION_INPUT_PATHS,
    changedPaths: ["frontend/src/pages/Library.jsx"],
    unchangedPaths: ["frontend/src/components/EditorialHomeLibrarySurfaces.jsx", "frontend/src/components/ReferencePublicPages.css", "frontend/src/styles/library-paper-review.css"],
    authorization: "DIRECT_OWNER_AUTHORIZATION_PR414_HELD_RELEASE_UAT_FAIL_CLOSED",
  },
  [PR416_LIBRARY_INTERACTION_BASELINE]: {
    reviewedSource: { commit: "e41894f08852ca25317cdf40ded642765eade46e", tree: "d3461ccf23014184840daab903fc08db1539f7a1", base: "f4035048d4148bc0edbe817947aa1dcc582505d9" },
    previous: { recordPath: PR414_LIBRARY_INTERACTION_BASELINE, commit: "b6bb598457c3a425c1b8dc77c78db431a95b36e0", hash: "7bd2fc4b5dc9dcac43a1a9a4086c92075d9ea5443262e77b99385841f66853f4" },
    authorizedHash: "29dc1e90c0fbf4bffcd9edbdd1878c94c2647d039528878c70bb15669f90366f",
    inputPaths: ISSUE380_UI_COMPLETION_LIBRARY_INTERACTION_INPUT_PATHS,
    changedPaths: ["frontend/src/components/EditorialHomeLibrarySurfaces.jsx"],
    unchangedPaths: ["frontend/src/components/ReferencePublicPages.css", "frontend/src/styles/library-paper-review.css", "frontend/src/pages/Library.jsx"],
    authorization: "DIRECT_OWNER_AUTHORIZATION_PR416_POST_LAUNCH_READER_UI_MANDATE",
  },
  [HOME_SECTIONS_LIBRARY_INTERACTION_BASELINE]: {
    reviewedSource: { commit: "5c950bfdaa5d7fb5da6fd21c0c324333d7cbff2f", tree: "2d11851680b06f80bf62a0c6014db5cddab26ce8", base: "a08a73e1c44041739ea452f947623a3ff1302d3e" },
    previous: { recordPath: PR416_LIBRARY_INTERACTION_BASELINE, commit: "e41894f08852ca25317cdf40ded642765eade46e", hash: "29dc1e90c0fbf4bffcd9edbdd1878c94c2647d039528878c70bb15669f90366f" },
    authorizedHash: "3cbf2dda50902d4745849eb8157af447cf26af0ceb17e93ba9aaf604e621ffc7",
    inputPaths: ISSUE380_UI_COMPLETION_LIBRARY_INTERACTION_INPUT_PATHS,
    changedPaths: ["frontend/src/components/EditorialHomeLibrarySurfaces.jsx"],
    unchangedPaths: ["frontend/src/components/ReferencePublicPages.css", "frontend/src/styles/library-paper-review.css", "frontend/src/pages/Library.jsx"],
    authorization: "DIRECT_OWNER_REQUEST_RESTORE_HOME_JOURNEY_AND_PASS_SECTIONS",
  },
  [INDIA_COMMERCIAL_CUTOVER_HOME_LIBRARY_INTERACTION_BASELINE]: {
    reviewedSource: { commit: "b84884c8971f6ba7b7b5b8ac2c9a1910845970ec", tree: "94a20566c50c9c3085d2871cac1bb68532973a31", base: "6909c26c334086767a7dfcb3f709eee66ac2ea9d" },
    previous: { recordPath: HOME_SECTIONS_LIBRARY_INTERACTION_BASELINE, commit: "5c950bfdaa5d7fb5da6fd21c0c324333d7cbff2f", hash: "3cbf2dda50902d4745849eb8157af447cf26af0ceb17e93ba9aaf604e621ffc7" },
    authorizedHash: "c2f93da984c39f54915df94541f98ce1931e128781b9a9c69621d66b57ac1846",
    inputPaths: ISSUE380_UI_COMPLETION_LIBRARY_INTERACTION_INPUT_PATHS,
    changedPaths: ["frontend/src/components/EditorialHomeLibrarySurfaces.jsx"],
    unchangedPaths: ["frontend/src/components/ReferencePublicPages.css", "frontend/src/styles/library-paper-review.css", "frontend/src/pages/Library.jsx"],
    authorization: "DIRECT_OWNER_AUTHORIZATION_INDIA_COMMERCIAL_GO_LIVE_2026_09_25",
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

export function libraryInteractionSurfaceHash(root = process.cwd(), inputPaths = LIBRARY_INTERACTION_INPUT_PATHS) {
  const listing = [...inputPaths]
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
  const { contract } = expected;
  const contractInputPaths = contract.inputPaths || LIBRARY_INTERACTION_INPUT_PATHS;
  const inputPathsMatch = Array.isArray(baseline.input_paths)
    && baseline.input_paths.length === contractInputPaths.length
    && baseline.input_paths.every((value, index) => value === contractInputPaths[index]);
  const changedPaths = baseline.reviewed_source_comparison?.changed_paths_within_input_set;
  const unchangedPaths = baseline.reviewed_source_comparison?.unchanged_paths_within_input_set;
  const previous = baseline.previous_baseline;
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
    || (contract.reviewedSource.base && baseline.reviewed_source?.base !== contract.reviewedSource.base)
    || !GIT_OBJECT_ID.test(baseline.reviewed_source?.commit || "") || !GIT_OBJECT_ID.test(baseline.reviewed_source?.tree || "")
    || (contract.reviewedSource.base && !GIT_OBJECT_ID.test(baseline.reviewed_source?.base || ""))
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
  const observed_surface_sha256 = libraryInteractionSurfaceHash(root, baseline.input_paths);
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
