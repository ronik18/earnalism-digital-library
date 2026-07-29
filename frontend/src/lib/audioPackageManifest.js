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

export function normalizeAudioTrack(raw = {}, resolveUrl = (value) => value || '') {
  const explicitAudioSource = firstExplicitAsset(raw, ['audio_url', 'audioUrl', 'mp3', 'src']);
  const explicitTimestampSource = firstExplicitAsset(raw, ['timestamps_url', 'timestampsUrl', 'timestamps']);
  const rawChunks = raw.chunks || raw.pages || raw.timestamp_chunks;
  const chunks = Array.isArray(rawChunks)
    ? rawChunks.map((chunk, index) => ({
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
      audioUrl: resolveExplicitUrl(
        resolveUrl,
        firstExplicitAsset(chunk, ['audio_url', 'audioUrl', 'mp3', 'src']) || explicitAudioSource,
      ),
      timestampsUrl: resolveExplicitUrl(
        resolveUrl,
        firstExplicitAsset(chunk, ['timestamps_url', 'timestampsUrl', 'timestamps'])
          || explicitTimestampSource,
      ),
      version: chunk.version || chunk.audio_sha256 || chunk.hash || raw.version || '',
    }))
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
    version: raw.version || raw.hash || '',
    chunks,
  };
}

export function normalizeAudioManifest(raw = {}, resolveUrl = (value) => value || '') {
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
  return {
    schemaVersion: raw.schema_version || '',
    slug: raw.slug || '',
    version: raw.version || raw.package_version || raw.hash || '',
    packageVersion: raw.package_version || raw.version || raw.hash || '',
    durationMs: finiteNumber(raw.duration_ms ?? raw.durationMs, 0),
    segmentCount: finiteNumber(raw.segment_count ?? raw.segmentCount, 0),
    tracks,
  };
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
    if (preferredTrack) track = preferredTrack;
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
    const nextChunk = chunkIndex >= 0 ? chunks[chunkIndex + 1] : null;
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
    chapterId: chapterId || '',
    chunked: false,
  };
}
