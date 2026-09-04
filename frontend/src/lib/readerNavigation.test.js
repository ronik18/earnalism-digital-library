import { readerBookMatchesRoute, readerRouteForBook } from './readerNavigation';

describe('reader navigation identity', () => {
  test('builds a title-specific reader route', () => {
    expect(readerRouteForBook('bharat-at-the-crossroads', { listen: true }))
      .toBe('/reader/bharat-at-the-crossroads?listen=1');
  });

  test('rejects a manifest for a different title', () => {
    expect(readerBookMatchesRoute({ slug: 'a-ghost-story' }, 'bharat-at-the-crossroads')).toBe(false);
    expect(readerBookMatchesRoute({ slug: 'bharat-at-the-crossroads' }, 'bharat-at-the-crossroads')).toBe(true);
  });

  test('fails closed when a manifest omits or cannot safely decode its slug', () => {
    expect(readerBookMatchesRoute({}, 'bharat-at-the-crossroads')).toBe(false);
    expect(readerBookMatchesRoute({ slug: '%E0%A4%A' }, 'bharat-at-the-crossroads')).toBe(false);
    expect(readerRouteForBook('')).toBe('/library');
  });
});
