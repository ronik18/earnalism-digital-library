import React, { act } from "react";
import { createRoot } from "react-dom/client";
import Inspector, { projectServingBinding } from "./OpenWindowServingBinding";
import { api } from "../../lib/api";
jest.mock("../../lib/api", () => ({ api: { get: jest.fn() } }));

const uuid = "74251b53-9e18-49fb-9fff-bb7c505633d4";
const digest = "a".repeat(64);
const files = ["public_book.json", "reader_manifest.json", "approval_evidence.json", "source_evidence.json", "checksum_manifest.json", "publication_manifest.json"];
const good = () => ({
  schema: "earnalism.serving-publication-binding.v1", requested_uuid: uuid,
  uuid_association: "exact-database-id-to-slug", slug: "the-open-window", serving_id: "controlled-the-open-window",
  resolver: "reader_book_access_doc/populate_cache=false; controlled packet required", selected_root: "/app/data/controlled_publications/the-open-window",
  selection: "first-complete-controlled-artifact-packet", metadata_file_sha256: Object.fromEntries(files.map(f => [f, digest])),
  hash_assertions_by_record: Object.fromEntries(files.map(f => [f, { source_hash: digest }])),
  serving_hashes: { source_hash: digest, content_hash: digest, provenance_hash: digest },
  declared_canonical_reader_identity: { chapter_count: 1, content_sha256: digest, ordered_chapter_sha256: [{ id: "chapter-1", sha256: digest }] },
  ordered_chapter_file_hashes: [{ id: "chapter-1", order: 1, file: "chapters/chapter-1.json", declared_file_sha256: digest }],
  canonical_hash_domain: "Declared canonical digests", chapter_hash_domain: "Declared JSON-file digests",
  rights_metadata: { commercial_use_allowed: true, approved_to_publish: true },
  canonical_pointer: { manifest: { version: "m1", segmentation_version: "s1" }, activation_generation: 0, generation_basis: "activation-state" },
  deployment: { status: "AVAILABLE", git_sha: "0f2bb1e728890f1f0e41ded9b12f07c76246bce0", deployment_id: "168e2abf-6b42-455e-b6c8-e2f8b77be4d3",
    project_id: "a8533934-35c4-463e-9f43-577a9ac391ee", service_id: "5af42e7e-f518-4f6a-b602-d9950866501f", environment_id: "580b250c-80ee-48ad-bfbe-fa4e31a6b378" },
  limitation: "No audio admission or full-book acceptance", canonical_pointer_source_join: "Pointer does not independently prove source derivation",
});
let root, host;
const receipt = () => JSON.parse(host.querySelector("pre").textContent);
const click = () => host.querySelector("button").dispatchEvent(new MouseEvent("click", { bubbles: true }));
beforeEach(async () => { global.IS_REACT_ACT_ENVIRONMENT = true; api.get.mockReset(); host=document.createElement("div"); document.body.append(host); root=createRoot(host); await act(async () => root.render(<Inspector />)); });
afterEach(async () => { if(root) await act(async () => root.unmount());host.remove(); });
test("explicit one-shot fixed admin request, no mount request or credential handling", async () => {
  expect(api.get).not.toHaveBeenCalled(); api.get.mockResolvedValue({ status:200, data:good() });
  await act(async () => { click();click(); });
  expect(api.get).toHaveBeenCalledTimes(1);
  expect(api.get.mock.calls[0][0]).toBe(`/admin/books/${uuid}/serving-binding`);
  expect(api.get.mock.calls[0][1]).toEqual({skipAuthRedirect:true,timeout:15000,signal:expect.any(AbortSignal)});
  expect(receipt().outcome).toBe("OBSERVED_METADATA"); expect(host.querySelector("button").disabled).toBe(true);
});
test.each([401,403,404,409,500])("HTTP %i stops without retry or raw error export", async status => {
  api.get.mockRejectedValue({response:{status,data:{detail:"DO_NOT_DISPLAY"}}});
  await act(async () => click()); expect(api.get).toHaveBeenCalledTimes(1);
  expect(receipt()).toMatchObject({outcome:"STOPPED",http_status:status});expect(host.textContent).not.toContain("DO_NOT_DISPLAY");
});
test.each([
  data => {data.requested_uuid="other";}, data => {data.slug="other";},
  data => {data.deployment.project_id="00000000-0000-0000-0000-000000000000";},
  data => {data.deployment.git_sha="b".repeat(40);},
  data => {data.canonical_pointer.activation_generation=-1;},
  data => {delete data.metadata_file_sha256[files[0]];},
  data => {data.declared_canonical_reader_identity.ordered_chapter_sha256[0].id="wrong";},
  data => {data.ordered_chapter_file_hashes.push({...data.ordered_chapter_file_hashes[0]});},
])("malformed or mismatched metadata stops", async change => {
  const data=good();change(data);api.get.mockResolvedValue({status:200,data});
  await act(async () => click());expect(receipt().outcome).toBe("STOPPED");expect(receipt().metadata).toBeUndefined();
});
test("unknown payload fields are not retained in the metadata projection", () => {
  const data=good();data.secret="DO_NOT_DISPLAY";data.canonical_pointer.manifest.secret="DO_NOT_DISPLAY";
  data.deployment.secret="DO_NOT_DISPLAY";
  expect(JSON.stringify(projectServingBinding(data))).not.toContain("DO_NOT_DISPLAY");
});
test("unmount aborts and does not follow up", async () => {
  let resolve;api.get.mockImplementation(() => new Promise(r => {resolve=r;}));
  await act(async () => click()); const signal=api.get.mock.calls[0][1].signal;
  await act(async () => root.unmount());root=null;expect(signal.aborted).toBe(true);
  await act(async () => resolve({status:200,data:good()}));expect(api.get).toHaveBeenCalledTimes(1);
});
test.each([null,[],{},"html",{unexpected:"payload"}])("invalid response shape stops: %j", async data => {
  api.get.mockResolvedValue({status:200,data});await act(async () => click());expect(receipt().outcome).toBe("STOPPED");
});
