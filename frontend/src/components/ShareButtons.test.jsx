import React, { act } from 'react';
import { createRoot } from 'react-dom/client';
import ShareButtons from './ShareButtons';
jest.mock('sonner', () => ({ toast: { success: jest.fn(), error: jest.fn() } }));
globalThis.IS_REACT_ACT_ENVIRONMENT = true;

test('article share intents contain the canonical public URL and no sensitive query', () => {
  window.history.replaceState({}, '', '/journal/a-quiet-story?token=secret&utm_source=social#comments');
  const container = document.createElement('div');
  const root = createRoot(container);
  act(() => root.render(<ShareButtons title="A quiet story" variant="article" />));
  const links = [...container.querySelectorAll('a')].map(a => new URL(a.href));
  expect(links.map(url => url.hostname)).toEqual(['wa.me', 'www.facebook.com', 'x.com', 'www.linkedin.com']);
  expect(links[0].searchParams.get('text')).toBe('A quiet story http://localhost/journal/a-quiet-story');
  expect(links[1].searchParams.get('u')).toBe('http://localhost/journal/a-quiet-story');
  expect(links[2].pathname).toBe('/intent/tweet');
  expect(links[2].searchParams.get('url')).toBe('http://localhost/journal/a-quiet-story');
  expect(links[3].searchParams.get('url')).toBe('http://localhost/journal/a-quiet-story');
  links.forEach(url => expect(url.href).not.toMatch(/secret|utm_source|comments/));
  act(() => root.unmount());
});
