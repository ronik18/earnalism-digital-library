import {
  AUDIOBOOK_NEXT_SEGMENT_PREFETCH_RATIO,
  audiobookProgressStorageKey,
  loadAudiobookProgress,
  pendingAudiobookResumeMatches,
  requestAudiobookPlayback,
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

  test('binds a pending cross-chapter resume to one book and immutable package', () => {
    const pending = {
      bookId: 'the-open-window',
      packageVersion: 'sha256-current',
      chapterId: 'chapter-002',
      segmentId: 'c002-s001',
    };
    const expected = {
      bookId: 'the-open-window',
      packageVersion: 'sha256-current',
      chapterId: 'chapter-002',
      segmentChapterId: 'chapter-002',
    };

    expect(pendingAudiobookResumeMatches(pending, expected)).toBe(true);
    expect(pendingAudiobookResumeMatches(pending, {
      ...expected,
      bookId: 'another-title',
    })).toBe(false);
    expect(pendingAudiobookResumeMatches(pending, {
      ...expected,
      packageVersion: 'sha256-replaced',
    })).toBe(false);
    expect(pendingAudiobookResumeMatches(pending, {
      ...expected,
      segmentChapterId: 'chapter-001',
    })).toBe(false);
  });

  test('requests playback synchronously while the first-click activation is live', async () => {
    const order = [];
    let resolvePlayback;
    const playback = new Promise((resolve) => {
      resolvePlayback = resolve;
    });
    const audio = {
      play: jest.fn(() => {
        order.push('play');
        return playback;
      }),
    };

    const requested = requestAudiobookPlayback(audio);
    order.push('returned');

    expect(audio.play).toHaveBeenCalledTimes(1);
    expect(order).toEqual(['play', 'returned']);

    resolvePlayback();
    await expect(requested).resolves.toBeUndefined();
  });

  test('turns synchronous media and autoplay failures into rejectable promises', async () => {
    const blocked = Object.assign(new Error('Playback requires user activation'), {
      name: 'NotAllowedError',
    });
    const audio = {
      play: jest.fn(() => {
        throw blocked;
      }),
    };

    await expect(requestAudiobookPlayback(audio)).rejects.toBe(blocked);
    await expect(requestAudiobookPlayback(null)).rejects.toThrow(
      'An audio element with play() is required',
    );
  });
});
