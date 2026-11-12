import { normalizeAudioPreviewManifest } from './audioPackageManifest';
const version = `sha256-${'a'.repeat(64)}`;
const make = () => ({ schema_version: 'audiobook_preview.v1', slug: 'approved', package_version: version, duration_ms: 180000,
  segments: [{ segment_id: 'segment-1', chapter_id: 'c1', cumulative_start_ms: 0, duration_ms: 180000,
    audio_url: `/api/reader/book/approved/audiobook/preview/packages/${version}/segments/segment-1` }] });
const normalize = raw => normalizeAudioPreviewManifest(raw, { expectedSlug: 'approved', expectedPackageVersion: version });
test('preview is separate from paid progress and contains only its bounded URL', () => {
  const normalized = normalize(make());
  expect(normalized.valid).toBe(true);
  expect(normalized.packageVersion).toBe(`preview:${version}`);
  expect(normalized.preview).toBe(true);
});
test.each(['long', 'cross-origin', 'full-audio', 'query', 'wrong-version', 'gap', 'duplicate'])('rejects %s preview authority', mode => {
  const raw = make();
  if (mode === 'long') raw.duration_ms = raw.segments[0].duration_ms = 180001;
  if (mode === 'cross-origin') raw.segments[0].audio_url = 'https://other.invalid/full.mp3';
  if (mode === 'full-audio') raw.segments[0].audio_url = raw.segments[0].audio_url.replace('/preview', '');
  if (mode === 'query') raw.segments[0].audio_url += '?source=full';
  if (mode === 'wrong-version') raw.package_version = `sha256-${'b'.repeat(64)}`;
  if (mode === 'gap') raw.segments[0].cumulative_start_ms = 1;
  if (mode === 'duplicate') raw.segments.push({ ...raw.segments[0] });
  expect(normalize(raw).valid).toBe(false);
});
