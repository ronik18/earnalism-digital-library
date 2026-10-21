import { useEffect, useRef, useState } from "react";
import { api } from "../../lib/api";

const UUID = "74251b53-9e18-49fb-9fff-bb7c505633d4";
const ENDPOINT = `/admin/books/${UUID}/serving-binding`;
const HASH = /^[a-fA-F0-9]{64}$/;
const hash = (value) => typeof value === "string" && HASH.test(value);
const HASH_FIELDS = ["source_hash", "content_hash", "provenance_hash", "manifest_sha256", "publication_authorization_sha256", "cover_provenance_sha256"];
const FILES = ["public_book.json", "reader_manifest.json", "approval_evidence.json", "source_evidence.json", "checksum_manifest.json", "publication_manifest.json"];
const BACKEND = Object.freeze({ git_sha: "0f2bb1e728890f1f0e41ded9b12f07c76246bce0", deployment_id: "168e2abf-6b42-455e-b6c8-e2f8b77be4d3",
  project_id: "a8533934-35c4-463e-9f43-577a9ac391ee", service_id: "5af42e7e-f518-4f6a-b602-d9950866501f", environment_id: "580b250c-80ee-48ad-bfbe-fa4e31a6b378" });
const text = (value) => typeof value === "string" && value.length > 0 && value.length <= 2048 && !/[\u0000-\u001f\u007f]/.test(value);
const object = (value) => value && typeof value === "object" && !Array.isArray(value);
const pick = (value, keys) => Object.fromEntries(keys.filter((key) => Object.prototype.hasOwnProperty.call(value, key)).map((key) => [key, value[key]]));
const hashes = (value) => object(value) && Object.values(value).every((v) => hash(v));

export function projectServingBinding(data) {
  if (!object(data) || JSON.stringify(data).length > 65536 ||
      data.schema !== "earnalism.serving-publication-binding.v1" || data.requested_uuid !== UUID ||
      data.slug !== "the-open-window" || data.serving_id !== "controlled-the-open-window" ||
      data.uuid_association !== "exact-database-id-to-slug" || !text(data.selected_root) ||
      !text(data.resolver) || !text(data.selection) || !text(data.limitation) ||
      !text(data.canonical_pointer_source_join) || !text(data.canonical_hash_domain) || !text(data.chapter_hash_domain)) return null;
  if (!hashes(data.metadata_file_sha256) || !FILES.every((f) => hash(data.metadata_file_sha256[f])) ||
      !hashes(data.serving_hashes) || !["source_hash", "content_hash", "provenance_hash"].every((k) => hash(data.serving_hashes[k])) ||
      !object(data.hash_assertions_by_record) || !FILES.every((f) => hashes(data.hash_assertions_by_record[f]))) return null;
  const chapters = data.ordered_chapter_file_hashes;
  const canonical = data.declared_canonical_reader_identity;
  if (!Array.isArray(chapters) || chapters.length < 1 || chapters.length > 200 || !object(canonical) ||
      canonical.chapter_count !== chapters.length || !hash(canonical.content_sha256) ||
      !Array.isArray(canonical.ordered_chapter_sha256) || canonical.ordered_chapter_sha256.length !== chapters.length) return null;
  const ids = new Set();
  const orders = new Set();
  for (let index = 0; index < chapters.length; index += 1) {
    const c = chapters[index];
    const declared = canonical.ordered_chapter_sha256[index];
    if (!object(c) || typeof c.id !== "string" || !/^[A-Za-z0-9_-]+$/.test(c.id) || ids.has(c.id) ||
        !Number.isSafeInteger(c.order) || orders.has(c.order) || (index > 0 && chapters[index - 1].order >= c.order) ||
        c.file !== `chapters/${c.id}.json` || !hash(c.declared_file_sha256) ||
        !object(declared) || declared.id !== c.id || !hash(declared.sha256)) return null;
    ids.add(c.id); orders.add(c.order);
  }
  const pointer = data.canonical_pointer;
  const deployment = data.deployment;
  if (!object(pointer) || !object(pointer.manifest) || !text(pointer.manifest.version) || !text(pointer.manifest.segmentation_version) ||
      !Number.isSafeInteger(pointer.activation_generation) || pointer.activation_generation < 0 || !text(pointer.generation_basis) ||
      !object(deployment) || deployment.status !== "AVAILABLE" || !/^[a-f0-9]{40}$/.test(deployment.git_sha || "") ||
      !Object.entries(BACKEND).every(([key, value]) => deployment[key] === value) ||
      !["deployment_id", "project_id", "service_id", "environment_id"].every((k) => /^[a-f0-9]{8}(?:-[a-f0-9]{4}){3}-[a-f0-9]{12}$/.test(deployment[k] || "")) ||
      !object(data.rights_metadata)) return null;
  const rights = pick(data.rights_metadata, ["rights_tier", "verification_status", "commercial_use_allowed", "approved_to_publish", "publication_status"]);
  if (!Object.values(rights).every((v) => v === null || typeof v === "boolean" || text(v))) return null;
  return {
    ...pick(data, ["schema", "requested_uuid", "uuid_association", "slug", "serving_id", "resolver", "selected_root", "selection", "canonical_hash_domain", "chapter_hash_domain", "limitation", "canonical_pointer_source_join"]),
    metadata_file_sha256: pick(data.metadata_file_sha256, FILES),
    hash_assertions_by_record: Object.fromEntries(FILES.map((f) => [f, pick(data.hash_assertions_by_record[f], HASH_FIELDS)])),
    serving_hashes: pick(data.serving_hashes, HASH_FIELDS),
    declared_canonical_reader_identity: { chapter_count: canonical.chapter_count, content_sha256: canonical.content_sha256,
      ordered_chapter_sha256: canonical.ordered_chapter_sha256.map((c) => pick(c, ["id", "sha256"])) },
    ordered_chapter_file_hashes: chapters.map((c) => pick(c, ["id", "order", "file", "declared_file_sha256"])),
    rights_metadata: rights,
    canonical_pointer: { manifest: pick(pointer.manifest, ["version", "segmentation_version"]),
      activation_generation: pointer.activation_generation, generation_basis: pointer.generation_basis },
    deployment: pick(deployment, ["status", "git_sha", "deployment_id", "project_id", "service_id", "environment_id"]),
  };
}

export default function OpenWindowServingBinding() {
  const started = useRef(false);
  const controller = useRef(null);
  const [receipt, setReceipt] = useState({ outcome: "NOT_RUN", requested_uuid: UUID });
  useEffect(() => () => controller.current?.abort(), []);
  const inspect = async () => {
    if (started.current) return;
    started.current = true;
    const abort = new AbortController();
    controller.current = abort;
    const started_at = new Date().toISOString();
    setReceipt({ outcome: "RUNNING", requested_uuid: UUID, started_at });
    let status = null;
    try {
      const response = await api.get(ENDPOINT, { skipAuthRedirect: true, timeout: 15000, signal: abort.signal });
      status = response.status;
      const metadata = status === 200 ? projectServingBinding(response.data) : null;
      if (!metadata) throw new Error("Invalid metadata response");
      if (!abort.signal.aborted) setReceipt({ outcome: "OBSERVED_METADATA", http_status: status, started_at, completed_at: new Date().toISOString(), metadata });
    } catch (error) {
      if (abort.signal.aborted) return;
      const measured = error.response?.status ?? status;
      setReceipt({ outcome: "STOPPED", requested_uuid: UUID, http_status: Number.isInteger(measured) ? measured : null,
        started_at, completed_at: new Date().toISOString() });
    }
  };
  return <section aria-label="Open Window serving binding" className="rounded border p-4">
    <h2>The Open Window: serving metadata</h2>
    <p>One read-only request using the current admin session. Metadata does not establish audio admission, rights approval or complete-book acceptance.</p>
    <button type="button" className="btn-secondary" onClick={inspect} disabled={receipt.outcome !== "NOT_RUN"}>Read Open Window serving binding</button>
    <p role="status">{receipt.outcome}</p>
    <pre className="whitespace-pre-wrap break-words" data-testid="open-window-serving-binding-receipt">{JSON.stringify(receipt, null, 2)}</pre>
  </section>;
}
