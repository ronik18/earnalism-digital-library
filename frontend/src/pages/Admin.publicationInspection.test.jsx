import React, { act } from "react";
import { createRoot } from "react-dom/client";

const mockGet = jest.fn();

jest.mock("../lib/api", () => ({
  api: { get: (...args) => mockGet(...args) },
  formatError: jest.fn(),
  formatMinutes: jest.fn(),
}));
jest.mock("../context/AuthContext", () => ({ useAuth: () => ({}) }));
jest.mock("../context/SettingsContext", () => ({ useSettings: () => ({}) }));
jest.mock("../components/BrandMark", () => () => null);
jest.mock("../components/Admin/ChapterUpload", () => () => null);
jest.mock("../components/Admin/CoverUpload", () => () => null);
jest.mock("../components/Admin/CoverManager", () => () => null);
jest.mock("../components/Admin/PublishingWorkflowPanel", () => () => null);
jest.mock("../lib/images", () => ({ normalizeImageUrl: jest.fn(), optimizedImageUrl: jest.fn() }));
jest.mock("../hooks/useSEO", () => jest.fn());
jest.mock("sonner", () => ({ toast: { error: jest.fn() } }));
jest.mock("react-router-dom", () => ({ Link: ({ children }) => <a>{children}</a>, Navigate: () => null, useNavigate: () => jest.fn() }));

import { PublicationInspectionAdmin } from "./Admin";

globalThis.IS_REACT_ACT_ENVIRONMENT = true;

function fixture(overrides = {}) {
  return {
    inspection_scope: "YUGALANGURIYA_ONLY",
    observed_at: "2026-09-19T10:00:00.000Z",
    complete: true,
    errors: [],
    limitations: {
      atomic_snapshot: false,
      storage_or_cdn_certification: false,
      query_max_time_ms: 250,
      overall_deadline_ms: 1500,
      note: "Independent read-only metadata queries.",
    },
    identity: {
      slug: "yugalanguriya",
      canonical_title: "Yugalanguriya",
      edition_identity: "fixture-edition",
      package_metadata_status: "PRESENT",
      availability_reason: "NOT_IN_CURRENT_CONTROLLED_LIVE_CATALOG",
    },
    activation_pointer: { status: "PRESENT", selected_version: "v-safe", generation: 2, metadata_status: "OBSERVED" },
    retained_manifests: {
      status: "OBSERVED",
      limit: 20,
      truncated: false,
      pointer_version_in_returned_records: "PRESENT_IN_RETURNED_SET",
      records: [{ segmentation_version: "v-safe", manifest_version: "m-safe", status: "active", total_pages: 13, metadata_status: "OBSERVED", stored_segment_count: 13, segment_count_status: "OBSERVED", protected_page_exists: true, protected_page_status: "OBSERVED" }],
    },
    active_manifest: { status: "OBSERVED", active_count: 1, selection_state: "SINGLE_ACTIVE_MANIFEST", selected: { segmentation_version: "v-safe", manifest_version: "m-safe", status: "active", total_pages: 13, metadata_status: "OBSERVED", stored_segment_count: 13, segment_count_status: "OBSERVED", protected_page_exists: true, protected_page_status: "OBSERVED" } },
    consistency: { status: "POINTER_MATCHES_ACTIVE_MANIFEST", non_atomic: true, release_readiness: "NOT_DETERMINED_BY_METADATA_INSPECTION" },
    protected_page: { segmentation_version: "v-safe", page_index: 4, status: "OBSERVED", exists: true },
    active_text_sessions: { status: "OBSERVED", active_text_session_count: 0 },
    ...overrides,
  };
}

function deferred() {
  let resolve;
  let reject;
  const promise = new Promise((res, rej) => { resolve = res; reject = rej; });
  return { promise, resolve, reject };
}

async function flush() {
  await act(async () => {
    for (let index = 0; index < 8; index += 1) await Promise.resolve();
  });
}

function render(context = "admin-one") {
  const container = document.createElement("div");
  document.body.appendChild(container);
  const root = createRoot(container);
  act(() => root.render(<PublicationInspectionAdmin administratorContextKey={context} />));
  return {
    container,
    root,
    click() { act(() => container.querySelector('[data-testid="publication-inspection-run"]').dispatchEvent(new MouseEvent("click", { bubbles: true }))); },
    rerender(nextContext) { act(() => root.render(<PublicationInspectionAdmin administratorContextKey={nextContext} />)); },
    async cleanup() { await act(async () => root.unmount()); container.remove(); },
  };
}

describe("PublicationInspectionAdmin", () => {
  beforeEach(() => { document.body.innerHTML = ""; mockGet.mockReset(); });
  afterEach(() => { document.body.innerHTML = ""; });

  test("renders bounded publication fields and does not overlap inspection requests", async () => {
    mockGet.mockResolvedValue({ data: fixture({ complete: false, errors: [{ component: "active_manifest", code: "READ_FAILED" }] }) });
    const mounted = render();
    mounted.click();
    mounted.click();
    await flush();

    expect(mockGet).toHaveBeenCalledTimes(1);
    expect(mockGet).toHaveBeenCalledWith("/admin/reading-pass/yugalanguriya/publication-inspection");
    expect(mounted.container.textContent).toContain("SINGLE_ACTIVE_MANIFEST");
    expect(mounted.container.textContent).toContain("v-safe");
    expect(mounted.container.textContent).toContain("active_manifest: READ_FAILED");
    expect(mounted.container.querySelector('[data-testid="publication-inspection-manifests"]')).not.toBeNull();
    expect(mounted.container.querySelector('[data-testid="publication-inspection-limitations"]')).not.toBeNull();
    await mounted.cleanup();
  });

  test("clears a previous observation when a refresh fails instead of presenting it as current", async () => {
    mockGet.mockResolvedValueOnce({ data: fixture() }).mockRejectedValueOnce(new Error("synthetic secret: no render"));
    const mounted = render();
    mounted.click();
    await flush();
    expect(mounted.container.textContent).toContain("Yugalanguriya");

    mounted.click();
    await flush();
    expect(mounted.container.textContent).toContain("The inspection could not complete. No result has been inferred.");
    expect(mounted.container.querySelector('[data-testid="publication-inspection-result"]')).toBeNull();
    expect(mounted.container.textContent).not.toContain("synthetic secret");
    await mounted.cleanup();
  });

  test("rejects malformed scope and does not render a truthy string as complete", async () => {
    mockGet.mockResolvedValue({ data: fixture({ complete: "false", identity: { ...fixture().identity, slug: "other-title" } }) });
    const mounted = render();
    mounted.click();
    await flush();

    expect(mounted.container.textContent).toContain("No result has been inferred.");
    expect(mounted.container.querySelector('[data-testid="publication-inspection-result"]')).toBeNull();
    await mounted.cleanup();
  });

  test("ignores late results after unmount or administrator-context replacement", async () => {
    const pending = deferred();
    mockGet.mockReturnValueOnce(pending.promise);
    const mounted = render("admin-one");
    mounted.click();
    mounted.rerender("admin-two");
    await act(async () => { pending.resolve({ data: fixture() }); await Promise.resolve(); });

    expect(mounted.container.querySelector('[data-testid="publication-inspection-result"]')).toBeNull();
    expect(mounted.container.textContent).toContain("No inspection has been run in this browser session.");
    await mounted.cleanup();
  });
});
