import React, { act } from 'react';
import { createRoot } from 'react-dom/client';
import ReaderExperienceV2 from './ReaderExperienceV2';
import useVisualPagination from './useVisualPagination';
import { READER_SETTINGS_STORAGE_KEY } from '../../lib/readerSettings';
jest.mock('./useVisualPagination', () => ({ __esModule: true, default: jest.fn() }));
jest.mock('./useAuthorizedBookMap', () => ({ __esModule: true, default: () => ({ complete: false, options: [], sourceRef: { current: null }, measureRef: { current: null } }) }));
globalThis.IS_REACT_ACT_ENVIRONMENT = true;
let host, root;
const named = text => [...host.querySelectorAll('button')].find(node => node.getAttribute('aria-label') === text || node.textContent.trim() === text);
const click = async node => act(async () => node.dispatchEvent(new MouseEvent('click', { bubbles: true })));
const render = async (model = {}, access = {}) => act(async () => root.render(<ReaderExperienceV2 model={{ title: 'রাধারাণী', chapterTitle: 'প্রথম পরিচ্ছেদ', language: 'bn', slug: 'isolated-folio', canonicalPage: 1, windowFirst: 1, windowLast: 3, totalPages: 4, previewLimit: 3, sourceRevision: 'isolated-revision', previewContentRevision: 'isolated-book', paragraphs: ['Original isolated fixture.'], contents: [{ page: 1, label: 'Opening' }, { page: 4, label: 'Protected chapter' }], ...model }} access={access} />));
const pages = Array.from({ length: 4 }, (_, index) => ({ start: index * 40, end: (index + 1) * 40, html: `<p>Original isolated fragment ${index + 1}.</p>`, text: `Original isolated fragment ${index + 1}.` }));
beforeEach(() => {
  localStorage.clear(); Object.defineProperty(document, 'fullscreenElement', { configurable: true, writable: true, value: null });
  jest.spyOn(window, 'scrollTo').mockImplementation(() => {});
  useVisualPagination.mockReturnValue({ pages, pending: false, signature: 'isolated-layout', width: 350, height: 640 });
  host = document.createElement('div'); document.body.append(host); root = createRoot(host);
});
afterEach(() => { act(() => root.unmount()); host.remove(); jest.restoreAllMocks(); delete document.exitFullscreen; delete document.fullscreenElement; localStorage.removeItem(READER_SETTINGS_STORAGE_KEY); });

test('Quiet Folio has one reader bar and one page row with literary Bengali defaults', async () => {
  await render();
  expect(host.querySelectorAll('[aria-label="Reader actions"]')).toHaveLength(1);
  expect(host.querySelectorAll('nav[aria-label="Page navigation"]')).toHaveLength(1);
  expect(host.querySelector('.experience-header, .reader-v2__rail, .experience-bottom-nav')).toBeNull();
  expect(host.querySelector('select')).toBeNull();
  const body = host.querySelector('[data-testid="reader-reading-text"]');
  expect(body.style.fontFamily).toContain('Noto Serif Bengali'); expect(body.style.fontSize).toBe('1.25rem');
});

test.each([['Contents', 'Contents and page navigation'], ['Reader settings', 'Reading preferences'], ['Open notes and bookmarks', 'Notes and bookmarks'], ['Edition & credits', 'Edition and credits']])('%s is modal, traps focus, suspends visibility and restores its trigger', async (triggerName, label) => {
  const visibility = jest.fn(); await render({ onVisualPageVisibility: visibility });
  const trigger = named(triggerName); trigger.focus(); await click(trigger);
  const dialog = host.querySelector('dialog'); expect(dialog.getAttribute('aria-modal')).toBe('true');
  expect(host.querySelector('#' + dialog.getAttribute('aria-labelledby')).textContent).toBe(label);
  expect(dialog.contains(document.activeElement)).toBe(true);
  expect(host.querySelector('.reader-folio__surface').hasAttribute('inert')).toBe(true);
  expect(visibility.mock.calls.at(-1)[0]).toBeNull();
  const controls = [...dialog.querySelectorAll('button:not([disabled]), select:not([disabled]), textarea, a[href]')];
  controls.at(-1).focus();
  await act(async () => controls.at(-1).dispatchEvent(new KeyboardEvent('keydown', { key: 'Tab', bubbles: true, cancelable: true })));
  expect(document.activeElement).toBe(controls[0]);
  await act(async () => controls[0].dispatchEvent(new KeyboardEvent('keydown', { key: 'Tab', shiftKey: true, bubbles: true, cancelable: true })));
  expect(document.activeElement).toBe(controls.at(-1));
  await act(async () => dialog.dispatchEvent(new KeyboardEvent('keydown', { key: 'Escape', bubbles: true, cancelable: true })));
  expect(host.querySelector('dialog')).toBeNull(); expect(document.activeElement).toBe(trigger);
  expect(host.querySelector('.reader-folio__surface').hasAttribute('inert')).toBe(false);
  expect(visibility.mock.calls.at(-1)[0]).toMatchObject({ start: 0, end: 40 });
});

test('a modal excludes page-turn keys without changing a nonzero source anchor', async () => {
  const anchor = jest.fn(); await render({ onVisualAnchor: anchor, visualAnchor: 40 });
  await click(named('Contents'));
  await act(async () => host.querySelector('dialog').dispatchEvent(new KeyboardEvent('keydown', { key: 'ArrowRight', bubbles: true })));
  expect(anchor).not.toHaveBeenCalled();
  expect(host.querySelector('[data-testid="reader-reading-text"]').textContent).toContain('fragment 2');
});

test('unsupported fullscreen offers reachable focus reading without claiming native state', async () => {
  await render({ visualAnchor: 80 }); await click(named('Enter fullscreen'));
  expect(host.querySelector('.reader-folio').dataset.nativeFullscreen).toBe('false');
  expect(host.querySelector('.reader-folio').dataset.focusMode).toBe('true');
  expect(host.querySelector('[role="status"]').textContent).toMatch(/unavailable/);
  expect(document.activeElement).toBe(named('Show reader controls'));
  expect(host.querySelector('[data-testid="reader-reading-text"]').textContent).toContain('fragment 3');
  await click(named('Show reader controls'));
  expect(host.querySelector('.reader-folio').dataset.focusMode).toBe('false');
  expect(document.activeElement).toBe(named('Enter fullscreen'));
});

test('native fullscreen follows fullscreenchange and external browser exit, not a resolved promise', async () => {
  const anchor = jest.fn(); await render({ visualAnchor: 80, onVisualAnchor: anchor });
  const folio = host.querySelector('.reader-folio'); folio.requestFullscreen = jest.fn().mockResolvedValue(undefined);
  await click(named('Enter fullscreen')); expect(folio.requestFullscreen).toHaveBeenCalledTimes(1);
  expect(folio.dataset.nativeFullscreen).toBe('false'); expect(folio.dataset.focusMode).toBe('false');
  await act(async () => { document.fullscreenElement = folio; document.dispatchEvent(new Event('fullscreenchange')); });
  expect(folio.dataset.nativeFullscreen).toBe('true'); expect(folio.dataset.focusMode).toBe('true');
  await act(async () => { document.fullscreenElement = null; document.dispatchEvent(new Event('fullscreenchange')); });
  expect(folio.dataset.nativeFullscreen).toBe('false'); expect(folio.dataset.focusMode).toBe('false');
  expect(anchor).not.toHaveBeenCalled();
  expect(host.querySelector('[data-testid="reader-reading-text"]').textContent).toContain('fragment 3');
});

test('fullscreen denial falls back to focus with truthful status', async () => {
  await render(); const folio = host.querySelector('.reader-folio');
  folio.requestFullscreen = jest.fn().mockRejectedValue(new Error('Synthetic user-agent denial'));
  await click(named('Enter fullscreen'));
  expect(folio.dataset.nativeFullscreen).toBe('false'); expect(folio.dataset.focusMode).toBe('true');
  expect(host.querySelector('[role="status"]').textContent).toMatch(/not opened/);
});

test('focus changes preserve the guest third-page continuation gate', async () => {
  const protectedRequest = jest.fn(); const anchor = jest.fn();
  await render({ visualAnchor: 80, onVisualAnchor: anchor, sourceAnchorForOffset: offset => ({ page: 2, offset, revision: 'isolated-revision' }), onRequestProtectedContent: protectedRequest });
  await click(named('Reader settings')); await click(named('Focus reading'));
  expect(host.querySelector('dialog')).toBeNull();
  await click(named('Show reader controls')); await click(named('Next page'));
  expect(protectedRequest).toHaveBeenCalledWith(2, 120, 'isolated-revision', expect.objectContaining({ page: 2, offset: 120 }));
  expect(anchor).not.toHaveBeenCalled();
  expect(host.querySelector('[data-testid="reader-reading-text"]').textContent).not.toContain('fragment 4');
});

test('saved typography survives focus changes', async () => {
  localStorage.setItem(READER_SETTINGS_STORAGE_KEY, JSON.stringify({ readerTypographyVersion: 2, readerTextSizeRem: 1.125, readerFontFamilyPreference: 'sans' }));
  await render(); await click(named('Enter fullscreen'));
  const body = host.querySelector('[data-testid="reader-reading-text"]');
  expect(body.style.fontSize).toBe('1.125rem'); expect(body.style.fontFamily).toContain('Noto Sans Bengali');
});


test('Escape exits browser-independent focus mode and returns a reachable control', async () => {
  await render(); await click(named('Enter fullscreen'));
  await act(async () => window.dispatchEvent(new KeyboardEvent('keydown', { key: 'Escape', bubbles: true, cancelable: true })));
  expect(host.querySelector('.reader-folio').dataset.focusMode).toBe('false');
  expect(document.activeElement).toBe(named('Enter fullscreen'));
});


test.each(['focus', 'native fullscreen'])('%s keeps keyboard page turns available from the dedicated Show controls affordance', async mode => {
  const anchor = jest.fn(); await render({ onVisualAnchor: anchor }, { authorized: true });
  if (mode === 'focus') { await click(named('Reader settings')); await click(named('Focus reading')); }
  else {
    const folio = host.querySelector('.reader-folio');
    await act(async () => { document.fullscreenElement = folio; document.dispatchEvent(new Event('fullscreenchange')); });
  }
  expect(document.activeElement).toBe(named('Show reader controls'));
  await act(async () => document.activeElement.dispatchEvent(new KeyboardEvent('keydown', { key: 'ArrowRight', bubbles: true, cancelable: true })));
  expect(anchor).toHaveBeenLastCalledWith(40);
  expect(host.querySelector('[data-testid="reader-reading-text"]').textContent).toContain('fragment 2');
  await act(async () => document.activeElement.dispatchEvent(new KeyboardEvent('keydown', { key: 'ArrowLeft', bubbles: true, cancelable: true })));
  expect(anchor).toHaveBeenLastCalledWith(0);
  expect(host.querySelector('[data-testid="reader-reading-text"]').textContent).toContain('fragment 1');
});

test('shorter public previews use their actual displayed page total in the progress meter', async () => {
  useVisualPagination.mockReturnValue({ pages: pages.slice(0, 2), pending: false, signature: 'short-layout', width: 350, height: 640 });
  await render({ visualAnchor: 40 });
  expect(host.querySelector('.reader-folio__page-context').textContent).toBe('Preview · 2 of 2');
  expect(host.querySelector('progress').value).toBe(2); expect(host.querySelector('progress').max).toBe(2);
});
