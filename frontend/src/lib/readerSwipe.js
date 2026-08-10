export const READER_SWIPE_THRESHOLD_PX = 48;

export function readerSwipeDirection(start, end, {
  threshold = READER_SWIPE_THRESHOLD_PX,
  axisBias = 1.2,
} = {}) {
  if (!start || !end) return '';
  const deltaX = Number(end.x) - Number(start.x);
  const deltaY = Number(end.y) - Number(start.y);
  const horizontalDistance = Math.abs(deltaX);
  if (!Number.isFinite(deltaX) || !Number.isFinite(deltaY)) return '';
  if (horizontalDistance < threshold || horizontalDistance <= Math.abs(deltaY) * axisBias) return '';
  return deltaX < 0 ? 'next' : 'previous';
}
