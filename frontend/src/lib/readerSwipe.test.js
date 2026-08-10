import { readerSwipeDirection } from './readerSwipe';

describe('reader swipe navigation', () => {
  test('maps a left swipe to the next page and a right swipe to the previous page', () => {
    expect(readerSwipeDirection({ x: 240, y: 120 }, { x: 160, y: 126 })).toBe('next');
    expect(readerSwipeDirection({ x: 160, y: 120 }, { x: 240, y: 126 })).toBe('previous');
  });

  test('ignores taps, short drags, and mostly vertical gestures', () => {
    expect(readerSwipeDirection({ x: 100, y: 100 }, { x: 112, y: 101 })).toBe('');
    expect(readerSwipeDirection({ x: 100, y: 100 }, { x: 140, y: 170 })).toBe('');
  });
});
