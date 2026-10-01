import { OFFICIAL_SOCIAL_URLS, getEnabledSocialLinks, normalizeSocialUrlForPlatform } from './socialLinks';

describe('canonical official social destinations', () => {
  test('every default is a usable platform-specific profile or email', () => {
    expect(getEnabledSocialLinks({})).toHaveLength(6);
    Object.entries(OFFICIAL_SOCIAL_URLS).forEach(([id, url]) => expect(normalizeSocialUrlForPlatform(url, id)).toBe(url));
  });
  test.each([
    ['instagram', 'https://instagram.com.evil.example/theearnalism/'],
    ['instagram', 'https://www.facebook.com/theearnalism/'],
    ['x', 'https://x.com/intent/post?text=hello'],
    ['facebook', 'https://www.facebook.com/'],
    ['youtube', 'https://user:secret@www.youtube.com/channel/example'],
    ['email', 'https://example.com/contact'],
  ])('rejects a mislabeled, placeholder or credential-bearing %s override', (id, url) => {
    expect(normalizeSocialUrlForPlatform(url, id)).toBe('');
    expect(getEnabledSocialLinks({ [id]: url }).find(link => link.id === id).url).toBe(OFFICIAL_SOCIAL_URLS[id]);
  });
  test('retains valid configured profiles and legacy twitter alias without inventing a handle', () => {
    expect(getEnabledSocialLinks({ twitter: 'https://twitter.com/earnalism' }).find(link => link.id === 'x').url).toBe('https://twitter.com/earnalism');
  });
});
