import {
  audioSegmentAtMediaPosition,
  chapterIdForAudioSegment,
  normalizeAudioManifest,
  normalizeAudioTrack,
  selectAudioTrack,
} from './audioPackageManifest';

const packageVersion = `sha256-${'a'.repeat(64)}`;

const rawManifest = {
  schema_version: 'audiobook_package_manifest.v2',
  slug: 'the-open-window',
  package_version: packageVersion,
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
          audio_url: `/api/reader/book/the-open-window/audiobook/packages/${packageVersion}/segments/c001-s001`,
          timestamps_url: `/api/reader/book/the-open-window/audiobook/packages/${packageVersion}/segments/c001-s001/timestamps`,
          audio_sha256: 'b'.repeat(64),
        },
        {
          segment_id: 'c001-s002',
          order: 1,
          start_word: 100,
          end_word: 199,
          cumulative_start_ms: 300000,
          duration_ms: 320000,
          audio_url: `/api/reader/book/the-open-window/audiobook/packages/${packageVersion}/segments/c001-s002`,
          timestamps_url: `/api/reader/book/the-open-window/audiobook/packages/${packageVersion}/segments/c001-s002/timestamps`,
          audio_sha256: 'c'.repeat(64),
        },
      ],
    },
  ],
};

describe('audiobook package manifest', () => {
  test('accepts chunk-only tracks without requiring a monolithic MP3', () => {
    const manifest = normalizeAudioManifest(
      rawManifest,
      (value) => `https://api.test${value}`,
      {
        expectedSlug: 'the-open-window',
        expectedPackageVersion: packageVersion,
      },
    );

    expect(manifest.valid).toBe(true);
    expect(manifest.schemaVersion).toBe('audiobook_package_manifest.v2');
    expect(manifest.packageVersion).toBe(rawManifest.package_version);
    expect(manifest.tracks).toHaveLength(1);
    expect(manifest.tracks[0].audioUrl).toBe('');
    expect(manifest.tracks[0].chunks).toHaveLength(2);
    expect(manifest.tracks[0].chunks[0].audioUrl).toContain('/segments/c001-s001');
  });

  test('accepts a canonical sticky-canary manifest when release truth has no package version yet', () => {
    const manifest = normalizeAudioManifest(
      rawManifest,
      (value) => value,
      {
        expectedSlug: 'the-open-window',
        expectedPackageVersion: '',
      },
    );

    expect(manifest.valid).toBe(true);
    expect(manifest.packageVersion).toBe(packageVersion);
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

  test('selects the word-bound segment and exposes the next immutable segment', () => {
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
    expect(first.nextAudioUrl).toContain('/segments/c001-s002');
    expect(first.nextTimestampsUrl).toContain('/segments/c001-s002/timestamps');
    expect(second.segmentId).toBe('c001-s002');
    expect(second.nextSegmentId).toBe('');
    expect(second.nextAudioUrl).toBe('');
    expect(second.nextTimestampsUrl).toBe('');
    expect(second.cumulativeStartMs).toBe(300000);
  });

  test('maps a server media position to its immutable segment and offset', () => {
    const manifest = normalizeAudioManifest(rawManifest);

    expect(audioSegmentAtMediaPosition(manifest, 180)).toEqual({
      segmentId: 'c001-s001',
      chapterId: 'chapter-001',
      offsetSeconds: 180,
    });
    expect(audioSegmentAtMediaPosition(manifest, 305.5)).toEqual({
      segmentId: 'c001-s002',
      chapterId: 'chapter-001',
      offsetSeconds: 5.5,
    });
  });

  test('continues across track boundaries and binds the next chapter', () => {
    const crossTrackRaw = {
      ...rawManifest,
      duration_ms: 740000,
      segment_count: 3,
      tracks: [
        ...rawManifest.tracks,
        {
          id: 'chapter-002',
          chapter_id: 'chapter-002',
          order: 1,
          chunks: [
            {
              segment_id: 'c002-s001',
              order: 0,
              start_word: 200,
              end_word: 249,
              cumulative_start_ms: 620000,
              duration_ms: 120000,
              audio_url: `/api/reader/book/the-open-window/audiobook/packages/${packageVersion}/segments/c002-s001`,
              timestamps_url: `/api/reader/book/the-open-window/audiobook/packages/${packageVersion}/segments/c002-s001/timestamps`,
              audio_sha256: 'd'.repeat(64),
            },
          ],
        },
      ],
    };
    const manifest = normalizeAudioManifest(crossTrackRaw);
    const lastInChapterOne = selectAudioTrack({
      manifest,
      chapterId: 'chapter-001',
      preferredSegmentId: 'c001-s002',
    });
    const firstInChapterTwo = selectAudioTrack({
      manifest,
      chapterId: 'chapter-002',
      preferredSegmentId: lastInChapterOne.nextSegmentId,
    });

    expect(manifest.valid).toBe(true);
    expect(lastInChapterOne.nextSegmentId).toBe('c002-s001');
    expect(lastInChapterOne.nextChapterId).toBe('chapter-002');
    expect(lastInChapterOne.nextAudioUrl).toContain('/segments/c002-s001');
    expect(firstInChapterTwo.segmentId).toBe('c002-s001');
    expect(firstInChapterTwo.chapterId).toBe('chapter-002');
    expect(chapterIdForAudioSegment(manifest, 'c002-s001')).toBe('chapter-002');
  });

  test('does not restore a preferred segment into the wrong visible chapter', () => {
    const crossTrackRaw = {
      ...rawManifest,
      duration_ms: 740000,
      segment_count: 3,
      tracks: [
        ...rawManifest.tracks,
        {
          id: 'chapter-002',
          chapter_id: 'chapter-002',
          order: 1,
          chunks: [
            {
              segment_id: 'c002-s001',
              order: 0,
              start_word: 200,
              end_word: 249,
              cumulative_start_ms: 620000,
              duration_ms: 120000,
              audio_url: `/api/reader/book/the-open-window/audiobook/packages/${packageVersion}/segments/c002-s001`,
              timestamps_url: `/api/reader/book/the-open-window/audiobook/packages/${packageVersion}/segments/c002-s001/timestamps`,
            },
          ],
        },
      ],
    };
    const manifest = normalizeAudioManifest(crossTrackRaw);
    const selected = selectAudioTrack({
      manifest,
      chapterId: 'chapter-001',
      preferredSegmentId: 'c002-s001',
    });

    expect(selected.chapterId).toBe('chapter-001');
    expect(selected.segmentId).toBe('c001-s001');
  });

  test('fails closed for mismatched release truth or non-reader asset URLs', () => {
    const wrongSlug = normalizeAudioManifest(rawManifest, (value) => value, {
      expectedSlug: 'another-title',
      expectedPackageVersion: packageVersion,
    });
    const wrongVersion = normalizeAudioManifest(rawManifest, (value) => value, {
      expectedSlug: 'the-open-window',
      expectedPackageVersion: `sha256-${'f'.repeat(64)}`,
    });
    const wrongAsset = normalizeAudioManifest({
      ...rawManifest,
      tracks: [{
        ...rawManifest.tracks[0],
        chunks: [
          {
            ...rawManifest.tracks[0].chunks[0],
            audio_url: 'https://cdn.example.com/the-open-window.mp3',
          },
          rawManifest.tracks[0].chunks[1],
        ],
      }],
    });

    expect(wrongSlug.valid).toBe(false);
    expect(wrongSlug.tracks).toEqual([]);
    expect(wrongSlug.validationError).toMatch(/slug does not match/i);
    expect(wrongVersion.valid).toBe(false);
    expect(wrongVersion.tracks).toEqual([]);
    expect(wrongVersion.validationError).toMatch(/package_version does not match/i);
    expect(wrongAsset.valid).toBe(false);
    expect(wrongAsset.validationError).toMatch(/same-origin reader package routes/i);
  });

  test('rejects protocol-relative package assets even when their path is canonical', () => {
    const protocolRelative = normalizeAudioManifest({
      ...rawManifest,
      tracks: [{
        ...rawManifest.tracks[0],
        chunks: [
          {
            ...rawManifest.tracks[0].chunks[0],
            audio_url: `//evil.example/api/reader/book/the-open-window/audiobook/packages/${packageVersion}/segments/c001-s001`,
          },
          rawManifest.tracks[0].chunks[1],
        ],
      }],
    }, (value) => value, {
      expectedSlug: 'the-open-window',
      expectedPackageVersion: packageVersion,
    });

    expect(protocolRelative.valid).toBe(false);
    expect(protocolRelative.tracks).toEqual([]);
    expect(protocolRelative.validationError).toMatch(/same-origin reader package routes/i);
  });

  test('rejects backslash network paths for package audio and timestamps', () => {
    const networkPath = `/${String.fromCharCode(92)}evil.example/api/reader/book/the-open-window/audiobook/packages/${packageVersion}/segments/c001-s001`;
    const cases = [
      {
        audio_url: networkPath,
      },
      {
        timestamps_url: `${networkPath}/timestamps`,
      },
    ];

    cases.forEach((overrides) => {
      const manifest = normalizeAudioManifest({
        ...rawManifest,
        tracks: [{
          ...rawManifest.tracks[0],
          chunks: [
            {
              ...rawManifest.tracks[0].chunks[0],
              ...overrides,
            },
            rawManifest.tracks[0].chunks[1],
          ],
        }],
      }, (value) => value, {
        expectedSlug: 'the-open-window',
        expectedPackageVersion: packageVersion,
      });

      expect(manifest.valid).toBe(false);
      expect(manifest.tracks).toEqual([]);
      expect(manifest.validationError).toMatch(/same-origin reader package routes/i);
    });
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
