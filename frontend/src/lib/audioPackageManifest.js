export const AUDIOBOOK_PACKAGE_MANIFEST_SCHEMA_VERSION = 'audiobook_package_manifest.v2';

function firstExplicitAsset(source = {}, keys = []) {
  for (const key of keys) {
    if (source?.[key]) return source[key];
  }
  return '';
}

function finiteNumber(value, fallback = 0) {
  const parsed = Number(value);
  return Number.isFinite(parsed) ? parsed : fallback;
}

function resolveExplicitUrl(resolveUrl, value) {
  return value ? resolveUrl(value) : '';
}

function clean(value = '') {
  return String(value || '').trim();
}

function emptyAudioManifest(raw = {}, validationError = '') {
  return {
    schemaVersion: raw.schema_version || '',
    slug: raw.slug || '',
    version: raw.version || raw.package_version || raw.hash || '',
    packageVersion: raw.package_version || raw.version || raw.hash || '',
    durationMs: finiteNumber(raw.duration_ms ?? raw.durationMs, 0),
    segmentCount: finiteNumber(raw.segment_count ?? raw.segmentCount, 0),
    tracks: [],
    valid: false,
    validationError,
  };
}

function sameOriginPackagePath(value = '') {
  const raw = clean(value);
  if (!raw) return '';
  if (/[\u0000-\u001F\u007F\\]/.test(raw)) return '';
  // A protocol-relative URL is cross-origin capable even though it begins
  // with "/". Never interpret it as an API-relative package path.
  if (raw.startsWith('//')) return '';
  if (raw.startsWith('/')) {
    try {
      const validationOrigin = 'https://earnalism.invalid';
      const parsed = new URL(raw, validationOrigin);
      return (
        parsed.origin !== validationOrigin
        || parsed.search
        || parsed.hash
      ) ? '' : parsed.pathname;
    } catch {
      return '';
    }
  }
  try {
    const parsed = new URL(raw);
    if (
      typeof window === 'undefined'
      || !window.location?.origin
      || parsed.origin !== window.location.origin
      || parsed.search
      || parsed.hash
    ) return '';
    return parsed.pathname;
  } catch {
    return '';
  }
}

function isExpectedPackageAssetUrl(value, {
  slug,
  packageVersion,
  segmentId,
  asset,
}) {
  const path = sameOriginPackagePath(value);
  if (!path || !slug || !packageVersion || !segmentId) return false;
  const segmentPath = `/api/reader/book/${encodeURIComponent(slug)}/audiobook/packages/${encodeURIComponent(packageVersion)}/segments/${encodeURIComponent(segmentId)}`;
  return path === (asset === 'timestamps' ? `${segmentPath}/timestamps` : segmentPath);
}

export function normalizeAudioTrack(raw = {}, resolveUrl = (value) => value || '') {
  const explicitAudioSource = firstExplicitAsset(raw, ['audio_url', 'audioUrl', 'mp3', 'src']);
  const explicitTimestampSource = firstExplicitAsset(raw, ['timestamps_url', 'timestampsUrl', 'timestamps']);
  const rawChunks = raw.chunks || raw.pages || raw.timestamp_chunks;
  const chunks = Array.isArray(rawChunks)
    ? rawChunks.map((chunk, index) => {
      const sourceAudioUrl = firstExplicitAsset(chunk, ['audio_url', 'audioUrl', 'mp3', 'src'])
        || explicitAudioSource;
      const sourceTimestampsUrl = firstExplicitAsset(
        chunk,
        ['timestamps_url', 'timestampsUrl', 'timestamps'],
      ) || explicitTimestampSource;
      return {
        segmentId: chunk.segment_id || chunk.segmentId || chunk.id || '',
        order: finiteNumber(chunk.order, index),
        startWord: finiteNumber(chunk.start_word ?? chunk.startWord ?? chunk.word_start, 0),
        endWord: finiteNumber(
          chunk.end_word ?? chunk.endWord ?? chunk.word_end,
          Number.MAX_SAFE_INTEGER,
        ),
        cumulativeStartMs: finiteNumber(
          chunk.cumulative_start_ms ?? chunk.cumulativeStartMs,
          0,
        ),
        durationMs: finiteNumber(chunk.duration_ms ?? chunk.durationMs, 0),
        audioUrl: resolveExplicitUrl(resolveUrl, sourceAudioUrl),
        timestampsUrl: resolveExplicitUrl(resolveUrl, sourceTimestampsUrl),
        sourceAudioUrl,
        sourceTimestampsUrl,
        version: chunk.version || chunk.audio_sha256 || chunk.hash || raw.version || '',
      };
    })
      .filter((chunk) => Boolean(chunk.audioUrl) && Boolean(chunk.timestampsUrl))
      .sort((left, right) => left.order - right.order)
    : [];

  return {
    id: raw.id || raw.chapter_id || raw.chapterId || '',
    chapterId: raw.chapter_id || raw.chapterId || raw.id || '',
    order: finiteNumber(raw.order, 0),
    startWord: finiteNumber(raw.start_word ?? raw.startWord, 0),
    endWord: finiteNumber(raw.end_word ?? raw.endWord, Number.MAX_SAFE_INTEGER),
    cumulativeStartMs: finiteNumber(raw.cumulative_start_ms ?? raw.cumulativeStartMs, 0),
    durationMs: finiteNumber(raw.duration_ms ?? raw.durationMs, 0),
    audioUrl: resolveExplicitUrl(resolveUrl, explicitAudioSource),
    timestampsUrl: resolveExplicitUrl(resolveUrl, explicitTimestampSource),
    sourceAudioUrl: explicitAudioSource,
    sourceTimestampsUrl: explicitTimestampSource,
    version: raw.version || raw.hash || '',
    chunks,
  };
}

function validateNormalizedManifest(manifest, {
  expectedSlug = '',
  expectedPackageVersion = '',
} = {}) {
  if (manifest.schemaVersion !== AUDIOBOOK_PACKAGE_MANIFEST_SCHEMA_VERSION) {
    return `schema_version must be ${AUDIOBOOK_PACKAGE_MANIFEST_SCHEMA_VERSION}`;
  }
  if (!/^[a-z0-9]+(?:-[a-z0-9]+)*$/.test(manifest.slug)) return 'slug is not canonical';
  if (expectedSlug && manifest.slug !== expectedSlug) return 'slug does not match reader release truth';
  if (!/^sha256-[a-f0-9]{64}$/.test(manifest.packageVersion)) {
    return 'package_version is not canonical';
  }
  if (expectedPackageVersion && manifest.packageVersion !== expectedPackageVersion) {
    return 'package_version does not match reader release truth';
  }
  if (!manifest.tracks.length) return 'tracks must not be empty';

  const chapterIds = new Set();
  const segmentIds = new Set();
  let expectedStartWord = 0;
  let expectedStartMs = 0;
  let actualSegmentCount = 0;

  for (let trackIndex = 0; trackIndex < manifest.tracks.length; trackIndex += 1) {
    const track = manifest.tracks[trackIndex];
    if (!track.id || !track.chapterId || chapterIds.has(track.chapterId)) {
      return 'track and chapter identifiers must be non-empty and unique';
    }
    chapterIds.add(track.chapterId);
    if (track.order !== trackIndex || !track.chunks.length) {
      return 'track ordering must be contiguous and every track must contain segments';
    }
    for (let segmentIndex = 0; segmentIndex < track.chunks.length; segmentIndex += 1) {
      const chunk = track.chunks[segmentIndex];
      if (!chunk.segmentId || segmentIds.has(chunk.segmentId)) {
        return 'segment identifiers must be non-empty and globally unique';
      }
      segmentIds.add(chunk.segmentId);
      if (chunk.order !== segmentIndex) return 'segment ordering must be contiguous';
      if (chunk.startWord !== expectedStartWord || chunk.endWord < chunk.startWord) {
        return 'segment word ranges must be globally contiguous';
      }
      if (
        chunk.cumulativeStartMs !== expectedStartMs
        || !Number.isInteger(chunk.durationMs)
        || chunk.durationMs <= 0
      ) {
        return 'segment timing must be positive and globally contiguous';
      }
      if (!isExpectedPackageAssetUrl(chunk.sourceAudioUrl, {
        slug: manifest.slug,
        packageVersion: manifest.packageVersion,
        segmentId: chunk.segmentId,
        asset: 'audio',
      }) || !isExpectedPackageAssetUrl(chunk.sourceTimestampsUrl, {
        slug: manifest.slug,
        packageVersion: manifest.packageVersion,
        segmentId: chunk.segmentId,
        asset: 'timestamps',
      })) {
        return 'segment assets must use exact same-origin reader package routes';
      }
      expectedStartWord = chunk.endWord + 1;
      expectedStartMs += chunk.durationMs;
      actualSegmentCount += 1;
    }
  }

  if (
    actualSegmentCount !== manifest.segmentCount
    || manifest.segmentCount <= 0
    || !Number.isInteger(manifest.segmentCount)
  ) {
    return 'segment_count does not match the exact segment list';
  }
  if (manifest.durationMs !== expectedStartMs) {
    return 'duration_ms does not match cumulative segment duration';
  }
  return '';
}

export function normalizeAudioManifest(
  raw = {},
  resolveUrl = (value) => value || '',
  expected = {},
) {
  const rawTracks = raw.tracks || raw.chapters || raw.items || [];
  const tracks = Array.isArray(rawTracks)
    ? rawTracks
      .map((track) => normalizeAudioTrack(track, resolveUrl))
      .filter((track) => (
        (Boolean(track.audioUrl) && Boolean(track.timestampsUrl))
        || track.chunks.length > 0
      ))
      .sort((left, right) => left.order - right.order)
    : [];
  const manifest = {
    schemaVersion: raw.schema_version || '',
    slug: raw.slug || '',
    version: raw.version || raw.package_version || raw.hash || '',
    packageVersion: raw.package_version || raw.version || raw.hash || '',
    durationMs: finiteNumber(raw.duration_ms ?? raw.durationMs, 0),
    segmentCount: finiteNumber(raw.segment_count ?? raw.segmentCount, 0),
    tracks,
    valid: true,
    validationError: '',
  };
  const validationError = validateNormalizedManifest(manifest, expected);
  return validationError ? emptyAudioManifest(raw, validationError) : manifest;
}

export function chapterIdForAudioSegment(manifest, segmentId = '') {
  if (!segmentId) return '';
  return (manifest?.tracks || []).find((track) => (
    track.chunks || []
  ).some((chunk) => chunk.segmentId === segmentId))?.chapterId || '';
}

export function selectAudioTrack({
  manifest,
  chapterId,
  currentWordOffset = 0,
  preferredSegmentId = '',
  approvedAudioUrl,
  approvedTimestampsUrl,
}) {
  const tracks = manifest?.tracks || [];
  let track = tracks.find((item) => item.chapterId && item.chapterId === chapterId) || tracks[0];
  if (preferredSegmentId) {
    const preferredTrack = tracks.find((item) => (
      item.chunks || []
    ).some((chunk) => chunk.segmentId === preferredSegmentId));
    if (preferredTrack && (!chapterId || preferredTrack.chapterId === chapterId)) track = preferredTrack;
  }
  if (track) {
    const chunks = track.chunks || [];
    let chunkIndex = preferredSegmentId
      ? chunks.findIndex((item) => item.segmentId === preferredSegmentId)
      : chunks.findIndex(
        (item) => currentWordOffset >= item.startWord && currentWordOffset <= item.endWord,
    );
    if (chunkIndex < 0 && chunks.length) chunkIndex = 0;
    const chunk = chunkIndex >= 0 ? chunks[chunkIndex] : null;
    const orderedSegments = tracks.flatMap((item) => (
      item.chunks || []
    ).map((itemChunk) => ({ chunk: itemChunk, track: item })));
    const globalChunkIndex = chunk
      ? orderedSegments.findIndex((item) => item.chunk.segmentId === chunk.segmentId)
      : -1;
    const nextSegment = globalChunkIndex >= 0 ? orderedSegments[globalChunkIndex + 1] : null;
    const nextChunk = nextSegment?.chunk || null;
    return {
      audioUrl: chunk?.audioUrl || track.audioUrl,
      timestampsUrl: chunk?.timestampsUrl || track.timestampsUrl,
      startWord: chunk?.startWord ?? track.startWord ?? 0,
      endWord: chunk?.endWord ?? track.endWord ?? Number.MAX_SAFE_INTEGER,
      cumulativeStartMs: chunk?.cumulativeStartMs ?? track.cumulativeStartMs ?? 0,
      durationMs: chunk?.durationMs ?? track.durationMs ?? 0,
      version: chunk?.version || track.version || manifest.version || '',
      packageVersion: manifest.packageVersion || manifest.version || '',
      segmentId: chunk?.segmentId || '',
      nextSegmentId: nextChunk?.segmentId || '',
      nextAudioUrl: nextChunk?.audioUrl || '',
      nextTimestampsUrl: nextChunk?.timestampsUrl || '',
      nextVersion: nextChunk?.version || '',
      nextChapterId: nextSegment?.track?.chapterId || '',
      chapterId: track.chapterId || '',
      chunked: Boolean(chunk || chunks.length),
    };
  }
  return {
    audioUrl: approvedAudioUrl,
    timestampsUrl: approvedTimestampsUrl,
    startWord: 0,
    endWord: Number.MAX_SAFE_INTEGER,
    cumulativeStartMs: 0,
    durationMs: 0,
    version: '',
    packageVersion: '',
    segmentId: '',
    nextSegmentId: '',
    nextAudioUrl: '',
    nextTimestampsUrl: '',
    nextVersion: '',
    nextChapterId: '',
    chapterId: chapterId || '',
    chunked: false,
  };
}
