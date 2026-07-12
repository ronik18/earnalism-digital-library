import {
  audioTimestampEndMs,
  audioTimestampStartMs,
  normalizeAudioTimestamp,
} from './audioTimestampSchema';

describe('approved audiobook timestamp schema', () => {
  test('preserves explicit millisecond timestamps', () => {
    expect(audioTimestampStartMs({ start_ms: 1250, start: 99 })).toBe(1250);
    expect(audioTimestampEndMs({ end_ms: 1750, end: 99 })).toBe(1750);
  });

  test('converts production word timestamps from seconds', () => {
    expect(normalizeAudioTimestamp({ word: 'took', start: 0.26, end: 0.48 })).toEqual({
      word: 'took',
      start: 0.26,
      end: 0.48,
      start_ms: 260,
      end_ms: 480,
    });
  });

  test('converts production section timestamps from seconds', () => {
    const cue = normalizeAudioTimestamp({ index: 2, start: 138.72, end: 274.513 });
    expect(cue.start_ms).toBeCloseTo(138720);
    expect(cue.end_ms).toBeCloseTo(274513);
  });

  test('fails safely for missing or invalid values', () => {
    expect(normalizeAudioTimestamp({ start: 'invalid' })).toMatchObject({
      start_ms: 0,
      end_ms: 0,
    });
  });
});
