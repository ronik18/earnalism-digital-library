import React, { act } from "react";
import { createRoot } from "react-dom/client";
import { MemoryRouter, Routes, Route } from "react-router-dom";
import BookDetail from "./BookDetail";
import { api } from "../lib/api";
import * as pass from "../lib/readingPassApi";
let mockUser = null;
jest.mock('react-router-dom', () => { const { TextEncoder, TextDecoder } = require('util'); globalThis.TextEncoder = TextEncoder; globalThis.TextDecoder = TextDecoder; return require('react-router'); }, { virtual: true });
jest.mock('../lib/api', () => ({ api: { get: jest.fn() } }));
jest.mock('../context/AuthContext', () => ({ useAuth: () => ({ user: mockUser }) }));
jest.mock('../lib/readingPassApi', () => ({ getReadingPassPosition: jest.fn(), startReadingPassSession: jest.fn(), saveReadingPassPosition: jest.fn() }));
jest.mock('../hooks/useSEO', () => () => {});
jest.mock('../lib/funnelAnalytics', () => ({ trackFunnelEvent: jest.fn(), trackPageAnalyticsView: jest.fn() }));
jest.mock('../components/BookCoverImage', () => () => null);
globalThis.IS_REACT_ACT_ENVIRONMENT = true;
const slug = 'a-white-heron';
const book = { slug, title: 'A White Heron', author: 'Sarah Orne Jewett', publication_status: 'LIVE_APPROVED', reader_enabled: true, is_published: true, audio_enabled: false };
const canonicalPages = { page_count: 7, schema_version: 's1', content_revision: 'v1', pages: Array.from({ length: 7 }, (_, i) => ({ page_number: i + 1, chapter_id: 'c1' })) };
let container, root;
beforeEach(() => { jest.clearAllMocks(); localStorage.clear(); mockUser = null; container = document.createElement('div'); document.body.appendChild(container); root = createRoot(container);
  api.get.mockImplementation(async url => ({ data: url.startsWith('/books/') ? book : { book: { slug }, audio: { enabled: false }, access: { reading_pass: { enabled: true, segments_ready: true } }, canonical_pages: canonicalPages } })); });
afterEach(async () => { await act(async () => root.unmount()); container.remove(); });
async function mount() { await act(async () => root.render(<MemoryRouter initialEntries={['/book/' + slug]}><Routes><Route path="/book/:slug" element={<BookDetail />} /></Routes></MemoryRouter>)); }
const primary = () => container.querySelector('[data-testid="start-reading"]');
test('guest details never query private reading positions', async () => { await mount(); expect(pass.getReadingPassPosition).not.toHaveBeenCalled(); expect(container.querySelector('[data-testid="reading-position-empty"]')).toBeNull(); });
test('confirmed empty progress is visible before Read without any session or save', async () => {
  mockUser = { id: 'reader-a', role: 'user' }; pass.getReadingPassPosition.mockResolvedValue({ content_id: slug, content_type: 'text', version: 0, position: {} });
  await mount(); expect(container.querySelector('[data-testid="reading-position-empty"]').textContent).toBe('No saved reading progress.');
  expect(primary().getAttribute('href')).toBe('/reader/' + slug); expect(pass.getReadingPassPosition).toHaveBeenCalledTimes(1);
  expect(pass.startReadingPassSession).not.toHaveBeenCalled(); expect(pass.saveReadingPassPosition).not.toHaveBeenCalled();
});
test('compatible existing progress offers Continue with the unchanged local-first entry URL', async () => {
  mockUser = { id: 'reader-a', role: 'user' }; pass.getReadingPassPosition.mockResolvedValue({ user_id: mockUser.id, content_id: slug, content_type: 'text', version: 2, publication_version_compatibility: 'active', position: { canonical_page_index: 4, chapter_id: 'c1', segmentation_version: 's1', manifest_version: 'v1', publication_version_state: 'bound' } });
  await mount(); expect(primary().textContent.trim()).toBe('Continue reading'); expect(primary().getAttribute('href')).toBe('/reader/' + slug); expect(container.querySelector('[data-testid="reading-position-empty"]')).toBeNull();
});
test('lookup denial does not label a book new or block its normal Read entry', async () => {
  mockUser = { id: 'reader-a', role: 'user' }; pass.getReadingPassPosition.mockRejectedValue({ response: { status: 401 } });
  await mount(); expect(primary().getAttribute('href')).toBe('/reader/' + slug); expect(container.querySelector('[data-testid="reading-position-empty"]')).toBeNull(); expect(pass.getReadingPassPosition).toHaveBeenCalledTimes(1);
});
test('a foreign zero-version record is never presented as no progress', async () => {
  mockUser = { id: 'reader-a', role: 'user' }; pass.getReadingPassPosition.mockResolvedValue({ user_id: 'other', content_id: slug, content_type: 'text', version: 0, position: {} });
  await mount(); expect(container.querySelector('[data-testid="reading-position-empty"]')).toBeNull();
});

test('an unreleased edition does not query private positions even with runtime metadata', async () => {
  mockUser = { id: 'reader-a', role: 'user' };
  api.get.mockImplementation(async url => ({ data: url.startsWith('/books/') ? { ...book, publication_status: 'DRAFT' } : { book: { slug }, audio: { enabled: false }, access: { reading_pass: { enabled: true, segments_ready: true } }, canonical_pages: canonicalPages } }));
  await mount(); expect(pass.getReadingPassPosition).not.toHaveBeenCalled(); expect(container.querySelector('[data-testid="reading-position-empty"]')).toBeNull();
});
