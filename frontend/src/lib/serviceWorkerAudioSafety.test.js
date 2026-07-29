import fs from 'fs';
import path from 'path';

const serviceWorkerSource = fs.readFileSync(
  path.resolve(__dirname, '../../public/service-worker.js'),
  'utf8',
);

describe('service worker audiobook safety', () => {
  test('bypasses every release-gated reader audiobook API request before caching', () => {
    expect(serviceWorkerSource).toMatch(
      /function isAudiobookApiRequest\(request\)[\s\S]*\/api\\\/reader\\\/book/,
    );
    expect(serviceWorkerSource).toMatch(
      /if \(isAudiobookApiRequest\(request\)\) return;[\s\S]*if \(isStaticAsset\(request\)\)/,
    );
  });

  test('continues to bypass byte-range requests explicitly', () => {
    expect(serviceWorkerSource).toMatch(
      /if \(request\.headers\.has\("range"\)\) return;/,
    );
  });
});
