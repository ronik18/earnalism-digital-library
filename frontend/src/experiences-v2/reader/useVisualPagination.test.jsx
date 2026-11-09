import React, { act } from 'react';
import { createRoot } from 'react-dom/client';
import useVisualPagination from './useVisualPagination';
import { paginateRenderedResponsive } from './visualPagination';
jest.mock('./visualPagination', () => ({ paginateRenderedResponsive: jest.fn() }));
globalThis.IS_REACT_ACT_ENVIRONMENT = true;
let root, host, result, source, viewport, measure;
const refs = {};
function Harness({ revision = 'original' }) {
  result = useVisualPagination({ ...refs, revision, typography: 'Bengali', authorizationScope: 'guest' });
  return null;
}
const render = async (revision) => act(async () => { root.render(<Harness revision={revision} />); });
beforeEach(() => {
  host = document.createElement('div'); document.body.append(host); root = createRoot(host);
  source = document.createElement('div'); source.textContent = 'রাধারাণী';
  viewport = document.createElement('div'); measure = document.createElement('div');
  Object.defineProperties(viewport, { clientWidth: { value: 350 }, clientHeight: { value: 600 } });
  Object.assign(refs, { sourceRef: { current: source }, viewportRef: { current: viewport }, measureRef: { current: measure } });
  Object.defineProperty(document, 'fonts', { configurable: true, value: { load: jest.fn().mockResolvedValue([]), ready: Promise.resolve(), addEventListener: jest.fn(), removeEventListener: jest.fn() } });
  paginateRenderedResponsive.mockReset().mockReturnValue([{ start: 0, end: 8, html: '<p>রাধারাণী</p>' }]);
});
afterEach(() => { act(() => root.unmount()); host.remove(); delete document.fonts; });
test('loads the actual script and refits overflow at most twice without changing source or viewport geometry', async () => {
  await render();
  expect(document.fonts.load).toHaveBeenCalledWith(expect.any(String), 'রাধারাণী');
  expect(paginateRenderedResponsive.mock.calls[0][2]).toBe(600);
  await act(async () => { expect(result.refit(12)).toBe(true); });
  expect(paginateRenderedResponsive.mock.calls.at(-1)[2]).toBe(586);
  expect(result.height).toBe(600);
  await act(async () => { expect(result.refit(4)).toBe(true); });
  expect(paginateRenderedResponsive.mock.calls.at(-1)[2]).toBe(580);
  await act(async () => { expect(result.refit(4)).toBe(false); });
  expect(paginateRenderedResponsive).toHaveBeenCalledTimes(3);
  expect(source.textContent).toBe('রাধারাণী');
  await render('new-source');
  expect(paginateRenderedResponsive.mock.calls.at(-1)[2]).toBe(600);
  await act(async () => { expect(result.refit(2)).toBe(true); });
});
