const AUDIOBOOK_PROGRESS_PREFIX = 'earnalism.audiobook.progress.v1';

export const AUDIOBOOK_PROGRESS_SAVE_INTERVAL_MS = 5000;
export const AUDIOBOOK_NEXT_SEGMENT_PREFETCH_RATIO = 0.7;

function finiteNumber(value, fallback = 0) {
  const parsed = Number(value);
  return Number.isFinite(parsed) ? parsed : fallback;
}

function browserStorage() {
  if (typeof window === 'undefined' || !window.localStorage) return null;
  return window.localStorage;
}

export function audiobookProgressStorageKey(slug = '') {
  return `${AUDIOBOOK_PROGRESS_PREFIX}:${encodeURIComponent(String(slug || '').trim())}`;
}

export function sanitizeAudiobookProgress(value = {}) {
  if (!value || typeof value !== 'object' || Array.isArray(value)) return null;
  const packageVersion = String(value.packageVersion || '').trim();
  const segmentId = String(value.segmentId || '').trim();
  if (!packageVersion || !segmentId) return null;
  return {
    packageVersion,
    segmentId,
    offset: Math.max(0, finiteNumber(value.offset, 0)),
    speed: Math.max(0.7, Math.min(1.8, finiteNumber(value.speed, 1))),
  };
}

export function loadAudiobookProgress(
  slug,
  packageVersion,
  storage = browserStorage(),
) {
  if (!storage || !slug || !packageVersion) return null;
  try {
    const progress = sanitizeAudiobookProgress(
      JSON.parse(storage.getItem(audiobookProgressStorageKey(slug)) || 'null'),
    );
    return progress?.packageVersion === packageVersion ? progress : null;
  } catch {
    return null;
  }
}

export function saveAudiobookProgress(slug, value, storage = browserStorage()) {
  const progress = sanitizeAudiobookProgress(value);
  if (!storage || !slug || !progress) return false;
  try {
    storage.setItem(audiobookProgressStorageKey(slug), JSON.stringify(progress));
    return true;
  } catch {
    return false;
  }
}

export function pendingAudiobookResumeMatches(pending, {
  bookId = '',
  packageVersion = '',
  chapterId = '',
  segmentChapterId = '',
} = {}) {
  if (!pending || typeof pending !== 'object' || Array.isArray(pending)) return false;
  return Boolean(
    bookId
    && packageVersion
    && chapterId
    && segmentChapterId
    && pending.bookId === bookId
    && pending.packageVersion === packageVersion
    && pending.chapterId === chapterId
    && segmentChapterId === chapterId
    && pending.segmentId
  );
}

export function shouldPrefetchNextSegment(currentTime, duration, hasNextSegment) {
  const safeCurrentTime = finiteNumber(currentTime, 0);
  const safeDuration = finiteNumber(duration, 0);
  return Boolean(
    hasNextSegment
    && safeDuration > 0
    && safeCurrentTime / safeDuration >= AUDIOBOOK_NEXT_SEGMENT_PREFETCH_RATIO
  );
}

export function requestAudiobookPlayback(audio) {
  if (!audio || typeof audio.play !== 'function') {
    return Promise.reject(new TypeError('An audio element with play() is required'));
  }

  try {
    // Keep play() in the caller's user-activation stack. Deferring this call
    // through an animation frame or promise can make browsers reject the first
    // click after the lazily assigned media source finishes loading.
    return Promise.resolve(audio.play());
  } catch (error) {
    return Promise.reject(error);
  }
}
