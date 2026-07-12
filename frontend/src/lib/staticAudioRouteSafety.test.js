import fs from 'fs';
import path from 'path';

const vercelConfig = JSON.parse(
  fs.readFileSync(path.resolve(__dirname, '../../vercel.json'), 'utf8')
);

describe('static audio route safety', () => {
  test('routes legacy static audio requests to a removed-content response', () => {
    expect(vercelConfig.rewrites).toEqual(
      expect.arrayContaining([
        {
          source: '/audio/:path*',
          destination: '/api/removed-content?path=/audio/:path*',
        },
      ])
    );
  });

  test('does not cache a legacy static audio namespace', () => {
    expect(vercelConfig.headers || []).not.toEqual(
      expect.arrayContaining([
        expect.objectContaining({ source: '/audio/(.*)' }),
      ])
    );
  });
});
