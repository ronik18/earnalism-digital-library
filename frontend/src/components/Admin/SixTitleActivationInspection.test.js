import React, { act } from "react";
import { createRoot } from "react-dom/client";
import Inspector from "./SixTitleActivationInspection";
import { api } from "../../lib/api";
jest.mock("../../lib/api", () => ({ api: { get: jest.fn() } }), { virtual: true });
const slugs = ["the-art-of-money-getting", "the-call-of-the-wild", "the-cop-and-the-anthem", "dsires-baby", "love-of-life", "the-time-machine"];
const good = (slug) => ({ status: 200, data: { book_slug: slug, segmentation_version: "segments-1", version: "manifest-1", activation_generation: 0 } });
let host, root;
const receipt = () => JSON.parse(host.querySelector("pre").textContent);
const click = () => host.querySelector("button").dispatchEvent(new MouseEvent("click", { bubbles: true }));
beforeEach(async () => { global.IS_REACT_ACT_ENVIRONMENT = true; api.get.mockReset(); host = document.createElement("div"); document.body.append(host); root = createRoot(host); await act(async () => root.render(<Inspector />)); });
afterEach(async () => { if (root) await act(async () => root.unmount()); host.remove(); });
test("explicit action only; exactly six fixed paths/config; strict output projection", async () => {
  expect(api.get).not.toHaveBeenCalled(); expect(receipt().every(r => r.outcome === "NOT_RUN")).toBe(true);
  api.get.mockImplementation(path => Promise.resolve({ ...good(slugs.find(s => path.includes(`/${s}/`))), data: { ...good(slugs.find(s => path.includes(`/${s}/`))).data, secret: "DO_NOT_DISPLAY" } }));
  await act(async () => click());
  expect(api.get.mock.calls.map(c => c[0])).toEqual(slugs.map(s => `/admin/reading-pass/books/${s}/segments/active`));
  for (const [, config] of api.get.mock.calls) { expect(config.skipAuthRedirect).toBe(true); expect(config.signal).toBeInstanceOf(AbortSignal); }
  expect(receipt().every(r => r.outcome === "OBSERVED" && r.http_status === 200 && r.started_at.endsWith("Z") && r.completed_at.endsWith("Z"))).toBe(true);
  expect(Object.keys(receipt()[0].pointer).sort()).toEqual(["activation_generation", "book_slug", "segmentation_version", "version"]);
  expect(host.textContent).not.toContain("DO_NOT_DISPLAY"); expect(host.querySelector("button").disabled).toBe(true);
});
test("synchronous double-click latch and sequential pending request", async () => {
  let resolve; api.get.mockImplementationOnce(() => new Promise(r => { resolve = r; })).mockImplementation(path => Promise.resolve(good(slugs.find(s => path.includes(`/${s}/`)))));
  await act(async () => { click(); click(); }); expect(api.get).toHaveBeenCalledTimes(1);
  await act(async () => resolve(good(slugs[0]))); expect(api.get).toHaveBeenCalledTimes(6);
});
test.each([401, 403, 500])("measured %i stops after partial receipt without retry", async status => {
  api.get.mockResolvedValueOnce(good(slugs[0])).mockRejectedValueOnce({ response: { status, data: { code: 200, secret: "HIDDEN" } } });
  await act(async () => click()); expect(api.get).toHaveBeenCalledTimes(2); expect(receipt()[0].outcome).toBe("OBSERVED"); expect(receipt()[1].http_status).toBe(status); expect(receipt().slice(2).every(r => r.outcome === "NOT_RUN")).toBe(true); expect(host.textContent).not.toContain("HIDDEN");
});
test("body code is never transport status; no-status error stops", async () => {
 api.get.mockRejectedValue({ response: { data: { code: 401 } } }); await act(async () => click()); expect(api.get).toHaveBeenCalledTimes(1); expect(receipt()[0].http_status).toBeNull(); expect(receipt()[0].outcome).toBe("NETWORK_OR_UNMEASURED");
});
test.each([null, [], {}, { book_slug: "wrong", segmentation_version: "s", version: "v", activation_generation: 1 }, { book_slug: slugs[0], segmentation_version: "", version: "v", activation_generation: 1 }, { book_slug: slugs[0], segmentation_version: "s", version: "v", activation_generation: true }, { book_slug: slugs[0], segmentation_version: "s", version: "v", activation_generation: -1 }, { book_slug: slugs[0], segmentation_version: "s", version: "v", activation_generation: Infinity }])("malformed pointer stops and is not projected: %j", async data => {
 api.get.mockResolvedValue({ status: 200, data }); await act(async () => click()); expect(api.get).toHaveBeenCalledTimes(1); expect(receipt()[0].outcome).toBe("INVALID_RESPONSE"); expect(receipt()[0].pointer).toBeUndefined(); expect(receipt()[1].outcome).toBe("NOT_RUN");
});
test("404/409 safe codes record and continue; arbitrary errors are not exported", async () => {
 api.get.mockRejectedValueOnce({ response: { status: 404, data: { detail: { code: "ACTIVE_SEGMENT_VERSION_MISSING", message: "PRIVATE" } } } }).mockRejectedValueOnce({ response: { status: 409, data: { detail: { code: "ACTIVATION_STATE_OUT_OF_SYNC" } } } }).mockImplementation(path => Promise.resolve(good(slugs.find(s => path.includes(`/${s}/`)))));
 await act(async () => click()); expect(api.get).toHaveBeenCalledTimes(6); expect(receipt()[0].error_code).toBe("ACTIVE_SEGMENT_VERSION_MISSING"); expect(receipt()[1].error_code).toBe("ACTIVATION_STATE_OUT_OF_SYNC"); expect(host.textContent).not.toContain("PRIVATE");
});
test("unmount aborts in-flight request and prevents subsequent calls", async () => {
 let resolve; api.get.mockImplementation(() => new Promise(r => { resolve = r; })); await act(async () => click()); const signal = api.get.mock.calls[0][1].signal;
 await act(async () => root.unmount()); root = null; expect(signal.aborted).toBe(true); await act(async () => resolve(good(slugs[0]))); expect(api.get).toHaveBeenCalledTimes(1);
});


describe("404/409 correction delta", () => {
  test.each([
    [404, null], [409, null], [404, []], [409, {}],
    [404, { detail: "ACTIVE_SEGMENT_VERSION_MISSING" }],
    [409, { detail: [] }],
    [404, { detail: { code: "UNKNOWN" } }],
    [409, { detail: { code: "UNKNOWN" } }],
    [404, { detail: { code: "ACTIVATION_STATE_OUT_OF_SYNC" } }],
    [409, { detail: { code: "ACTIVE_SEGMENT_VERSION_MISSING" } }],
    [404, Object.create({ detail: { code: "ACTIVE_SEGMENT_VERSION_MISSING" } })],
    [409, { detail: Object.create({ code: "ACTIVATION_STATE_OUT_OF_SYNC" }) }],
  ])("stops status %i with malformed/mismatched error %j", async (status, data) => {
    api.get.mockResolvedValueOnce(good(slugs[0])).mockRejectedValueOnce({ response: { status, data } });
    await act(async () => click());
    expect(api.get).toHaveBeenCalledTimes(2);
    expect(receipt()[0].outcome).toBe("OBSERVED");
    expect(receipt()[1].http_status).toBe(status);
    expect(receipt()[1].error_code).toBe("UNKNOWN");
    expect(receipt().slice(2).every(row => row.outcome === "NOT_RUN")).toBe(true);
    expect(host.querySelector('[role="status"]').textContent).toBe("STOPPED");
  });
});
