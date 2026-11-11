import React, { act } from 'react';
import { createRoot } from 'react-dom/client';
import ReaderExperienceV2, { READER_V2_FIXTURE } from './ReaderExperienceV2';
jest.mock('react-router-dom', () => ({ Link: ({ to, children }) => <a href={to}>{children}</a> }), { virtual: true });
jest.mock('./useVisualPagination', () => () => ({ pending: false, error: '', signature: 'reflow', pages: Array.from({ length: 6 }, (_, i) => ({ start: i * 10, end: (i + 1) * 10, html: `<p>Page ${i + 1}</p>` })) }));
jest.mock('./useAuthorizedBookMap', () => () => ({ sourceRef: { current: null }, measureRef: { current: null }, options: [] }));
globalThis.IS_REACT_ACT_ENVIRONMENT = true;
test('Back from a font-expanded preview returns directly to free text without authorization or charging', () => {
  const scroll = jest.spyOn(window, 'scrollTo').mockImplementation(() => {});
  const container = document.createElement('div'); const root = createRoot(container);
  const onVisualAnchor = jest.fn(); const onRequestProtectedContent = jest.fn();
  const model = { ...READER_V2_FIXTURE, visualFixture: false, visualAnchor: 45, onVisualAnchor, onRequestProtectedContent };
  try {
    act(() => root.render(<ReaderExperienceV2 model={model} />));
    expect(container.querySelector('[data-testid="reader-preview-limit"]')).not.toBeNull();
    act(() => container.querySelector('button[aria-label="Previous page"]').click());
    expect(onVisualAnchor).toHaveBeenCalledWith(20);
    expect(onRequestProtectedContent).not.toHaveBeenCalled();
    act(() => root.render(<ReaderExperienceV2 model={{ ...model, visualAnchor: 20 }} />));
    expect(container.querySelector('[data-testid="reader-reading-text"]').textContent).toContain('Page 3');
    act(() => container.querySelector('button[aria-label="Next page"]').click());
    expect(onRequestProtectedContent).toHaveBeenCalled();
  } finally { act(() => root.unmount()); scroll.mockRestore(); }
});
