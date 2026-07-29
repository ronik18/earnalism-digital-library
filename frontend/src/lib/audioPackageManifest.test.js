import {
  normalizeAudioManifest,
  normalizeAudioTrack,
  selectAudioTrack,
} from './audioPackageManifest';

const rawManifest = {
  schema_version: 'audiobook_package_manifest.v2',
  slug: 'the-open-window',
  package_version: `sha256-${'a'.repeat(64)}`,
  duration_ms: 620000,
  segment_count: 2,
  tracks: [
    {
      id: 'chapter-001',
      chapter_id: 'chapter-001',
      order: 0,
      chunks: [
        {
          segment_id: 'c001-s001',
          order: 0,
          start_word: 0,
          end_word: 99,
          cumulative_start_ms: 0,
          duration_ms: 300000,
          audio_url: '/api/reader/book/the-open-window/audiobook/packages/v/segments/c001-s001',
          timestamps_url: '/api/reader/book/the-open-window/audiobook/packages/v/segments/c001-s001/timestamps',
          audio_sha256: 'b'.repeat(64),
        },
        {
          segment_id: 'c001-s002',
          order: 1,
          start_word: 100,
          end_word: 199,
          cumulative_start_ms: 300000,
          duration_ms: 320000,
          audio_url: '/api/reader/book/the-open-window/audiobook/packages/v/segments/c001-s002',
          timestamps_url: '/api/reader/book/the-open-window/audiobook/packages/v/segments/c001-s002/timestamps',
          audio_sha256: 'c'.repeat(64),
        },
      ],
    },
  ],
};

describe('audiobook package manifest', () => {
  test('accepts chunk-only tracks without requiring a monolithic MP3', () => {
    const manifest = normalizeAudioManifest(rawManifest, (value) => `https://api.test${value}`);

    expect(manifest.schemaVersion).toBe('audiobook_package_manifest.v2');
    expect(manifest.packageVersion).toBe(rawManifest.package_version);
    expect(manifest.tracks).toHaveLength(1);
    expect(manifest.tracks[0].audioUrl).toBe('');
    expect(manifest.tracks[0].chunks).toHaveLength(2);
    expect(manifest.tracks[0].chunks[0].audioUrl).toContain('/segments/c001-s001');
  });

  test('drops incomplete chunks instead of inventing audio or timestamp fallbacks', () => {
    const track = normalizeAudioTrack({
      chapter_id: 'chapter-001',
      chunks: [
        { segment_id: 'audio-only', audio_url: '/segment.mp3' },
        { segment_id: 'complete', audio_url: '/segment-2.mp3', timestamps_url: '/segment-2.json' },
      ],
    });

    expect(track.chunks.map((chunk) => chunk.segmentId)).toEqual(['complete']);
  });

  test('selects the word-bound segment and exposes only the next same-chapter segment', () => {
    const manifest = normalizeAudioManifest(rawManifest);

    const first = selectAudioTrack({
      manifest,
      chapterId: 'chapter-001',
      currentWordOffset: 40,
    });
    const second = selectAudioTrack({
      manifest,
      chapterId: 'chapter-001',
      currentWordOffset: 40,
      preferredSegmentId: first.nextSegmentId,
    });

    expect(first.segmentId).toBe('c001-s001');
    expect(first.nextSegmentId).toBe('c001-s002');
    expect(second.segmentId).toBe('c001-s002');
    expect(second.nextSegmentId).toBe('');
    expect(second.cumulativeStartMs).toBe(300000);
  });

  test('uses approved legacy assets only when no package track is available', () => {
    const selected = selectAudioTrack({
      manifest: { tracks: [] },
      chapterId: 'chapter-001',
      approvedAudioUrl: '/approved.mp3',
      approvedTimestampsUrl: '/approved.json',
    });

    expect(selected.audioUrl).toBe('/approved.mp3');
    expect(selected.timestampsUrl).toBe('/approved.json');
    expect(selected.chunked).toBe(false);
  });
});
