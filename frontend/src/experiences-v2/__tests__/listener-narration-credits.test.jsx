// Frontend route/DOM contracts only; these mocks do not establish a live release.
import React, { act } from "react";
import { createRoot } from "react-dom/client";
import { renderToStaticMarkup } from "react-dom/server";

const mockGet = jest.fn();
const mockStart = jest.fn();
jest.mock("react-router-dom", () => ({
  Link: ({ to, children, ...props }) => <a href={to} {...props}>{children}</a>,
  NavLink: ({ to, children, className, ...props }) => <a href={to} className={typeof className === "function" ? className({ isActive: false }) : className} {...props}>{children}</a>,
  useLocation: () => ({ pathname: "/listen/sredni-vashtar", search: "" }),
  useNavigate: () => jest.fn(),
  useParams: () => ({ slug: "sredni-vashtar" }),
}), { virtual: true });
jest.mock("../../context/AuthContext", () => ({ useAuth: () => ({ user: { id: "test-only-member" } }) }));
jest.mock("../../lib/api", () => ({ userApi: { get: (...args) => mockGet(...args) } }));
jest.mock("../../lib/readingPassApi", () => ({
  startReadingPassAudioSession: (...args) => mockStart(...args),
  endReadingPassSession: jest.fn(), renewReadingPassLease: jest.fn(),
}));
jest.mock("../../lib/funnelAnalytics", () => ({ trackFunnelEvent: jest.fn() }));

import NarrationCredits from "../shared/NarrationCredits";
import ListenerExperienceV2 from "../listener/ListenerExperienceV2";
import ListenerExperienceV2Route from "../listener/ListenerExperienceV2Route";
import { listenerReleasePresentation } from "../shared/ReleaseTruthAdapter";

const credits = "AI voice: Verse. Music: Heartwarming/Heartbreaking, Kevin MacLeod (https://incompetech.com), CC BY 4.0 https://creativecommons.org/licenses/by/4.0/; edited.";
const packageVersion = "sha256-8185d1b2e20ea325e0a5cfdcf5346f7511c1ccf49937a438f1305ba7566c383e";
function readerResponse() {
  return {
    book: { slug: "sredni-vashtar", title: "Sredni Vashtar", author: "Saki" },
    access: { authenticated: true, role: "user" },
    audio: { enabled: true, asset_slug: "sredni-vashtar", provider: "", version: "test-only-canonical-version",
      delivery_mode: "PROTECTED_PACKAGE_V2", package_version: packageVersion, duration_ms: 638105,
      release_gate: "APPROVED", qa_status: "QA_PASSED", assets: {}, narration_disclosure: credits },
  };
}
function bookFromResponse(response = readerResponse()) {
  return { ...response.book, _readerManifest: { access: response.access, audio: response.audio } };
}
function privateBook() {
  return { slug: "the-open-window", title: "The Open Window", _readerManifest: {
    access: { authenticated: true, role: "user" },
    audio: { enabled: false, assets: {}, narration_disclosure: "Old public edition credits", transport_canary: {
      enabled: true, slug: "the-open-window", scope: "native_replacement_authorized_member_only",
      package_version: packageVersion, release_descriptor_sha256: "b".repeat(64), duration_ms: 491436,
      narration_disclosure: credits,
    } },
  } };
}
function domFor(element) {
  const host = document.createElement("div");
  host.innerHTML = renderToStaticMarkup(element);
  return host;
}

globalThis.IS_REACT_ACT_ENVIRONMENT = true;

beforeEach(() => { mockGet.mockReset(); mockStart.mockReset(); });

test("real route, adapter and Listener render API-shaped credits before authorization without media or debit", async () => {
  mockGet.mockResolvedValue({ data: readerResponse() });
  const host = document.createElement("div"); document.body.appendChild(host);
  const root = createRoot(host);
  try {
    await act(async () => { root.render(<ListenerExperienceV2Route />); });
    const panel = host.querySelector('[data-testid="listener-narration-credits"]');
    expect(panel.textContent).toContain("Verse");
    for (const text of ["Heartwarming", "Heartbreaking", "Kevin MacLeod", "CC BY 4.0", "edited."]) expect(panel.textContent).toContain(text);
    expect(panel.closest(".listener-v2__main")).not.toBeNull();
    expect(panel.closest(".listener-v2__side")).toBeNull(); // This aside is hidden on mobile.
    expect([...panel.querySelectorAll("a")].map((a) => a.href)).toEqual(["https://incompetech.com/", "https://creativecommons.org/licenses/by/4.0/"]);
    expect(mockGet).toHaveBeenCalledTimes(1);
    expect(mockGet.mock.calls[0][0]).toMatch(/^\/reader\/book\/sredni-vashtar\/manifest\?/);
    expect(mockStart).not.toHaveBeenCalled(); expect(host.querySelector("audio")).toBeNull();
  } finally { await act(async () => { root.unmount(); }); host.remove(); }
});

test("reader-only/unapproved response cannot reveal credits or listening controls", async () => {
  const value = readerResponse(); value.audio = { enabled: false, assets: {}, narration_disclosure: credits };
  mockGet.mockResolvedValue({ data: value });
  const host = document.createElement("div"); document.body.appendChild(host); const root = createRoot(host);
  try {
    await act(async () => { root.render(<ListenerExperienceV2Route />); });
    expect(host.textContent).toContain("Listening unavailable");
    expect(host.querySelector('[data-testid="listener-narration-credits"]')).toBeNull();
    expect(mockStart).not.toHaveBeenCalled(); expect(host.querySelector("audio")).toBeNull();
  } finally { await act(async () => { root.unmount(); }); host.remove(); }
});

test("selected private candidate uses its own disclosure and never falls back to the public edition", () => {
  const value = privateBook();
  expect(listenerReleasePresentation(value).narrationDisclosure).toBe(credits);
  delete value._readerManifest.audio.transport_canary.narration_disclosure;
  const host = domFor(<ListenerExperienceV2 book={value} />);
  expect(host.querySelector('[data-testid="listener-narration-credits"]')).toBeNull();
  expect(host.textContent).not.toContain("Old public edition credits");
});

test("guest/private-candidate denial and visual fixtures do not invent credits", () => {
  const value = privateBook(); value._readerManifest.access.authenticated = false;
  expect(domFor(<ListenerExperienceV2 book={value} />).querySelector('[data-testid="listener-narration-credits"]')).toBeNull();
  expect(domFor(<ListenerExperienceV2 book={bookFromResponse()} fixture />).querySelector('[data-testid="listener-narration-credits"]')).toBeNull();
});

test("a different protected package cannot inherit the selected edition's credits", () => {
  const host = domFor(<ListenerExperienceV2 book={bookFromResponse()} audioManifest={{ valid: true, packageVersion: `sha256-${"c".repeat(64)}`, tracks: [] }} />);
  expect(host.querySelector('[data-testid="listener-narration-credits"]')).toBeNull();
});

test("matching package retains credits during authorization without a new media request", () => {
  const host = domFor(<ListenerExperienceV2 book={bookFromResponse()} audioManifest={{ valid: true, packageVersion, tracks: [] }} />);
  expect(host.querySelector('[data-testid="listener-narration-credits"]').textContent).toContain("Kevin MacLeod");
  expect(host.querySelector("audio")).toBeNull();
});

test("missing or malformed disclosure has no invented narrator/music credit", () => {
  for (const disclosure of [null, "", "  ", {}]) expect(domFor(<NarrationCredits disclosure={disclosure} />).textContent).toBe("");
});

test("attribution links trim sentence punctuation and escape HTML without script links", () => {
  const host = domFor(<NarrationCredits disclosure={'<img src=x onerror=alert(1)> javascript:alert(1) (https://incompetech.com), https://creativecommons.org/licenses/by/4.0/; edited.'} />);
  expect(host.querySelector("img")).toBeNull();
  expect(host.textContent).toContain("<img src=x onerror=alert(1)>");
  expect(host.querySelector('[href^="javascript:"]')).toBeNull();
  for (const a of host.querySelectorAll("a")) { expect(a.target).toBe("_blank"); expect(a.rel).toBe("noopener noreferrer"); }
  expect([...host.querySelectorAll("a")].map((a) => a.getAttribute("href"))).toEqual(["https://incompetech.com", "https://creativecommons.org/licenses/by/4.0/"]);
});


test("a valid protected package with missing selected-version metadata has no inherited credits", () => {
  const value = bookFromResponse();
  value._readerManifest.audio.package_version = "";
  value._readerManifest.audio.provider = "legacy-provider";
  const host = domFor(<ListenerExperienceV2 book={value} audioManifest={{ valid: true, packageVersion, tracks: [] }} />);
  expect(host.querySelector('[data-testid="listener-narration-credits"]')).toBeNull();
});
