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
  expect(api.get.mock.calls[0][1].timeout).toBe(15000);
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
