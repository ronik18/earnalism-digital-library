import {
  AUDIOBOOK_NEXT_SEGMENT_PREFETCH_RATIO,
  audiobookProgressStorageKey,
  loadAudiobookProgress,
  saveAudiobookProgress,
  sanitizeAudiobookProgress,
  shouldPrefetchNextSegment,
} from './audiobookPlayback';

function memoryStorage() {
  const values = new Map();
  return {
    getItem: (key) => values.get(key) || null,
    setItem: (key, value) => values.set(key, value),
  };
}

describe('audiobook package playback', () => {
  test('stores the minimum package-bound playback position per slug', () => {
    const storage = memoryStorage();
    expect(saveAudiobookProgress('muchiram-gurer-jibanchorit', {
      packageVersion: 'sha256-package',
      segmentId: 'c001-s002',
      offset: 42.25,
      speed: 1.2,
    }, storage)).toBe(true);

    expect(JSON.parse(storage.getItem(
      audiobookProgressStorageKey('muchiram-gurer-jibanchorit'),
    ))).toEqual({
      packageVersion: 'sha256-package',
      segmentId: 'c001-s002',
      offset: 42.25,
      speed: 1.2,
    });
  });

  test('restores progress only for the exact immutable package version', () => {
    const storage = memoryStorage();
    saveAudiobookProgress('muchiram', {
      packageVersion: 'sha256-current',
      segmentId: 'c001-s001',
      offset: 17,
      speed: 0.9,
    }, storage);

    expect(loadAudiobookProgress('muchiram', 'sha256-current', storage)).toEqual({
      packageVersion: 'sha256-current',
      segmentId: 'c001-s001',
      offset: 17,
      speed: 0.9,
    });
    expect(loadAudiobookProgress('muchiram', 'sha256-replaced', storage)).toBeNull();
  });

  test('sanitizes offsets and speed without accepting incomplete records', () => {
    expect(sanitizeAudiobookProgress({
      packageVersion: 'v1',
      segmentId: 's1',
      offset: -5,
      speed: 99,
    })).toEqual({
      packageVersion: 'v1',
      segmentId: 's1',
      offset: 0,
      speed: 1.8,
    });
    expect(sanitizeAudiobookProgress({ packageVersion: 'v1' })).toBeNull();
  });

  test('prefetches the next segment only at the 70 percent boundary', () => {
    expect(AUDIOBOOK_NEXT_SEGMENT_PREFETCH_RATIO).toBe(0.7);
    expect(shouldPrefetchNextSegment(69.9, 100, true)).toBe(false);
    expect(shouldPrefetchNextSegment(70, 100, true)).toBe(true);
    expect(shouldPrefetchNextSegment(99, 100, false)).toBe(false);
    expect(shouldPrefetchNextSegment(0, 0, true)).toBe(false);
  });
});
