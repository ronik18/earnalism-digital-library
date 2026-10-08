import { installRoutePrefetch } from './routePrefetch';

const settle = () => Promise.resolve();
afterEach(() => { document.body.innerHTML = ''; });
test('idle visits fetch no route code; pointer and keyboard intent deduplicate and cleanup', async () => {
  const load = jest.fn().mockResolvedValue({});
  document.body.innerHTML = '<a href="/library"><span>Library</span></a>';
  const cleanup = installRoutePrefetch({ document, window, loaders: { '/library': load } });
  await settle(); expect(load).not.toHaveBeenCalled();
  document.querySelector('span').dispatchEvent(new Event('pointerover', { bubbles: true }));
  document.querySelector('a').dispatchEvent(new Event('focusin', { bubbles: true }));
  await settle(); expect(load).toHaveBeenCalledTimes(1);
  cleanup();
  const next = jest.fn();
  const stop = installRoutePrefetch({ document, window, loaders: { '/book': next } }); stop();
  document.querySelector('a').href = '/book/example';
  document.querySelector('a').dispatchEvent(new Event('focusin', { bubbles: true }));
  await settle(); expect(next).not.toHaveBeenCalled();
});
test('data saver and slow connections prevent speculative downloads', async () => {
  const load = jest.fn();
  for (const connection of [{ saveData: true }, { effectiveType: 'slow-2g' }, { effectiveType: '2g' }]) {
    const stop = installRoutePrefetch({ document, window: { navigator: { connection } }, loaders: { '/library': load } });
    stop();
  }
  await settle(); expect(load).not.toHaveBeenCalled();
});
test('external links never preload and nested title paths use only their route loader', async () => {
  const book = jest.fn().mockResolvedValue({}); const library = jest.fn();
  document.body.innerHTML = '<a href="https://example.com/library">External</a><a href="/book/example">Title</a>';
  const stop = installRoutePrefetch({ document, window, loaders: { '/book': book, '/library': library } });
  for (const a of document.querySelectorAll('a')) a.dispatchEvent(new Event('focusin', { bubbles: true }));
  await settle(); expect(book).toHaveBeenCalledTimes(1); expect(library).not.toHaveBeenCalled(); stop();
});
