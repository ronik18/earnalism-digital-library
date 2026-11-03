import React, { act, Suspense } from 'react';
import { createRoot } from 'react-dom/client';
jest.mock('react-router-dom', () => {
  const { TextEncoder, TextDecoder } = require('util');
  globalThis.TextEncoder = TextEncoder; globalThis.TextDecoder = TextDecoder;
  return require('react-router');
}, { virtual: true });
jest.mock('@vercel/analytics/react', () => ({ Analytics: () => null }), { virtual: true });
jest.mock('./context/AuthContext', () => ({ AuthProvider: ({ children }) => children }));
jest.mock('./context/SettingsContext', () => ({ SettingsProvider: ({ children }) => children }));
jest.mock('./components/Layout', () => () => null);
jest.mock('./pages/Home', () => () => null);
jest.mock('./components/AppToaster', () => ({ AppToaster: () => null }));
jest.mock('./pages/Reader', () => () => <p data-testid="legacy-admin">Server-verified administrative preview</p>);
import { MemoryRouter, Routes, Route, useLocation } from 'react-router-dom';
import { LegacyReaderRoute, LegacyListenerRedirect } from './App';
globalThis.IS_REACT_ACT_ENVIRONMENT = true;
function Destination() { const location = useLocation(); return <output>{location.pathname}{location.search}{location.hash}</output>; }
let root, container;
beforeEach(() => { container = document.createElement('div'); document.body.appendChild(container); root = createRoot(container); });
afterEach(async () => { await act(async () => root.unmount()); container.remove(); });
async function visit(entry) {
  await act(async () => root.render(<MemoryRouter initialEntries={[entry]}><Suspense fallback={<p>Loading</p>}><Routes>
    <Route path="/reader-legacy/:slug" element={<LegacyReaderRoute />} />
    <Route path="/listener-legacy/:slug" element={<LegacyListenerRedirect />} />
    <Route path="*" element={<Destination />} />
  </Routes></Suspense></MemoryRouter>));
}

test.each([
  ['/reader-legacy/radharani?p=2&a=120&r=retained#note', '/reader/radharani?p=2&a=120&r=retained#note'],
  ['/reader-legacy/radharani?listen=1&p=2', '/listener/radharani?p=2'],
  ['/reader-legacy/radharani?listen=1&preview=admin&p=31', '/listener/radharani?preview=admin&p=31'],
  ['/listener-legacy/radharani?listen=1&t=17#resume', '/listener/radharani?t=17#resume'],
  ['/reader-legacy/radharani?preview=Admin', '/reader/radharani?preview=Admin'],
])('legacy URL %s uses the protected current route', async (entry, expected) => {
  await visit(entry);
  expect(container.querySelector('output').textContent).toBe(expected);
  expect(container.querySelector('[data-testid="legacy-admin"]')).toBeNull();
});

test('the exact admin-preview entry preserves the server-verified authoring surface', async () => {
  await visit('/reader-legacy/radharani?preview=admin');
  expect(container.querySelector('[data-testid="legacy-admin"]')).not.toBeNull();
  // This chooses a UI surface only. The actual backend chapter route still
  // denies every non-admin principal before returning any chapter body.
});
