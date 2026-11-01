import React, { act } from "react";
import { createRoot } from "react-dom/client";
import { MemoryRouter, useNavigate } from "react-router-dom";
import Library from "./Library";
import { api } from "../lib/api";
// CRA Jest27 needs the real underlying router for v7 conditional exports.
jest.mock("react-router-dom", () => {
  const { TextEncoder, TextDecoder } = require("util");
  globalThis.TextEncoder = TextEncoder; globalThis.TextDecoder = TextDecoder;
  return require("react-router");
}, { virtual: true });
jest.mock("../lib/api", () => ({ api: { get: jest.fn() } }));
jest.mock("../hooks/useSEO", () => () => {});
const pending = () => { let resolve, reject; const promise = new Promise((yes, no) => { resolve = yes; reject = no; }); return { promise, resolve, reject }; };
const reader = (slug = "frankenstein", title = "Frankenstein") => ({
  slug, title, author: "Mary Shelley", publication_status: "LIVE_APPROVED", reader_enabled: true,
  public_route: `/book/${slug}`, reader_url: `/reader/${slug}`, preview_enabled: true,
  preview_url: `/reader/${slug}`, chapters: [{ id: "preview", is_preview: true }],
});
let container, root, navigate;
function Navigation() { navigate = useNavigate(); return null; }
const mount = async (entries = ["/library"]) => act(async () => {
  root.render(<MemoryRouter initialEntries={entries} initialIndex={0}><Library /><Navigation /></MemoryRouter>);
});
const click = async (element) => act(async () => { element.dispatchEvent(new MouseEvent("click", { bubbles: true })); });
beforeEach(() => {
  global.IS_REACT_ACT_ENVIRONMENT = true; api.get.mockReset();
  container = document.createElement("div"); document.body.appendChild(container); root = createRoot(container);
});
afterEach(async () => { await act(async () => root.unmount()); container.remove(); });
test("books publish independently, with one catalogue and no optional curation request", async () => {
  const request = pending(); api.get.mockReturnValue(request.promise); await mount();
  expect(container.textContent).toContain("Opening the collection");
  await act(async () => request.resolve({ data: [reader()] }));
  expect(container.querySelectorAll('[data-testid="reference-book-frankenstein"]')).toHaveLength(1);
  expect(container.querySelectorAll('[data-testid="library-reference-surface"]')).toHaveLength(1);
  expect(container.querySelector('.reference-library__legacy-content')).toBeNull();
  expect(api.get).toHaveBeenCalledTimes(1);
  expect(api.get.mock.calls[0][0]).toBe("/books");
  expect(api.get.mock.calls[0][1].timeout).toBe(60000);
});
test("empty and failed responses never revive bundled editions; explicit retry recovers", async () => {
  api.get.mockResolvedValueOnce({ data: [] }); await mount();
  expect(container.querySelector('[data-testid="library-catalogue-empty"]')).not.toBeNull();
  expect(container.querySelectorAll('.reference-book-tile')).toHaveLength(0);
  await act(async () => root.unmount()); root = createRoot(container);
  api.get.mockRejectedValueOnce(new Error("timeout")); await mount();
  expect(container.querySelector('[data-testid="library-catalogue-error"]')).not.toBeNull();
  expect(container.querySelectorAll('.reference-book-tile')).toHaveLength(0);
  api.get.mockResolvedValueOnce({ data: [reader()] });
  await click(container.querySelector('[data-testid="library-catalogue-retry"]'));
  expect(container.querySelector('[data-testid="reference-book-frankenstein"]')).not.toBeNull();
});
test("a late aborted response cannot replace the current mounted request", async () => {
  const old = pending(), current = pending(); api.get.mockReturnValueOnce(old.promise).mockReturnValueOnce(current.promise);
  await mount(); const signal = api.get.mock.calls[0][1].signal;
  await act(async () => root.unmount()); root = createRoot(container); await mount();
  expect(signal.aborted).toBe(true);
  await act(async () => old.resolve({ data: [reader()] }));
  expect(container.querySelector('[data-testid="reference-book-frankenstein"]')).toBeNull();
  await act(async () => current.resolve({ data: [reader("the-time-machine", "The Time Machine")] }));
  expect(container.querySelector('[data-testid="reference-book-the-time-machine"]')).not.toBeNull();
});
test("search follows browser back/forward without catalogue refetch", async () => {
  api.get.mockResolvedValue({ data: [reader()] });
  await mount(["/library?q=Frankenstein", "/library?q=NoMatchingEdition"]);
  const input = () => container.querySelector('input[aria-label="Search the Library"]');
  expect(input().value).toBe("Frankenstein");
  await act(async () => navigate(1));
  expect(input().value).toBe("NoMatchingEdition");
  expect(container.querySelectorAll('.reference-book-tile')).toHaveLength(0);
  await act(async () => navigate(-1));
  expect(input().value).toBe("Frankenstein");
  expect(container.querySelector('[data-testid="reference-book-frankenstein"]')).not.toBeNull();
  expect(api.get).toHaveBeenCalledTimes(1);
});

test("each approved audiobook appears once and links to its protected Listener", async () => {
  const books = require("../lib/__fixtures__/libraryCatalogue.public.json");
  api.get.mockResolvedValue({ data: books });
  await mount(["/library?availability=approved-audiobook"]);
  for (const slug of ["the-open-window", "the-selfish-giant"]) {
    const cards = container.querySelectorAll(`[data-testid="reference-book-${slug}"]`);
    expect(cards).toHaveLength(1);
    expect(cards[0].querySelector(`a[href="/listener/${slug}"]`).textContent).toBe("Listen");
  }
  expect(container.querySelectorAll(".reference-book-tile")).toHaveLength(2);
});
test("changing one facet preserves a different legacy facet and exposes legacy stage", async () => {
  api.get.mockResolvedValue({data: require("../lib/__fixtures__/libraryCatalogue.public.json")});
  await mount(["/library?category=gothic-fiction"]);
  await click([...container.querySelectorAll('button')].find(e => e.textContent === 'Novels & novellas'));
  expect(container.querySelector('[aria-label="Remove gothic fiction filter"]')).not.toBeNull();
  expect(container.querySelector('[aria-label="Remove Novels & novellas filter"]')).not.toBeNull();
  await act(async () => navigate('/library?category=short-story'));
  await click([...container.querySelectorAll('button')].find(e => e.textContent === 'mystery'));
  expect(container.querySelector('[aria-label="Remove Short stories & collections filter"]')).not.toBeNull();
  expect(container.querySelector('[aria-label="Remove mystery filter"]')).not.toBeNull();
  await click(container.querySelector('[aria-label="Remove mystery filter"]'));
  expect(container.querySelector('[aria-label="Remove Short stories & collections filter"]')).not.toBeNull();
  await act(async () => navigate('/library?category=pipeline'));
  expect(container.querySelector('[aria-label="Remove In preparation filter"]')).not.toBeNull();
  await click(container.querySelector('[aria-label="Remove In preparation filter"]'));
  expect(container.querySelector('[aria-label="Remove In preparation filter"]')).toBeNull();
});

test("held preparation cards offer enquiry only, never Reader, Listener or paid actions", async () => {
  api.get.mockResolvedValue({data:[reader()]});
  await mount(["/library?q=Calculus%20Made%20Easy"]);
  const cards = container.querySelectorAll('.reference-book-tile');
  expect(cards).toHaveLength(1);
  expect(cards[0].textContent).toContain('In preparation');
  const destinations = [...cards[0].querySelectorAll('a')].map(a=>a.getAttribute('href'));
  expect(destinations.length).toBeGreaterThan(0);
  expect(destinations.every(href=>href.startsWith('/contact?'))).toBe(true);
  expect(cards[0].querySelector('audio,video,button')).toBeNull();
  expect(cards[0].textContent).not.toMatch(/Pass required|Start Reading|Listen/);
});

// Real Axios request configuration flows into a deterministic offline transport.
// Its deadline competes with the response timer; tests do not resolve the mock
// manually or infer timeout behaviour from an assertion on the numeric constant.
function delayedCatalogueTransport(outcomes) {
  const axios = jest.requireActual("axios");
  let requests = 0;
  const instance = axios.create({ adapter: (config) => new Promise((resolve, reject) => {
    const outcome = outcomes[requests++];
    let settled = false;
    const finish = (callback, value) => {
      if (settled) return;
      settled = true; clearTimeout(response); clearTimeout(deadline);
      config.signal?.removeEventListener("abort", abort);
      callback(value);
    };
    const abort = () => finish(reject, new axios.CanceledError("cancelled"));
    const response = setTimeout(() => finish(resolve, {
      data: outcome.data, status: 200, statusText: "OK", headers: {}, config,
    }), outcome.delay);
    const deadline = setTimeout(() => finish(reject, new axios.AxiosError(
      "catalogue transport deadline", "ECONNABORTED", config,
    )), config.timeout);
    config.signal?.addEventListener("abort", abort, { once: true });
    if (config.signal?.aborted) abort();
  }) });
  api.get.mockImplementation((...args) => instance.get(...args));
  return () => requests;
}
const advanceTransport = async (milliseconds) => act(async () => {
  jest.advanceTimersByTime(milliseconds);
  await Promise.resolve(); await Promise.resolve();
});
test("a legitimate 27-second catalogue response survives the former 15-second deadline", async () => {
  jest.useFakeTimers();
  try {
    const count = delayedCatalogueTransport([{ delay: 27000, data: [reader()] }]);
    await mount(); await advanceTransport(15001);
    expect(container.textContent).toContain("Opening the collection");
    expect(container.querySelector('[data-testid="library-catalogue-error"]')).toBeNull();
    await advanceTransport(11999);
    expect(container.querySelector('[data-testid="reference-book-frankenstein"]')).not.toBeNull();
    expect(count()).toBe(1);
  } finally { jest.useRealTimers(); }
});
test("the 60-second transport deadline fails closed until one explicit retry, without late revival", async () => {
  jest.useFakeTimers();
  try {
    const count = delayedCatalogueTransport([
      { delay: 90000, data: [reader()] },
      { delay: 27000, data: [reader("the-time-machine", "The Time Machine")] },
    ]);
    await mount(); await advanceTransport(59999);
    expect(container.querySelector('[data-testid="library-catalogue-error"]')).toBeNull();
    await advanceTransport(1);
    expect(container.querySelector('[data-testid="library-catalogue-error"]')).not.toBeNull();
    expect(container.querySelectorAll('.reference-book-tile')).toHaveLength(0);
    await advanceTransport(30000); // Original response time cannot revive stale inventory.
    expect(container.querySelectorAll('.reference-book-tile')).toHaveLength(0);
    expect(count()).toBe(1);
    await click(container.querySelector('[data-testid="library-catalogue-retry"]'));
    await click(container.querySelector('[data-testid="library-catalogue-retry"]'));
    expect(count()).toBe(2);
    await advanceTransport(27000);
    expect(container.querySelector('[data-testid="reference-book-the-time-machine"]')).not.toBeNull();
    expect(container.querySelector('a[href="/reader/frankenstein"]')).toBeNull();
    expect(count()).toBe(2);
  } finally { jest.useRealTimers(); }
});
